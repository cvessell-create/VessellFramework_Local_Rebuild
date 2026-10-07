import json
import sqlite3
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vessell.ambient.api import Settings, create_app
from vessell.ambient.capture import capture, load_request, main, publish
from vessell.ambient.models import AmbientEvent
from vessell.ambient.store import Store, canonical, digest

FIXTURE = Path(__file__).resolve().parents[1] / "case_studies/ambient/static/allowlist.json"
ADMIN = "capture-admin-test-" * 3
INGEST = "capture-ingest-test-" * 3
IMAGE = "sha256:" + "f" * 64


def request():
    return load_request(FIXTURE, "example")


def artifacts(req, failed=False):
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        + req["viewport"]["width"].to_bytes(4, "big")
        + req["viewport"]["height"].to_bytes(4, "big")
    )
    return {
        "screenshot.png": png,
        "checks.json": canonical({
            "request_sha256": req["request_sha256"], "request": req,
            "viewport": req["viewport"], "checks": [{"passed": not failed}],
            "horizontal_overflow": failed, "model_status": "not_configured",
        }).encode(),
        "capture.log": b"synthetic test renderer, not a real image\n",
    }


def test_allowlist_and_request_digest_are_pinned(tmp_path):
    req = request()
    assert req["source_html"].endswith("\n")
    assert digest(req["source_html"]) == req["source_sha256"]
    assert digest(canonical({k: v for k, v in req.items() if k != "request_sha256"})) == req["request_sha256"]
    with pytest.raises(ValueError, match="allowlist"):
        load_request(FIXTURE, "unlisted")
    config = json.loads(FIXTURE.read_text())
    config["snapshots"]["example"]["source"] = "../outside.html"
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="inside"):
        load_request(path, "example")
    config["snapshots"]["example"]["source"] = "example.html"
    (tmp_path / "example.html").write_text("changed")
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="digest mismatch"):
        load_request(path, "example")


def test_source_symlink_escape_and_byte_limit(tmp_path):
    base = tmp_path / "allowed"
    base.mkdir()
    outside = tmp_path / "outside.html"
    outside.write_text("outside")
    (base / "example.html").symlink_to(outside)
    path = base / "allowlist.json"
    path.write_bytes(FIXTURE.read_bytes())
    with pytest.raises(ValueError, match="inside"):
        load_request(path, "example")
    (base / "example.html").unlink()
    (base / "example.html").write_bytes(b"x" * 32769)
    with pytest.raises(ValueError, match="limit"):
        load_request(path, "example")


def test_changed_checks_invalidate_approval(tmp_path):
    req = request()
    config = json.loads(FIXTURE.read_text())
    config["snapshots"]["example"]["checks"][0]["text"] = "Changed expected output"
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps(config))
    (tmp_path / "example.html").write_bytes(FIXTURE.with_name("example.html").read_bytes())
    assert load_request(path, "example")["request_sha256"] != req["request_sha256"]


def test_cli_requires_approval_before_any_execution(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a))
    assert main(["inspect", "--allowlist", str(FIXTURE), "--snapshot", "example"]) == 0
    assert json.loads(capsys.readouterr().out)["request_sha256"] == request()["request_sha256"]
    with pytest.raises(SystemExit) as error:
        main(["run", "--allowlist", str(FIXTURE), "--snapshot", "example",
              "--approve-request-sha", "wrong"])
    assert error.value.code == 1
    assert not calls


def test_container_limits_immutable_image_and_timeout_cleanup(tmp_path, monkeypatch):
    commands = []

    def run(command, **kwargs):
        commands.append((command, kwargs))
        if command[1:3] == ["image", "inspect"]:
            return subprocess.CompletedProcess(command, 0, stdout=IMAGE + "\n")
        if command[1] == "run":
            raise subprocess.TimeoutExpired(command, 45)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(subprocess.TimeoutExpired):
        capture(request(), tmp_path)
    command = commands[1][0]
    assert command[-1] == IMAGE
    for value in ["--read-only", "--cap-drop", "ALL", "no-new-privileges", "--pids-limit"]:
        assert value in command
    assert command[command.index("--network") + 1] == "none"
    assert "-v" not in command and "--mount" not in command
    assert commands[-1][0][-1] == command[command.index("--name") + 1]


def test_capture_failed_exit_retains_stderr(tmp_path, monkeypatch):
    def run(command, **kwargs):
        if command[1:3] == ["image", "inspect"]:
            return subprocess.CompletedProcess(command, 0, stdout=IMAGE)
        return subprocess.CompletedProcess(command, 2, stdout=b"", stderr=b"renderer failed")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(RuntimeError, match="exited 2"):
        capture(request(), tmp_path)
    assert (tmp_path / "container.stderr.log").read_bytes() == b"renderer failed"


def test_snapshot_is_durable_and_never_automatically_approved(tmp_path, field_assessment):
    from vessell.ambient.models import FieldInquiryAction
    path = tmp_path / "review.sqlite"
    req = request()
    evidence = artifacts(req, failed=True)
    job = publish(Store(path), req, IMAGE, evidence, "operator", "Approve static capture only")
    store = Store(path)
    assert store.work_once()
    job = store.get(job["id"])
    assert job["state"] == "AWAITING_APPROVAL"
    assert job["preview"]["capture_checks"]["checks"][0]["passed"] is False
    assert job["event"]["data"]["source_html"] == req["source_html"]
    assert job["event"]["data"]["model_status"] == "not_configured"
    assert store.artifact(job["id"], "screenshot.png") == evidence["screenshot.png"]
    assert store.changes(0)[-1]["job_id"] == job["id"]
    assert not store.work_once()
    store.complete_field_inquiry(job["id"], FieldInquiryAction(
        expected_version=job["version"], expected_field_version=0, assessment=field_assessment,
    ), "human")
    store.action(job["id"], "approve", "human", "Release measured report, not a correctness claim", job["version"], 1)
    assert store.work_once()
    assert store.get(job["id"])["state"] == "COMPLETED"
    store.prune(1, apply=True)
    with store.connection() as db:
        db.execute("UPDATE ambient_jobs SET updated_at='2000-01-01' WHERE id=?", (job["id"],))
    assert store.prune(1, apply=True) == 1
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM ambient_artifacts").fetchone()[0] == 0


def test_modified_or_deleted_artifacts_fail_readback(tmp_path):
    path = tmp_path / "review.sqlite"
    req = request()
    job = publish(Store(path), req, IMAGE, artifacts(req), "operator", "Approved capture")
    with sqlite3.connect(path) as db:
        db.execute("UPDATE ambient_artifacts SET content=? WHERE name='capture.log'", (b"changed",))
    with pytest.raises(ValueError, match="integrity"):
        Store(path).get(job["id"])


def test_source_request_and_viewport_mismatches_fail_atomically(tmp_path):
    req = request()
    wrong = artifacts(req)
    report = json.loads(wrong["checks.json"])
    report["request"]["source_html"] = "different"
    wrong["checks.json"] = canonical(report).encode()
    store = Store(tmp_path / "review.sqlite")
    with pytest.raises(ValueError, match="approval"):
        publish(store, req, IMAGE, wrong, "operator", "Approved capture")
    assert store.list_jobs() == []
    wrong = artifacts(req)
    wrong["screenshot.png"] = wrong["screenshot.png"][:16] + (1921).to_bytes(4, "big") + (600).to_bytes(4, "big")
    with pytest.raises(ValueError, match="dimensions"):
        publish(store, req, IMAGE, wrong, "operator", "Approved capture")
    assert store.list_jobs() == []


def test_authenticated_artifacts_and_ingress_cannot_trigger_capture(tmp_path):
    app = create_app(Settings(tmp_path / "api.sqlite", ADMIN, INGEST))
    req = request()
    job = publish(app.state.store, req, IMAGE, artifacts(req), "operator", "Approved capture")
    url = f"/api/v1/jobs/{job['id']}/artifacts/screenshot.png"
    with TestClient(app) as client:
        assert client.get(url).status_code == 401
        response = client.get(url, headers={"Authorization": f"Bearer {ADMIN}"})
        assert response.status_code == 200 and response.headers["content-type"] == "image/png"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert client.get(url.replace("screenshot.png", "source.html"),
                          headers={"Authorization": f"Bearer {ADMIN}"}).status_code == 404
        assert client.post("/api/v1/events", json=job["event"],
                           headers={"Authorization": f"Bearer {INGEST}"}).status_code == 422
    event = AmbientEvent.model_validate_json(canonical(job["event"]))
    with pytest.raises(ValueError, match="local capture"):
        app.state.store.ingest("manual", event)
