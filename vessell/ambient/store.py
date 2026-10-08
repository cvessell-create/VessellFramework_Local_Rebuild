from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from vessell.app.pipeline import run_case_pipeline
from vessell.field_inquiry import (
    FIELD_POLICY,
    InvalidFieldInquiry,
    assess_field_inquiry,
    field_template,
)

from .models import AmbientEvent, FieldInquiryAction, FilingAction, FilingState, SnapshotData

LOG = logging.getLogger(__name__)
TERMINAL = ("COMPLETED", "REJECTED", "FAILED")
TRANSITIONS = {
    "PENDING": {"RUNNING", "FAILED"},
    "RUNNING": {"AWAITING_APPROVAL", "COMPLETED", "FAILED"},
    "AWAITING_APPROVAL": {"APPROVED", "REJECTED"},
    "APPROVED": {"RUNNING", "FAILED", "AWAITING_APPROVAL"},
    "COMPLETED": set(), "REJECTED": set(), "FAILED": set(),
}


class Conflict(ValueError):
    pass


class MissingJob(LookupError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat()


def analyze(event: dict[str, Any]) -> dict[str, Any]:
    specialist = event["event_type"] == "agent.analysis.requested"
    case = {
        "title": "Specialist evidence review" if specialist else f"Ambient review: {event['event_type']}",
        "subject": event["source"],
        "decision_question": (
            event["data"]["question"] if specialist
            else "What does this reported event establish for local review?"
        ),
        "domain": "Callable evidence analysis" if specialist else "Local event analysis",
        "evidence": [{
            **row, "status": "WORKING HYPOTHESIS",
        } for row in event["data"]["evidence"]] if specialist else [{
            "source_id": "external-event", "status": "WORKING HYPOTHESIS",
            "description": canonical(event["data"]),
        }],
        "harm_gate": {
            "accuracy_risk": True, "academic_risk": False, "professional_risk": True,
            "legal_risk": False, "financial_security_risk": False,
            "hard_to_reverse": False, "benefit_proportionate": True,
        },
        "analysis": {"posture": (
            "Uncorroborated provider report. Human review can release this local analysis, "
            "not establish event truth or authorize external actions."
        )},
    }
    if specialist and event["data"].get("field_inquiry") is not None:
        case["field_inquiry"] = event["data"]["field_inquiry"]
    if specialist and event["data"].get("game_theory") is not None:
        case["game_theory"] = event["data"]["game_theory"]
    result = asdict(run_case_pipeline(case, track_provenance=False))
    if specialist:
        result["confidence_ceiling"] = "VERY LOW"
        result["notes"].append(
            "Agent-submitted descriptions are uncorroborated; the specialist ceiling is VERY LOW.",
        )
    return {
        "pipeline": result, "event": event,
        "scope": "Local analysis only; no model calls, network actions or repository changes.",
        "review_is_not_corroboration": True,
        "role": "evidence-specialist" if specialist else "event-review",
        "caller_classification_is_not_verification": True,
    }


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS ambient_meta(version INTEGER NOT NULL);
                INSERT INTO ambient_meta SELECT 1 WHERE NOT EXISTS(SELECT 1 FROM ambient_meta);
                CREATE TABLE IF NOT EXISTS ambient_jobs(
                    id TEXT PRIMARY KEY, provider TEXT NOT NULL, source TEXT NOT NULL,
                    event_id TEXT NOT NULL, event_json TEXT NOT NULL, event_hash TEXT NOT NULL,
                    state TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0,
                    preview_json TEXT, result_json TEXT, updated_at TEXT NOT NULL,
                    UNIQUE(provider,source,event_id));
                CREATE TABLE IF NOT EXISTS ambient_events(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES ambient_jobs(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL,
                    UNIQUE(job_id,version));
                CREATE INDEX IF NOT EXISTS ambient_state_updated
                    ON ambient_jobs(state,updated_at);
                CREATE INDEX IF NOT EXISTS ambient_history_job
                    ON ambient_events(job_id,seq);
                CREATE TABLE IF NOT EXISTS ambient_artifacts(
                    job_id TEXT NOT NULL REFERENCES ambient_jobs(id) ON DELETE CASCADE,
                    name TEXT NOT NULL, content BLOB NOT NULL,
                    PRIMARY KEY(job_id,name));
            """)
            if db.execute("SELECT version FROM ambient_meta").fetchone()[0] not in (1, 2):
                raise ValueError("Unsupported ambient database schema")
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS ambient_filing(
                    job_id TEXT PRIMARY KEY REFERENCES ambient_jobs(id) ON DELETE CASCADE,
                    snapshot TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS ambient_filing_history(
                    job_id TEXT NOT NULL REFERENCES ambient_jobs(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL,
                    PRIMARY KEY(job_id,version));
                CREATE TABLE IF NOT EXISTS ambient_updates(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES ambient_jobs(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS ambient_field_reviews(
                    job_id TEXT NOT NULL REFERENCES ambient_jobs(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL,
                    PRIMARY KEY(job_id,version));
            """)
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT version FROM ambient_meta").fetchone()[0] == 1:
                for row in db.execute("SELECT id,updated_at FROM ambient_jobs").fetchall():
                    self._initialize_filing(db, row["id"], row["updated_at"])
                # Preserve existing SSE cursors; future filing and lifecycle changes share this log.
                db.execute(
                    "INSERT INTO ambient_updates(seq,job_id,kind) "
                    "SELECT seq,job_id,'lifecycle' FROM ambient_events ORDER BY seq",
                )
                db.execute("UPDATE ambient_meta SET version=2")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def _append(
        self, db: sqlite3.Connection, job_id: str, state: str, actor: str, reason: str,
        field_review_hash: str | None = None,
    ) -> None:
        row = db.execute("SELECT * FROM ambient_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise MissingJob(job_id)
        if state not in TRANSITIONS[row["state"]]:
            raise Conflict(f"Illegal transition: {row['state']} -> {state}")
        previous = db.execute(
            "SELECT hash,payload FROM ambient_events WHERE job_id=? ORDER BY seq DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        if state != "AWAITING_APPROVAL" and row["state"] in ("APPROVED", "RUNNING"):
            field_review_hash = json.loads(previous["payload"]).get("field_review_hash")
        version = row["version"] + 1
        timestamp = now()
        payload = canonical({
            "job_id": job_id, "version": version, "from": row["state"], "state": state,
            "actor": actor, "reason": reason, "timestamp": timestamp,
            "previous_hash": previous["hash"],
            "event_hash": row["event_hash"],
            "preview_hash": digest(row["preview_json"]) if row["preview_json"] else None,
            "result_hash": digest(row["result_json"]) if row["result_json"] else None,
            "field_review_hash": field_review_hash,
        })
        db.execute(
            "INSERT INTO ambient_events(job_id,version,payload,hash) VALUES(?,?,?,?)",
            (job_id, version, payload, digest(payload)),
        )
        db.execute(
            "UPDATE ambient_jobs SET state=?,version=?,updated_at=? WHERE id=?",
            (state, version, timestamp, job_id),
        )
        self._notify(db, job_id, "lifecycle")

    @staticmethod
    def _notify(db: sqlite3.Connection, job_id: str, kind: str) -> None:
        db.execute(
            "INSERT INTO ambient_updates(job_id,kind) VALUES(?,?)", (job_id, kind),
        )

    def _initialize_filing(self, db: sqlite3.Connection, job_id: str, timestamp: str) -> None:
        state = FilingState.model_validate_json(canonical({
            "version": 0, "updated_at": timestamp,
        }))
        self._save_filing(db, job_id, state, "system", None)

    @staticmethod
    def _save_filing(
        db: sqlite3.Connection, job_id: str, state: FilingState,
        actor: str, previous_hash: str | None,
    ) -> None:
        snapshot = state.model_dump(mode="json")
        payload = canonical({
            "job_id": job_id, "version": state.version, "actor": actor,
            "timestamp": snapshot["updated_at"], "previous_hash": previous_hash,
            "filing": snapshot,
        })
        db.execute(
            "INSERT INTO ambient_filing_history(job_id,version,payload,hash) VALUES(?,?,?,?)",
            (job_id, state.version, payload, digest(payload)),
        )
        db.execute(
            "INSERT INTO ambient_filing(job_id,snapshot) VALUES(?,?) "
            "ON CONFLICT(job_id) DO UPDATE SET snapshot=excluded.snapshot",
            (job_id, canonical(snapshot)),
        )

    @staticmethod
    def _read_filing(db: sqlite3.Connection, job_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        row = db.execute(
            "SELECT snapshot FROM ambient_filing WHERE job_id=?", (job_id,),
        ).fetchone()
        history = db.execute(
            "SELECT * FROM ambient_filing_history WHERE job_id=? ORDER BY version", (job_id,),
        ).fetchall()
        previous = None
        decoded = []
        for version, entry in enumerate(history):
            event = json.loads(entry["payload"])
            state = FilingState.model_validate_json(canonical(event["filing"]))
            if (
                entry["version"] != version or event["version"] != version
                or state.version != version or event["job_id"] != job_id
                or entry["hash"] != digest(entry["payload"])
                or event["previous_hash"] != previous
                or event["timestamp"] != event["filing"]["updated_at"]
                or not isinstance(event["actor"], str) or not event["actor"].strip()
                or (version == 0 and (
                    state.folder != "inbox" or state.is_read or state.flagged
                    or state.category_color is not None or event["actor"] != "system"
                ))
            ):
                raise ValueError("Filing history integrity mismatch")
            previous = entry["hash"]
            decoded.append({**event, "hash": previous})
        if row is None or not decoded or row["snapshot"] != canonical(decoded[-1]["filing"]):
            raise ValueError("Filing snapshot integrity mismatch")
        return decoded[-1]["filing"], decoded

    def file(self, job_id: str, update: FilingAction, actor: str) -> dict[str, Any]:
        if not actor.strip() or len(actor) > 200:
            raise ValueError("Filing actor must contain 1-200 nonblank characters")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._read(db, job_id)
            current = job["filing"]
            if current["version"] != update.expected_version:
                raise Conflict("Filing is stale; reload the item before changing its organization")
            patch = update.model_dump(mode="json", exclude_unset=True, exclude={"expected_version"})
            if all(current[key] == value for key, value in patch.items()):
                return job
            state = FilingState.model_validate_json(canonical({
                **current, **patch, "version": current["version"] + 1, "updated_at": now(),
            }))
            self._save_filing(db, job_id, state, actor, job["filing_history"][-1]["hash"])
            self._notify(db, job_id, "filing")
            return self._read(db, job_id)

    @staticmethod
    def _field_evidence_ids(event: dict[str, Any]) -> set[str]:
        if event["event_type"] == "agent.analysis.requested":
            return {item["source_id"] for item in event["data"]["evidence"]}
        return {"external-event"}

    def _read_field(self, db: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        history = db.execute(
            "SELECT * FROM ambient_field_reviews WHERE job_id=? ORDER BY version", (row["id"],),
        ).fetchall()
        previous = None
        decoded = []
        ids = self._field_evidence_ids(json.loads(row["event_json"]))
        for version, entry in enumerate(history, start=1):
            record = json.loads(entry["payload"])
            checkpoint = db.execute(
                "SELECT payload FROM ambient_events WHERE job_id=? AND version=?",
                (row["id"], record["job_version"]),
            ).fetchone()
            if (
                entry["version"] != version or record["version"] != version
                or record["job_id"] != row["id"] or record["policy"] != FIELD_POLICY
                or entry["hash"] != digest(entry["payload"]) or record["previous_hash"] != previous
                or record["event_hash"] != row["event_hash"]
                or record["preview_hash"] != (digest(row["preview_json"]) if row["preview_json"] else None)
                or checkpoint is None
                or json.loads(checkpoint["payload"])["state"] != "AWAITING_APPROVAL"
                or json.loads(checkpoint["payload"])["preview_hash"] != record["preview_hash"]
                or not isinstance(record["actor"], str) or not record["actor"].strip()
            ):
                raise ValueError("Knowing Field review integrity mismatch")
            try:
                assessed = assess_field_inquiry(record["assessment"], ids)
            except InvalidFieldInquiry as error:
                raise ValueError("Knowing Field stored assessment integrity mismatch") from error
            if assessed.assessment is None:
                raise ValueError("Knowing Field stored assessment is missing")
            previous = entry["hash"]
            decoded.append({**record, "hash": previous})
        return {
            "status": "HUMAN_COMPLETED" if decoded else (
                "LEGACY_UNASSESSED" if row["state"] == "COMPLETED" else "MISSING"
            ),
            "version": len(decoded), "policy": FIELD_POLICY,
            "assessment": decoded[-1]["assessment"] if decoded else None,
            "history": decoded, "template": field_template(sorted(ids)),
            "validates_experience": False, "grants_authority": False,
        }

    def complete_field_inquiry(
        self, job_id: str, update: FieldInquiryAction, actor: str,
    ) -> dict[str, Any]:
        if not actor.strip() or len(actor) > 200:
            raise ValueError("Field reviewer must contain 1-200 nonblank characters")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._read(db, job_id)
            if job["state"] != "AWAITING_APPROVAL" or job["version"] != update.expected_version:
                raise Conflict("Field inquiry is stale or workflow is not awaiting a release decision")
            field = job["field_review"]
            if field["version"] != update.expected_field_version:
                raise Conflict("Field inquiry revision is stale; reload before completion")
            assessment = assess_field_inquiry(
                update.assessment, self._field_evidence_ids(job["event"]),
            ).assessment
            payload = canonical({
                "job_id": job_id, "version": field["version"] + 1,
                "job_version": job["version"], "actor": actor, "timestamp": now(),
                "policy": FIELD_POLICY, "assessment": assessment,
                "event_hash": digest(canonical(job["event"])),
                "preview_hash": digest(canonical(job["preview"])),
                "previous_hash": field["history"][-1]["hash"] if field["history"] else None,
            })
            db.execute(
                "INSERT INTO ambient_field_reviews(job_id,version,payload,hash) VALUES(?,?,?,?)",
                (job_id, field["version"] + 1, payload, digest(payload)),
            )
            self._notify(db, job_id, "field-inquiry")
            return self._read(db, job_id)

    def ingest(
        self, provider: str, event: AmbientEvent, *,
        artifacts: dict[str, bytes] | None = None,
    ) -> tuple[dict[str, Any], bool]:
        if isinstance(event.data, SnapshotData):
            if provider != "local-capture" or artifacts is None:
                raise ValueError("Snapshots require the approved local capture importer")
            self._verify_artifacts(event.data, artifacts)
        elif artifacts is not None:
            raise ValueError("Artifacts are only supported for local snapshots")
        envelope = event.model_dump(mode="json")
        if envelope["event_type"] == "agent.analysis.requested" and envelope["data"].get("field_inquiry") is None:
            envelope["data"].pop("field_inquiry", None)
        if envelope["event_type"] == "agent.analysis.requested" and envelope["data"].get("game_theory") is None:
            envelope["data"].pop("game_theory", None)
        text = canonical(envelope)
        job_id = uuid.uuid4().hex
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM ambient_jobs WHERE provider=? AND source=? AND event_id=?",
                (provider, event.source, event.event_id),
            ).fetchone()
            if row:
                if row["event_json"] != text:
                    raise Conflict("Delivery ID reused with changed content")
                return self._read(db, row["id"]), False
            timestamp = now()
            db.execute(
                """INSERT INTO ambient_jobs
                (id,provider,source,event_id,event_json,event_hash,state,updated_at)
                VALUES(?,?,?,?,?,?,'PENDING',?)""",
                (job_id, provider, event.source, event.event_id, text, digest(text), timestamp),
            )
            payload = canonical({
                "job_id": job_id, "version": 0, "from": None, "state": "PENDING",
                "actor": provider, "reason": "Authenticated delivery registered",
                "timestamp": timestamp, "previous_hash": None, "event_hash": digest(text),
                "preview_hash": None, "result_hash": None,
            })
            db.execute(
                "INSERT INTO ambient_events(job_id,version,payload,hash) VALUES(?,0,?,?)",
                (job_id, payload, digest(payload)),
            )
            if artifacts:
                db.executemany(
                    "INSERT INTO ambient_artifacts(job_id,name,content) VALUES(?,?,?)",
                    [(job_id, name, content) for name, content in artifacts.items()],
                )
            self._initialize_filing(db, job_id, timestamp)
            self._notify(db, job_id, "lifecycle")
            return self._read(db, job_id), True

    @staticmethod
    def _verify_artifacts(data: SnapshotData, artifacts: dict[str, bytes]) -> None:
        expected = {
            "screenshot.png": data.screenshot_sha256,
            "checks.json": data.checks_sha256, "capture.log": data.log_sha256,
        }
        if set(artifacts) != set(expected) or any(
            len(value) > 8 * 1024 * 1024
            or hashlib.sha256(value).hexdigest() != expected[name]
            for name, value in artifacts.items()
        ) or digest(data.source_html) != data.source_sha256:
            raise ValueError("Snapshot artifact integrity mismatch")
        png = artifacts["screenshot.png"]
        if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
            raise ValueError("Invalid snapshot PNG")
        width, height = int.from_bytes(png[16:20]), int.from_bytes(png[20:24])
        if not 1 <= width <= 1920 or not 1 <= height <= 1080:
            raise ValueError("Snapshot PNG dimensions exceed bounds")
        report = json.loads(artifacts["checks.json"])
        if not isinstance(report, dict) or report.get("request_sha256") != data.request_sha256:
            raise ValueError("Snapshot check report does not match approved request")
        request = report.get("request")
        if not isinstance(request, dict):
            raise TypeError("Snapshot report is missing its approved request")
        approved = {key: value for key, value in request.items() if key != "request_sha256"}
        if (
            digest(canonical(approved)) != data.request_sha256
            or request.get("request_sha256") != data.request_sha256
            or request.get("source_html") != data.source_html
            or request.get("declared_intent") != data.declared_intent
            or request.get("source_sha256") != data.source_sha256
            or report.get("viewport") != {"width": width, "height": height}
            or request.get("viewport") != report.get("viewport")
        ):
            raise ValueError("Snapshot approval or viewport does not match artifacts")

    def _read(self, db: sqlite3.Connection, job_id: str) -> dict[str, Any]:
        row = db.execute("SELECT * FROM ambient_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise MissingJob(job_id)
        history = db.execute(
            "SELECT * FROM ambient_events WHERE job_id=? ORDER BY version", (job_id,),
        ).fetchall()
        previous = None
        state = None
        decoded = []
        for version, entry in enumerate(history):
            event = json.loads(entry["payload"])
            if (
                entry["version"] != version or event["version"] != version
                or entry["hash"] != digest(entry["payload"])
                or event["previous_hash"] != previous or event["from"] != state
                or event["job_id"] != job_id or event["event_hash"] != row["event_hash"]
                or (version == 0 and event["state"] != "PENDING")
                or (version > 0 and event["state"] not in TRANSITIONS.get(state or "", set()))
            ):
                raise ValueError("Workflow history integrity mismatch")
            state, previous = event["state"], entry["hash"]
            decoded.append({**event, "seq": entry["seq"], "hash": entry["hash"]})
        if (
            not decoded or row["version"] != len(history) - 1 or row["state"] != state
            or digest(row["event_json"]) != row["event_hash"]
            or decoded[0]["actor"] != row["provider"]
            or json.loads(row["event_json"])["source"] != row["source"]
            or json.loads(row["event_json"])["event_id"] != row["event_id"]
            or decoded[-1]["preview_hash"] != (
                digest(row["preview_json"]) if row["preview_json"] else None
            )
            or decoded[-1]["result_hash"] != (
                digest(row["result_json"]) if row["result_json"] else None
            )
        ):
            raise ValueError("Workflow snapshot integrity mismatch")
        event_model = AmbientEvent.model_validate_json(row["event_json"])
        artifact_rows = db.execute(
            "SELECT name,content FROM ambient_artifacts WHERE job_id=?", (job_id,),
        ).fetchall()
        if isinstance(event_model.data, SnapshotData):
            self._verify_artifacts(
                event_model.data, {item["name"]: bytes(item["content"]) for item in artifact_rows},
            )
        elif artifact_rows:
            raise ValueError("Unexpected artifacts on non-snapshot workflow")
        filing, filing_history = self._read_filing(db, job_id)
        field_review = self._read_field(db, row)
        reviews = {record["hash"]: record for record in field_review["history"]}
        binding = None
        for checkpoint in decoded:
            if checkpoint["state"] == "APPROVED":
                binding = checkpoint.get("field_review_hash")
            elif checkpoint["state"] == "AWAITING_APPROVAL":
                binding = None
            elif binding is not None and checkpoint.get("field_review_hash") != binding:
                raise ValueError("Knowing Field release binding integrity mismatch")
            bound = checkpoint.get("field_review_hash")
            if bound is not None and (
                bound not in reviews or reviews[bound]["job_version"] >= checkpoint["version"]
            ):
                raise ValueError("Knowing Field approval binding integrity mismatch")
            if bound is not None and checkpoint["state"] == "APPROVED":
                eligible = [record for record in reviews.values()
                            if record["job_version"] < checkpoint["version"]]
                if max(eligible, key=lambda record: record["version"])["hash"] != bound:
                    raise ValueError("Knowing Field approved assessment revision integrity mismatch")
        return {
            "id": row["id"], "provider": row["provider"], "state": row["state"],
            "version": row["version"], "updated_at": row["updated_at"],
            "event": json.loads(row["event_json"]), "history": decoded,
            "preview": json.loads(row["preview_json"]) if row["preview_json"] else None,
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "filing": filing, "filing_history": filing_history,
            "field_review": field_review,
            "artifacts": [{"name": item["name"], "bytes": len(item["content"])}
                          for item in artifact_rows],
        }

    def artifact(self, job_id: str, name: str) -> bytes:
        with self.connection() as db:
            db.execute("BEGIN")
            self._read(db, job_id)
            row = db.execute(
                "SELECT content FROM ambient_artifacts WHERE job_id=? AND name=?", (job_id, name),
            ).fetchone()
            if row is None:
                raise MissingJob(f"{job_id}/{name}")
            return bytes(row["content"])

    def get(self, job_id: str) -> dict[str, Any]:
        with self.connection() as db:
            db.execute("BEGIN")
            return self._read(db, job_id)

    def list_jobs(self, limit: int = 50, before: str | None = None) -> list[dict[str, Any]]:
        with self.connection() as db:
            db.execute("BEGIN")
            rows = db.execute(
                "SELECT id FROM ambient_jobs WHERE (? IS NULL OR id<?) ORDER BY id DESC LIMIT ?",
                (before, before, limit),
            ).fetchall()
            return [self._read(db, row["id"]) for row in rows]

    def action(
        self, job_id: str, action: str, actor: str, reason: str, version: int,
        field_version: int | None = None,
    ) -> dict[str, Any]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._read(db, job_id)
            if job["version"] != version or job["state"] != "AWAITING_APPROVAL":
                raise Conflict("Review is stale or workflow is not awaiting approval")
            if action not in ("approve", "reject"):
                raise ValueError("Unsupported review action")
            if action == "approve" and not job["preview"]["pipeline"]["harm_gate"]["cleared"]:
                raise Conflict("Harm Gate blocks report release")
            if action == "approve" and (
                job["field_review"]["status"] != "HUMAN_COMPLETED"
                or field_version != job["field_review"]["version"]
            ):
                raise Conflict("Knowing Field completion is missing or stale; complete human inquiry before approval")
            self._append(
                db, job_id, "APPROVED" if action == "approve" else "REJECTED", actor, reason,
                job["field_review"]["history"][-1]["hash"] if action == "approve" else None,
            )
            return self._read(db, job_id)

    def work_once(self) -> bool:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id FROM ambient_jobs WHERE state IN ('PENDING','APPROVED') "
                "ORDER BY updated_at LIMIT 1",
            ).fetchone()
            if row is None:
                return False
            job_id = row["id"]
            job = self._read(db, job_id)
            if job["state"] == "APPROVED" and (
                job["field_review"]["status"] != "HUMAN_COMPLETED"
                or not job["preview"]["pipeline"]["harm_gate"]["cleared"]
            ):
                self._append(
                    db, job_id, "AWAITING_APPROVAL", "worker",
                    "Release policy requires completed Knowing Field inquiry and Harm Gate review",
                )
                return True
            self._append(db, job_id, "RUNNING", "worker", "Bounded local analysis")
            if job["state"] == "PENDING":
                try:
                    analysis = analyze(job["event"])
                    if job["event"]["event_type"] == "static.snapshot":
                        report = db.execute(
                            "SELECT content FROM ambient_artifacts WHERE job_id=? AND name='checks.json'",
                            (job_id,),
                        ).fetchone()
                        analysis["capture_checks"] = json.loads(report["content"])
                    preview = canonical(analysis)
                except (ValueError, KeyError, TypeError) as error:
                    LOG.exception("Ambient analysis failed for job %s", job_id)
                    self._append(db, job_id, "FAILED", "worker", f"Analysis failed: {type(error).__name__}")
                    return True
                db.execute("UPDATE ambient_jobs SET preview_json=? WHERE id=?", (preview, job_id))
                self._append(db, job_id, "AWAITING_APPROVAL", "worker", "Review analysis before release")
            else:
                db.execute(
                    "UPDATE ambient_jobs SET result_json=preview_json WHERE id=?", (job_id,),
                )
                self._append(db, job_id, "COMPLETED", "worker", "Approved report persisted; no external action")
            return True

    def changes(self, after: int, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT seq,job_id FROM ambient_updates WHERE seq>? ORDER BY seq LIMIT ?",
                (after, limit),
            )]

    def stats(self) -> dict[str, Any]:
        with self.connection() as db:
            return {
                "states": dict(db.execute(
                    "SELECT state,COUNT(*) FROM ambient_jobs GROUP BY state",
                ).fetchall()),
                "history_events": db.execute("SELECT COUNT(*) FROM ambient_events").fetchone()[0],
                "retention": "Preserved until explicit pruning or reset",
            }

    def prune(self, days: int, apply: bool = False) -> int:
        if days < 1:
            raise ValueError("Retention days must be positive")
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            ids = [row["id"] for row in db.execute(
                "SELECT id FROM ambient_jobs WHERE state IN (?,?,?) AND updated_at<?",
                (*TERMINAL, cutoff),
            )]
            for job_id in ids:
                self._read(db, job_id)
            if apply:
                db.executemany("DELETE FROM ambient_jobs WHERE id=?", [(i,) for i in ids])
            return len(ids)

    def reset(self, confirmation: str) -> None:
        if confirmation != str(self.path):
            raise ValueError("Confirm reset with the exact resolved database path")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT COUNT(*) FROM ambient_jobs WHERE state NOT IN (?,?,?)", TERMINAL,
            ).fetchone()[0]:
                raise Conflict("Cannot reset while nonterminal jobs remain")
            db.execute("DELETE FROM ambient_jobs")
