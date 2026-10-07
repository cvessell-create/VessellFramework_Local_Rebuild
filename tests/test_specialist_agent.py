import io
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

import pytest
from fastapi.testclient import TestClient

from vessell.ambient.api import Settings, create_app
from vessell.ambient.models import AmbientEvent
from vessell.ambient.specialist import (
    NoRedirect,
    SpecialistClient,
    SpecialistClientError,
    SpecialistTask,
)
from vessell.ambient.store import Store

ADMIN = "specialist-admin-test-only-" * 3
INGEST = "specialist-ingest-test-only-" * 3


def payload():
    return {
        "task_id": "task-001", "caller": "parent-agent",
        "timestamp": "2026-10-07T12:00:00Z",
        "question": "What does the reported configuration change establish?",
        "evidence": [
            {"source_id": "report-a", "description": "Caller reports a changed setting."},
            {"source_id": "report-b", "description": "A copied report repeats the claim.",
             "upstream_of": "report-a"},
        ],
    }


def test_reusable_specialist_replay_read_review_and_release(tmp_path, field_assessment):
    app = create_app(Settings(tmp_path / "agent.sqlite", ADMIN, INGEST))
    ingest = {"Authorization": f"Bearer {INGEST}"}
    admin = {"Authorization": f"Bearer {ADMIN}"}
    with TestClient(app) as client:
        assert client.post("/api/v1/agent/tasks", json=payload()).status_code == 401
        first = client.post("/api/v1/agent/tasks", json=payload(), headers=ingest)
        assert first.status_code == 202
        job_id = first.json()["id"]
        replay = client.post("/api/v1/agent/tasks", json=payload(), headers=ingest)
        assert replay.status_code == 200 and replay.json()["id"] == job_id
        changed = payload()
        changed["question"] = "Changed question under the same identity"
        assert client.post("/api/v1/agent/tasks", json=changed, headers=ingest).status_code == 409
        app.state.store.work_once()
        job = client.get(f"/api/v1/agent/tasks/{job_id}", headers=ingest).json()
        assert job["state"] == "AWAITING_APPROVAL"
        assert job["result"] is None
        assert job["preview"]["role"] == "evidence-specialist"
        assert job["preview"]["pipeline"]["counts"]["working_hypothesis"] == 2
        assert job["preview"]["pipeline"]["counts"]["source_established"] == 0
        assert job["preview"]["pipeline"]["confidence_ceiling"] == "VERY LOW"
        action = {"action": "approve", "expected_version": job["version"],
                  "reason": "Release analysis, not corroboration", "expected_field_version": 1}
        assert client.post(f"/api/v1/jobs/{job_id}/action", json=action, headers=admin).status_code == 409
        field_assessment["evidence_ids"] = ["report-a", "report-b"]
        completion = {"expected_version": job["version"], "expected_field_version": 0,
                      "assessment": field_assessment}
        assert client.post(f"/api/v1/jobs/{job_id}/field-inquiry", json=completion, headers=ingest).status_code == 401
        assert client.post(f"/api/v1/jobs/{job_id}/field-inquiry", json=completion, headers=admin).status_code == 200
        assert client.post(f"/api/v1/jobs/{job_id}/action", json=action, headers=ingest).status_code == 401
        assert client.get(f"/api/v1/jobs/{job_id}", headers=ingest).status_code == 401
        assert client.post(f"/api/v1/jobs/{job_id}/action", json=action, headers=admin).status_code == 200
        app.state.store.work_once()
        released = client.get(f"/api/v1/agent/tasks/{job_id}", headers=ingest).json()
        assert released["state"] == "COMPLETED" and released["result"] == job["preview"]
    reopened = Store(tmp_path / "agent.sqlite").get(job_id)
    assert reopened["result"] == released["result"]
    assert len(reopened["history"]) == 6


@pytest.mark.parametrize("change", ["naive-time", "duplicate-source", "self-verify", "oversize", "unknown-field"])
def test_invalid_agent_contract_is_explicitly_rejected(tmp_path, change):
    value = payload()
    if change == "naive-time":
        value["timestamp"] = "2026-10-07T12:00:00"
    elif change == "duplicate-source":
        value["evidence"][1]["source_id"] = "report-a"
    elif change == "self-verify":
        value["evidence"][0]["status"] = "SOURCE-ESTABLISHED"
    elif change == "oversize":
        value["evidence"][0]["description"] = "x" * 2001
    else:
        value["command"] = "not-an-execution-interface"
    app = create_app(Settings(tmp_path / "agent.sqlite", ADMIN, INGEST))
    with TestClient(app) as client:
        response = client.post("/api/v1/agent/tasks", json=value, headers={"Authorization": f"Bearer {INGEST}"})
        assert response.status_code == 422 and response.json()["detail"]
    assert app.state.store.list_jobs() == []


def test_unknown_lineage_cannot_raise_uncorroborated_confidence(tmp_path):
    value = payload()
    value["evidence"][1]["upstream_of"] = "missing-source"
    task = SpecialistTask.model_validate_json(json.dumps(value))
    store = Store(tmp_path / "lineage.sqlite")
    job, _ = store.ingest("agent", task.event())
    assert store.work_once()
    assert store.get(job["id"])["preview"]["pipeline"]["confidence_ceiling"] == "VERY LOW"


def test_specialist_reader_cannot_read_other_workflows(tmp_path):
    app = create_app(Settings(tmp_path / "agent.sqlite", ADMIN, INGEST))
    value = {
        "event_id": "push-1", "source": "owner/repo", "event_type": "vcs.push",
        "timestamp": "2026-10-07T12:00:00Z", "data": {
            "domain": "vcs", "repository": "owner/repo", "branch": "main",
            "commit_sha": "a" * 40, "author": "fixture",
        },
    }
    job, _ = app.state.store.ingest("manual", AmbientEvent.model_validate_json(json.dumps(value)))
    with TestClient(app) as client:
        assert client.get(f"/api/v1/agent/tasks/{job['id']}",
                          headers={"Authorization": f"Bearer {INGEST}"}).status_code == 404
        task = SpecialistTask.model_validate_json(json.dumps(payload()))
        assert client.post("/api/v1/events", json=task.event().model_dump(mode="json"),
                           headers={"Authorization": f"Bearer {INGEST}"}).status_code == 422


def test_openapi_and_tool_schema_are_discoverable(tmp_path):
    app = create_app(Settings(tmp_path / "agent.sqlite", ADMIN, INGEST))
    schema = app.openapi()
    assert schema["components"]["schemas"]["SpecialistTask"]["additionalProperties"] is False
    assert "AgentEvidence" in schema["components"]["schemas"]
    body = schema["paths"]["/api/v1/agent/tasks"]["post"]["requestBody"]
    assert body["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/SpecialistTask"
    tool = SpecialistClient.tool_contract()
    assert tool["human_release_required"] and tool["capabilities"] == ["submit", "read-specialist-task"]


def test_specialist_client_requests_and_errors_are_bounded(monkeypatch):
    client = SpecialistClient("http://127.0.0.1:8000", INGEST)
    calls = []

    def opened(request, timeout):
        calls.append(request)
        assert timeout == 15
        return io.BytesIO(json.dumps({
            "id": "a" * 32, "provider": "agent", "state": "PENDING", "result": None,
            "version": 0, "event": {}, "preview": None, "history": [], "artifacts": [],
        }).encode())

    monkeypatch.setattr(client.opener, "open", opened)
    task = SpecialistTask.model_validate_json(json.dumps(payload()))
    job = client.submit(task)
    assert client.get(job["id"])["state"] == "PENDING"
    assert calls[0].full_url == "http://127.0.0.1:8000/api/v1/agent/tasks"
    assert json.loads(calls[0].data)["question"] == task.question
    assert calls[0].get_header("Authorization") == f"Bearer {INGEST}"
    with pytest.raises(ValueError, match="job ID"):
        client.get("../admin")

    def denied(request, timeout):
        raise HTTPError(request.full_url, 401, "Denied", {}, None)

    monkeypatch.setattr(client.opener, "open", denied)
    with pytest.raises(SpecialistClientError, match="401"):
        client.get("a" * 32)
    monkeypatch.setattr(client.opener, "open", lambda *a, **k: io.BytesIO(b"x" * (1024 * 1024 + 1)))
    with pytest.raises(SpecialistClientError, match="1 MiB"):
        client.get("a" * 32)
    monkeypatch.setattr(client.opener, "open", lambda *a, **k: io.BytesIO(b'{"success":true}'))
    with pytest.raises(SpecialistClientError, match="response shape"):
        client.get("a" * 32)


@pytest.mark.parametrize("url", [
    "http://untrusted.example", "https://user:password@example.com",
    "https://example.com/?token=secret", "https://example.com/other", "file:///private",
])
def test_specialist_client_rejects_unsafe_origins(url):
    with pytest.raises(ValueError):
        SpecialistClient(url, INGEST)


def test_specialist_client_rejects_redirects_and_short_token():
    with pytest.raises(ValueError, match="token"):
        SpecialistClient("https://example.com", "short")
    with pytest.raises(SpecialistClientError, match="redirects"):
        NoRedirect().redirect_request(Request("https://example.com"), None, 302, "Found", {}, "https://another.example")


def test_vision_does_not_replace_authored_paper():
    root = Path(__file__).resolve().parents[1]
    assert (root / "VISION_AND_SCOPE.md").is_file()
    assert "VISION_AND_SCOPE.md" in (root / "AGENTS.md").read_text()
    assert "VISION_AND_SCOPE.md" in (root / ".github/copilot-instructions.md").read_text()
    assert (root / "SKILL.md").read_bytes() == (root / "mnt/skills/user/vessel-framework-analyst/SKILL.md").read_bytes()
