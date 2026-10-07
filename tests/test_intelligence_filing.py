import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from vessell.ambient.api import Settings, create_app
from vessell.ambient.models import AmbientEvent, FieldInquiryAction, FilingAction
from vessell.ambient.store import Conflict, Store


def event():
    return AmbientEvent.model_validate_json(json.dumps({
        "event_id": "filing-test", "source": "test/service",
        "event_type": "alert.triggered", "timestamp": "2026-10-07T12:00:00Z",
        "data": {"domain": "monitoring", "alert_id": "a1", "service_name": "test",
                 "severity": "info", "summary": "Uncorroborated test report"},
    }))


def test_persistent_filing_is_independent_of_evidence_review_and_replay(tmp_path, field_assessment):
    store = Store(tmp_path / "workspace.sqlite")
    job, _ = store.ingest("manual", event())
    assert job["filing"]["folder"] == "inbox"
    assert not job["filing"]["is_read"] and not job["filing"]["flagged"]
    assert job["filing"]["category_color"] is None
    assert store.work_once()
    original = store.get(job["id"])
    changed = store.file(job["id"], FilingAction(
        expected_version=0, folder="market", is_read=True, flagged=True, category_color="purple",
    ), "human-reviewer")
    for key in ("version", "state", "event", "preview", "result", "history", "updated_at"):
        assert changed[key] == original[key]
    assert changed["filing"]["version"] == 1
    assert changed["filing_history"][-1]["actor"] == "human-reviewer"
    reopened = Store(store.path)
    assert reopened.get(job["id"]) == changed
    replay, created = reopened.ingest("manual", event())
    assert not created and replay == changed
    archived = reopened.file(job["id"], FilingAction(
        expected_version=1, folder="archive", is_read=False, category_color=None,
    ), "human-reviewer")
    assert archived["state"] == "AWAITING_APPROVAL" and archived["result"] is None
    assert archived["filing"]["folder"] == "archive"
    assert archived["filing"]["flagged"] and not archived["filing"]["is_read"]
    assert archived["filing"]["category_color"] is None
    reopened.complete_field_inquiry(job["id"], FieldInquiryAction(
        expected_version=original["version"], expected_field_version=0, assessment=field_assessment,
    ), "human-reviewer")
    reopened.action(job["id"], "approve", "human-reviewer", "Release report, not truth", original["version"], 1)
    reopened.work_once()
    released = reopened.get(job["id"])
    assert released["state"] == "COMPLETED"
    assert released["result"] == original["preview"]
    assert released["filing"] == archived["filing"]


def test_filing_replay_notifications_and_stale_updates(tmp_path):
    store = Store(tmp_path / "workspace.sqlite")
    job, _ = store.ingest("manual", event())
    cursor = store.changes(0)[-1]["seq"]
    assert store.file(job["id"], FilingAction(expected_version=0, is_read=False), "reviewer") == job
    assert store.changes(cursor) == []
    store.file(job["id"], FilingAction(expected_version=0, flagged=True), "reviewer")
    change = store.changes(cursor)
    assert len(change) == 1 and change[0]["job_id"] == job["id"]
    with pytest.raises(Conflict, match="stale"):
        store.file(job["id"], FilingAction(expected_version=0, flagged=True), "reviewer")
    assert store.work_once()
    replay = Store(store.path).changes(cursor)
    assert len(replay) == 3
    assert [row["seq"] for row in replay] == sorted({row["seq"] for row in replay})
    assert store.changes(cursor, limit=1) == change


def test_competing_filings_conflict_but_filing_and_review_do_not(tmp_path):
    store = Store(tmp_path / "workspace.sqlite")
    job, _ = store.ingest("manual", event())
    store.work_once()
    job = store.get(job["id"])

    def file(folder):
        try:
            store.file(job["id"], FilingAction(expected_version=0, folder=folder), "reviewer")
            return "filed"
        except Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(file, ("market", "policy"))) == ["conflict", "filed"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        filing = pool.submit(store.file, job["id"], FilingAction(expected_version=1, flagged=True), "reviewer")
        review = pool.submit(store.action, job["id"], "reject", "reviewer", "Insufficient evidence", job["version"])
        filing.result()
        review.result()
    result = store.get(job["id"])
    assert result["state"] == "REJECTED"
    assert result["filing"]["version"] == 2 and result["filing"]["flagged"]


@pytest.mark.parametrize("patch", [
    {}, {"folder": "trash"}, {"folder": None}, {"category_color": "pink"},
    {"is_read": 1}, {"flagged": "yes"}, {"expected_version": -1},
    {"expected_version": True}, {"actor": "spoof"}, {"state": "COMPLETED"},
])
def test_strict_filing_contract(patch):
    with pytest.raises(ValidationError):
        FilingAction.model_validate_json(json.dumps({"expected_version": 0, **patch}))


@pytest.mark.parametrize("target", ["snapshot", "hash", "delete", "invalid-state"])
def test_filing_integrity_failures_are_explicit(tmp_path, target):
    store = Store(tmp_path / "workspace.sqlite")
    job, _ = store.ingest("manual", event())
    store.file(job["id"], FilingAction(expected_version=0, folder="market"), "reviewer")
    with sqlite3.connect(store.path) as db:
        if target == "snapshot":
            db.execute("UPDATE ambient_filing SET snapshot='{}'")
        elif target == "hash":
            db.execute("UPDATE ambient_filing_history SET hash='bad' WHERE version=1")
        elif target == "delete":
            db.execute("DELETE FROM ambient_filing_history WHERE version=0")
        else:
            db.execute("UPDATE ambient_filing_history SET payload='{}' WHERE version=1")
    with pytest.raises((ValueError, KeyError)):
        Store(store.path).get(job["id"])


def test_v1_migration_preserves_jobs_and_existing_sse_cursors(tmp_path):
    store = Store(tmp_path / "workspace.sqlite")
    job, _ = store.ingest("manual", event())
    store.work_once()
    original = store.get(job["id"])
    original_changes = store.changes(0)
    with sqlite3.connect(store.path) as db:
        db.execute("DROP TABLE ambient_filing")
        db.execute("DROP TABLE ambient_filing_history")
        db.execute("DROP TABLE ambient_updates")
        db.execute("UPDATE ambient_meta SET version=1")
    migrated = Store(store.path)
    result = migrated.get(job["id"])
    for key in ("version", "state", "event", "preview", "result", "history", "updated_at"):
        assert result[key] == original[key]
    assert result["filing"]["folder"] == "inbox" and result["filing"]["version"] == 0
    assert migrated.changes(0) == original_changes
    cursor = original_changes[-1]["seq"]
    migrated.file(job["id"], FilingAction(expected_version=0, flagged=True), "reviewer")
    assert Store(store.path).changes(cursor)[0]["seq"] > cursor
    assert Store(store.path).get(job["id"])["filing"]["flagged"]


def test_explicit_pruning_cascades_filing_and_notifications(tmp_path):
    store = Store(tmp_path / "workspace.sqlite")
    job, _ = store.ingest("manual", event())
    store.work_once()
    store.file(job["id"], FilingAction(expected_version=0, folder="archive"), "reviewer")
    store.action(job["id"], "reject", "reviewer", "Insufficient evidence", store.get(job["id"])["version"])
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE ambient_jobs SET updated_at='2000-01-01T00:00:00+00:00'")
    assert store.prune(30, apply=True) == 1
    with sqlite3.connect(store.path) as db:
        for table in ("ambient_filing", "ambient_filing_history", "ambient_updates"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_filing_api_requires_human_authority_and_exposes_typed_contract(tmp_path):
    admin_token, ingest_token = "filing-admin-test-" * 3, "filing-ingest-test-" * 3
    app = create_app(Settings(tmp_path / "workspace.sqlite", admin_token, ingest_token, reviewer_identity="configured-human"))
    job, _ = app.state.store.ingest("manual", event())
    path = f"/api/v1/jobs/{job['id']}/filing"
    patch = {"expected_version": 0, "folder": "market", "is_read": True}
    with TestClient(app) as client:
        assert client.post(path, json=patch).status_code == 401
        assert client.post(path, json=patch, headers={"Authorization": f"Bearer {ingest_token}"}).status_code == 401
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post(path, json=patch, headers=headers)
        assert response.status_code == 200
        assert response.json()["filing_history"][-1]["actor"] == "configured-human"
        assert client.post(path, json=patch, headers=headers).status_code == 409
        assert client.post(path, json={"expected_version": 1}, headers=headers).status_code == 422
        assert client.post(path.replace(job["id"], "0" * 32), json=patch, headers=headers).status_code == 404
        assert "FilingAction" in client.get("/openapi.json").json()["components"]["schemas"]
