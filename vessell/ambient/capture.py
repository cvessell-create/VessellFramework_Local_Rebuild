from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import sqlite3
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, ValidationError

from .models import AmbientEvent, Sha256, StrictModel, Text
from .store import Store, canonical, digest

LOG = logging.getLogger(__name__)
IMAGE = "vessell-static-capture:local"
MAX_REQUEST = 64 * 1024


class Viewport(StrictModel):
    width: Annotated[int, Field(ge=240, le=1920)]
    height: Annotated[int, Field(ge=240, le=1080)]


class ElementCheck(StrictModel):
    selector: Annotated[str, Field(min_length=1, max_length=200)]
    count: Annotated[int, Field(ge=0, le=100)]
    text: Annotated[str, Field(max_length=2000)] | None


class Snapshot(StrictModel):
    source: Text
    source_sha256: Sha256
    declared_intent: Text
    viewport: Viewport
    checks: Annotated[list[ElementCheck], Field(max_length=16)]


class Allowlist(StrictModel):
    snapshots: dict[str, Snapshot]


def bounded_read(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        value = stream.read(limit + 1)
    if len(value) > limit:
        raise ValueError(f"{path.name} exceeds its {limit}-byte limit")
    return value


def load_request(allowlist: Path, name: str) -> dict[str, Any]:
    config = Allowlist.model_validate_json(bounded_read(allowlist, MAX_REQUEST))
    if name not in config.snapshots:
        raise ValueError("Snapshot is not in the operator allowlist")
    snapshot = config.snapshots[name]
    base = allowlist.resolve().parent
    source = (base / snapshot.source).resolve()
    if not source.is_relative_to(base) or source.suffix.lower() != ".html":
        raise ValueError("Only HTML files inside the allowlist directory are accepted")
    html = bounded_read(source, 32768)
    if hashlib.sha256(html).hexdigest() != snapshot.source_sha256:
        raise ValueError("Allowlisted source digest mismatch; review changes before updating it")
    request = {
        "snapshot": name, "source_html": html.decode("utf-8"),
        "source_sha256": snapshot.source_sha256, "declared_intent": snapshot.declared_intent,
        "viewport": snapshot.viewport.model_dump(), "checks": [
            item.model_dump() for item in snapshot.checks
        ],
    }
    request["request_sha256"] = digest(canonical(request))
    if len(canonical(request).encode()) > MAX_REQUEST:
        raise ValueError("Combined capture request exceeds 64 KiB")
    return request


def capture(request: dict[str, Any], directory: Path) -> tuple[str, dict[str, bytes]]:
    image_id = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", IMAGE],
        check=True, text=True, capture_output=True, timeout=15,
    ).stdout.strip()
    if not image_id.startswith("sha256:") or len(image_id) != 71:
        raise ValueError("Docker did not return an immutable image ID")
    name = "vf-static-" + uuid.uuid4().hex
    command = [
        "docker", "run", "--rm", "--name", name, "--network", "none",
        "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "128", "--memory", "768m", "--cpus", "1",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m,mode=1777",
        "--shm-size", "64m", "--user", "1000:1000", "-i", image_id,
    ]
    try:
        result = subprocess.run(
            command, input=canonical(request).encode(), capture_output=True, timeout=45, check=False,
        )
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "rm", "-f", name], check=True, timeout=15, capture_output=True)
        raise
    directory.joinpath("container.stderr.log").write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError(f"Capture container exited {result.returncode}; inspect container.stderr.log")
    if len(result.stdout) > 12 * 1024 * 1024:
        raise ValueError("Capture output exceeds 12 MiB")
    output = json.loads(result.stdout)
    artifacts = {
        "screenshot.png": base64.b64decode(output["screenshot"], validate=True),
        "checks.json": canonical(output["report"]).encode(),
        "capture.log": (output["log"] + result.stderr.decode("utf-8", errors="replace")).encode(),
    }
    return image_id, artifacts


def publish(
    store: Store, request: dict[str, Any], image_id: str, artifacts: dict[str, bytes],
    reviewer: str, reason: str,
) -> dict[str, Any]:
    event = AmbientEvent.model_validate_json(canonical({
        "event_id": uuid.uuid4().hex, "source": "local-static-capture",
        "event_type": "static.snapshot", "timestamp": datetime.now(UTC).isoformat(),
        "data": {
            "domain": "snapshot", "declared_intent": request["declared_intent"],
            "source_html": request["source_html"], "source_sha256": request["source_sha256"],
            "request_sha256": request["request_sha256"], "image_id": image_id,
            "screenshot_sha256": hashlib.sha256(artifacts["screenshot.png"]).hexdigest(),
            "checks_sha256": hashlib.sha256(artifacts["checks.json"]).hexdigest(),
            "log_sha256": hashlib.sha256(artifacts["capture.log"]).hexdigest(),
            "execution_reviewer": reviewer, "execution_reason": reason,
        },
    }))
    job, _ = store.ingest("local-capture", event, artifacts=artifacts)
    return job


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or explicitly approve an allowlisted, offline static HTML capture.",
    )
    parser.add_argument("action", choices=["inspect", "run"])
    parser.add_argument("--allowlist", required=True, type=Path)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--approve-request-sha")
    parser.add_argument("--reviewer")
    parser.add_argument("--reason")
    args = parser.parse_args(argv)
    directory: Path | None = None
    try:
        request = load_request(args.allowlist, args.snapshot)
        if args.action == "inspect":
            print(json.dumps(request, indent=2))
            return 0
        if args.approve_request_sha != request["request_sha256"]:
            raise ValueError("Run requires the exact inspected --approve-request-sha")
        if (
            not args.database or not args.database.is_file() or not args.output_dir
            or not args.reviewer or not args.reviewer.strip() or not args.reason or not args.reason.strip()
        ):
            raise ValueError("Run requires an existing database, output directory, reviewer and reason")
        if len(args.reviewer) > 2000 or len(args.reason) > 2000:
            raise ValueError("Reviewer and reason must be at most 2000 characters")
        directory = Path(args.output_dir) / uuid.uuid4().hex
        directory.mkdir(parents=True, exist_ok=False)
        directory.joinpath("request.json").write_text(canonical(request), encoding="utf-8")
        directory.joinpath("source.html").write_text(request["source_html"], encoding="utf-8")
        image_id, artifacts = capture(request, directory)
        for name, content in artifacts.items():
            directory.joinpath(name).write_bytes(content)
        job = publish(Store(args.database), request, image_id, artifacts, args.reviewer, args.reason)
        directory.joinpath("receipt.json").write_text(canonical(job), encoding="utf-8")
        print(json.dumps({"job_id": job["id"], "evidence_directory": str(directory)}))
        return 0
    except (
        ValueError, ValidationError, OSError, RuntimeError, sqlite3.Error, subprocess.SubprocessError,
    ) as error:
        LOG.exception("Static snapshot capture failed")
        if directory is not None:
            directory.joinpath("failure.json").write_text(
                canonical({"error": str(error), "type": type(error).__name__}), encoding="utf-8",
            )
        parser.exit(1, f"Capture failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
