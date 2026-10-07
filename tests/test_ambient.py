import hashlib
import hmac
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from vessell.ambient.api import Settings, create_app, normalize
from vessell.ambient.cli import main
from vessell.ambient.models import AmbientEvent
from vessell.ambient.store import Conflict, Store

ADMIN = "admin-test-secret-" * 3
INGEST = "ingest-test-secret-" * 3
WEBHOOK = "webhook-test-secret-" * 3


def event_dict(event_id="test-1"):
    return {
        "event_id": event_id, "source": "owner/repository", "event_type": "vcs.push",
        "timestamp": "2026-10-07T12:00:00Z",
        "data": {
            "domain": "vcs", "repository": "owner/repository",
            "branch": "refs/heads/main", "commit_sha": "a" * 40, "author": "Test author",
        },
    }


def event(event_id="test-1"):
    return AmbientEvent.model_validate_json(json.dumps(event_dict(event_id)))


def ready(store):
    job, _ = store.ingest("manual", event())
    assert store.work_once()
    return store.get(job["id"])


def test_restart_review_release_and_integrity(tmp_path):
    path = tmp_path / "ambient.sqlite"
    store = Store(path)
    job = ready(store)
    assert job["state"] == "AWAITING_APPROVAL"
    assert job["preview"]["pipeline"]["confidence_ceiling"] == "VERY LOW"
    assert job["preview"]["pipeline"]["harm_gate"]["cleared"]
    store = Store(path)
    job = store.action(job["id"], "approve", "reviewer", "Release local report only", job["version"])
    assert job["state"] == "APPROVED"
    assert Store(path).work_once()
    result = Store(path).get(job["id"])
    assert result["state"] == "COMPLETED"
    assert result["result"] == result["preview"]
    assert result["result"]["review_is_not_corroboration"]
    assert [e["state"] for e in result["history"]] == [
        "PENDING", "RUNNING", "AWAITING_APPROVAL", "APPROVED", "RUNNING", "COMPLETED",
    ]
    with pytest.raises(Conflict):
        store.action(job["id"], "approve", "reviewer", "Retry", result["version"])


def test_concurrent_duplicate_registration_and_worker_are_atomic(tmp_path):
    path = tmp_path / "ambient.sqlite"
    Store(path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: Store(path).ingest("github", event()), range(16)))
    assert len({j["id"] for j, _ in results}) == 1
    assert sum(created for _, created in results) == 1
    with ThreadPoolExecutor(max_workers=4) as pool:
        processed = list(pool.map(lambda _: Store(path).work_once(), range(8)))
    assert sum(processed) == 1
    job = Store(path).get(results[0][0]["id"])
    assert len(job["history"]) == 3


def test_namespace_and_changed_duplicate(tmp_path):
    store = Store(tmp_path / "a.sqlite")
    github, _ = store.ingest("github", event())
    gitlab, _ = store.ingest("gitlab", event())
    assert github["id"] != gitlab["id"]
    changed = event_dict()
    changed["data"]["author"] = "different"
    with pytest.raises(Conflict, match="changed content"):
        store.ingest("github", AmbientEvent.model_validate_json(json.dumps(changed)))
    changed["source"] = "other/repo"
    _, created = store.ingest("github", AmbientEvent.model_validate_json(json.dumps(changed)))
    assert created


def test_competing_review_actions_only_one_wins(tmp_path):
    store = Store(tmp_path / "a.sqlite")
    job = ready(store)

    def review(action):
        try:
            return store.action(job["id"], action, "reviewer", "Explicit reason", job["version"])["state"]
        except Conflict:
            return "CONFLICT"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(review, ["approve", "reject"]))
    assert results.count("CONFLICT") == 1
    assert store.get(job["id"])["version"] == job["version"] + 1


def test_rejection_is_not_completion(tmp_path):
    store = Store(tmp_path / "a.sqlite")
    job = ready(store)
    rejected = store.action(job["id"], "reject", "reviewer", "Insufficient evidence", job["version"])
    assert rejected["state"] == "REJECTED"
    assert rejected["result"] is None
    assert not store.work_once()


def test_worker_rollback_resumes_pending_after_failure(tmp_path, monkeypatch):
    store = Store(tmp_path / "a.sqlite")
    job, _ = store.ingest("manual", event())
    original = store._append

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("simulated interruption before transaction commit")

    monkeypatch.setattr(store, "_append", fail)
    with pytest.raises(OSError):
        store.work_once()
    restored = Store(store.path)
    assert restored.get(job["id"])["state"] == "PENDING"
    assert restored.work_once()
    assert restored.get(job["id"])["state"] == "AWAITING_APPROVAL"


def test_analysis_failure_is_recorded_not_success(tmp_path, monkeypatch, caplog):
    store = Store(tmp_path / "a.sqlite")
    job, _ = store.ingest("manual", event())

    def broken(_):
        raise ValueError("analysis failure")

    monkeypatch.setattr("vessell.ambient.store.analyze", broken)
    assert store.work_once()
    assert store.get(job["id"])["state"] == "FAILED"
    assert "analysis failed" in caplog.text


@pytest.mark.parametrize("target", ["event", "preview", "history", "state", "delete"])
def test_tampering_detected(tmp_path, target):
    store = Store(tmp_path / "a.sqlite")
    job = ready(store)
    with sqlite3.connect(store.path) as db:
        if target == "event":
            db.execute("UPDATE ambient_jobs SET event_json='{}'")
        elif target == "preview":
            db.execute("UPDATE ambient_jobs SET preview_json='{}'")
        elif target == "history":
            db.execute("UPDATE ambient_events SET payload='{}' WHERE version=1")
        elif target == "state":
            db.execute("UPDATE ambient_jobs SET state='COMPLETED'")
        else:
            db.execute("DELETE FROM ambient_events WHERE version=1")
    with pytest.raises((ValueError, KeyError)):
        store.get(job["id"])


def test_prune_keeps_live_dedupe_and_requires_explicit_apply(tmp_path):
    store = Store(tmp_path / "a.sqlite")
    job = ready(store)
    store.action(job["id"], "reject", "reviewer", "Not needed", job["version"])
    live, _ = store.ingest("manual", event("live"))
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE ambient_jobs SET updated_at='2000-01-01T00:00:00+00:00'")
    assert store.prune(7) == 1
    assert len(store.list_jobs()) == 2
    assert store.prune(7, True) == 1
    assert store.get(live["id"])["state"] == "PENDING"
    assert not store.ingest("manual", event("live"))[1]
    assert store.ingest("manual", event())[1]
    with pytest.raises(ValueError):
        store.prune(0)
    with pytest.raises(ValueError):
        store.reset("incorrect path")
    with pytest.raises(Conflict):
        store.reset(str(store.path))


def test_reset_foreign_keys_and_history_cursor(tmp_path):
    store = Store(tmp_path / "a.sqlite")
    job = ready(store)
    first = store.changes(0)
    assert len(first) == 3
    assert store.changes(first[-1]["seq"]) == []
    store.action(job["id"], "reject", "reviewer", "reset fixture", job["version"])
    store.reset(str(store.path))
    assert store.list_jobs() == []
    assert store.stats()["history_events"] == 0
    assert store.ingest("manual", event())[0]["history"][0]["seq"] > first[-1]["seq"]


@pytest.mark.parametrize("change", [
    {"timestamp": "2026-10-07T12:00:00"},
    {"event_id": ""},
    {"event_type": "alert.triggered"},
    {"unknown": "field"},
])
def test_envelope_validation(change):
    data = event_dict()
    data.update(change)
    with pytest.raises(ValidationError):
        AmbientEvent.model_validate_json(json.dumps(data))


def test_settings_fail_closed(tmp_path):
    with pytest.raises(ValueError):
        Settings(tmp_path / "a.sqlite", "", "")
    with pytest.raises(ValueError):
        Settings(tmp_path / "a.sqlite", ADMIN, ADMIN)


def test_approval_cannot_bypass_harm_gate(tmp_path, monkeypatch):
    from vessell.ambient.store import analyze

    def blocked(data):
        result = analyze(data)
        result["pipeline"]["harm_gate"]["cleared"] = False
        return result

    monkeypatch.setattr("vessell.ambient.store.analyze", blocked)
    store = Store(tmp_path / "a.sqlite")
    job = ready(store)
    with pytest.raises(Conflict, match="Harm Gate"):
        store.action(job["id"], "approve", "reviewer", "Not a waiver", job["version"])
    assert store.action(job["id"], "reject", "reviewer", "Blocked", job["version"])["state"] == "REJECTED"


def test_webhook_disabled_without_secret(tmp_path):
    with TestClient(create_app(Settings(tmp_path / "a.sqlite", ADMIN, INGEST))) as client:
        assert client.post("/api/v1/ingress/github", content=b"{}").status_code == 503


def test_sqlite_indexes_and_single_schema_version(tmp_path):
    store = Store(tmp_path / "a.sqlite")
    with store.connection() as db:
        indexes = {row["name"] for row in db.execute("PRAGMA index_list(ambient_jobs)")}
        assert "ambient_state_updated" in indexes
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        db.execute("UPDATE ambient_meta SET version=999")
    with pytest.raises(ValueError, match="Unsupported"):
        Store(store.path)


@pytest.fixture
def api(tmp_path):
    config = Settings(tmp_path / "api.sqlite", ADMIN, INGEST, WEBHOOK, WEBHOOK)
    with TestClient(create_app(config)) as client:
        yield client


def wait_state(client, job_id, state):
    for _ in range(80):
        response = client.get(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {ADMIN}"})
        if response.json()["state"] == state:
            return response.json()
        time.sleep(0.025)
    pytest.fail(f"Job did not reach {state}")


def test_authenticated_api_and_worker_resume(api):
    assert api.get("/health").status_code == 200
    assert api.get("/api/v1/jobs").status_code == 401
    assert api.post("/api/v1/events", json=event_dict()).status_code == 401
    response = api.post("/api/v1/events", json=event_dict(), headers={"Authorization": f"Bearer {INGEST}"})
    assert response.status_code == 202
    job = wait_state(api, response.json()["id"], "AWAITING_APPROVAL")
    path = f"/api/v1/jobs/{job['id']}/action"
    action = {"action": "approve", "reason": "Reviewed local analysis", "expected_version": job["version"]}
    assert api.post(path, json=action, headers={"Authorization": f"Bearer {INGEST}"}).status_code == 401
    assert api.post(path, json={**action, "reason": "  "}, headers={"Authorization": f"Bearer {ADMIN}"}).status_code == 422
    assert api.post(path, json=action, headers={"Authorization": f"Bearer {ADMIN}"}).status_code == 200
    assert wait_state(api, job["id"], "COMPLETED")["result"]
    assert api.post(path, json=action, headers={"Authorization": f"Bearer {ADMIN}"}).status_code == 409
    assert api.get("/api/v1/jobs?limit=101", headers={"Authorization": f"Bearer {ADMIN}"}).status_code == 422
    assert api.get("/api/v1/jobs/missing", headers={"Authorization": f"Bearer {ADMIN}"}).status_code == 404


def push_payload(provider):
    base = {"ref": "refs/heads/main", "after": "b" * 40}
    if provider == "github":
        return {**base, "repository": {"full_name": "owner/repo"}, "pusher": {"name": "author"},
                "head_commit": {"timestamp": "2026-10-07T12:00:00Z"}}
    return {**base, "project": {"path_with_namespace": "owner/repo"}, "user_username": "author",
            "commits": [{"timestamp": "2026-10-07T12:00:00Z"}]}


@pytest.mark.parametrize("provider", ["github", "gitlab"])
def test_webhook_authentication_retries_and_changed_delivery(api, provider):
    payload = push_payload(provider)
    raw = json.dumps(payload).encode()

    def headers(content):
        if provider == "github":
            return {
                "x-hub-signature-256": "sha256=" + hmac.new(WEBHOOK.encode(), content, hashlib.sha256).hexdigest(),
                "x-github-delivery": "delivery-1", "x-github-event": "push",
            }
        return {"x-gitlab-token": WEBHOOK, "x-gitlab-event-uuid": "delivery-1",
                "x-gitlab-event": "Push Hook"}

    path = f"/api/v1/ingress/{provider}"
    assert api.post(path, content=raw).status_code == 401
    response = api.post(path, content=raw, headers=headers(raw))
    assert response.status_code == 202
    duplicate = api.post(path, content=raw, headers=headers(raw))
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == response.json()["id"]
    changed = json.dumps({**payload, "after": "c" * 40}).encode()
    assert api.post(path, content=changed, headers=headers(changed)).status_code == 409
    assert api.post(path, content=b"[]", headers=headers(b"[]")).status_code == 422


def test_bounded_body_bad_json_and_monitoring(api):
    headers = {"Authorization": f"Bearer {INGEST}"}
    assert api.post("/api/v1/events", content=b"x" * (65536 + 1), headers=headers).status_code == 413
    assert api.post("/api/v1/events", content=b"bad", headers=headers).status_code == 422
    data = {
        "event_id": "alert-1", "source": "monitor/service", "event_type": "alert.triggered",
        "timestamp": "2026-10-07T12:00:00Z",
        "data": {"domain": "monitoring", "alert_id": "alert-1", "service_name": "service",
                 "severity": "critical", "summary": "Reported availability issue"},
    }
    assert api.post("/api/v1/events", json=data, headers=headers).status_code == 202
    assert api.get("/api/v1/stream").status_code == 401
    assert api.get("/api/v1/stream", headers={"Authorization": f"Bearer {ADMIN}", "Last-Event-ID": "bad"}).status_code == 422
    assert api.get("/api/v1/stream", headers={"Authorization": f"Bearer {ADMIN}", "Last-Event-ID": "-1"}).status_code == 422


def test_cli_requires_existing_database_and_explicit_reset(tmp_path, monkeypatch, capsys):
    path = tmp_path / "a.sqlite"
    monkeypatch.setattr("sys.argv", ["vessell-ambient", "--database", str(path), "status"])
    assert main() == 2
    assert not path.exists()
    monkeypatch.setattr("sys.argv", ["vessell-ambient", "--database", str(path), "init"])
    assert main() == 0
    monkeypatch.setattr("sys.argv", ["vessell-ambient", "--database", str(path), "verify"])
    assert main() == 0
    assert "Verified 0" in capsys.readouterr().out


def test_malformed_and_deletion_pushes_rejected():
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        normalize("github", "delivery", {})
    payload = push_payload("github")
    payload["after"] = "0" * 40
    with pytest.raises(HTTPException):
        normalize("github", "delivery", payload)
