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

from .models import AmbientEvent

LOG = logging.getLogger(__name__)
TERMINAL = ("COMPLETED", "REJECTED", "FAILED")
TRANSITIONS = {
    "PENDING": {"RUNNING", "FAILED"},
    "RUNNING": {"AWAITING_APPROVAL", "COMPLETED", "FAILED"},
    "AWAITING_APPROVAL": {"APPROVED", "REJECTED"},
    "APPROVED": {"RUNNING", "FAILED"},
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
    case = {
        "title": f"Ambient review: {event['event_type']}",
        "subject": event["source"],
        "decision_question": "What does this reported event establish for local review?",
        "domain": "Local event analysis",
        "evidence": [{
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
    result = asdict(run_case_pipeline(case, track_provenance=False))
    return {
        "pipeline": result, "event": event,
        "scope": "Local analysis only; no model calls, network actions or repository changes.",
        "review_is_not_corroboration": True,
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
            """)
            if db.execute("SELECT version FROM ambient_meta").fetchone()[0] != 1:
                raise ValueError("Unsupported ambient database schema")
            db.execute("PRAGMA journal_mode=WAL")

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
    ) -> None:
        row = db.execute("SELECT * FROM ambient_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise MissingJob(job_id)
        if state not in TRANSITIONS[row["state"]]:
            raise Conflict(f"Illegal transition: {row['state']} -> {state}")
        previous = db.execute(
            "SELECT hash FROM ambient_events WHERE job_id=? ORDER BY seq DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        version = row["version"] + 1
        timestamp = now()
        payload = canonical({
            "job_id": job_id, "version": version, "from": row["state"], "state": state,
            "actor": actor, "reason": reason, "timestamp": timestamp,
            "previous_hash": previous["hash"],
            "event_hash": row["event_hash"],
            "preview_hash": digest(row["preview_json"]) if row["preview_json"] else None,
            "result_hash": digest(row["result_json"]) if row["result_json"] else None,
        })
        db.execute(
            "INSERT INTO ambient_events(job_id,version,payload,hash) VALUES(?,?,?,?)",
            (job_id, version, payload, digest(payload)),
        )
        db.execute(
            "UPDATE ambient_jobs SET state=?,version=?,updated_at=? WHERE id=?",
            (state, version, timestamp, job_id),
        )

    def ingest(self, provider: str, event: AmbientEvent) -> tuple[dict[str, Any], bool]:
        text = canonical(event.model_dump(mode="json"))
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
            return self._read(db, job_id), True

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
        return {
            "id": row["id"], "provider": row["provider"], "state": row["state"],
            "version": row["version"], "updated_at": row["updated_at"],
            "event": json.loads(row["event_json"]), "history": decoded,
            "preview": json.loads(row["preview_json"]) if row["preview_json"] else None,
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
        }

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

    def action(self, job_id: str, action: str, actor: str, reason: str, version: int) -> dict[str, Any]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._read(db, job_id)
            if job["version"] != version or job["state"] != "AWAITING_APPROVAL":
                raise Conflict("Review is stale or workflow is not awaiting approval")
            if action not in ("approve", "reject"):
                raise ValueError("Unsupported review action")
            if action == "approve" and not job["preview"]["pipeline"]["harm_gate"]["cleared"]:
                raise Conflict("Harm Gate blocks report release")
            self._append(db, job_id, "APPROVED" if action == "approve" else "REJECTED", actor, reason)
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
            self._append(db, job_id, "RUNNING", "worker", "Bounded local analysis")
            if job["state"] == "PENDING":
                try:
                    preview = canonical(analyze(job["event"]))
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
                "SELECT seq,job_id FROM ambient_events WHERE seq>? ORDER BY seq LIMIT ?",
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
