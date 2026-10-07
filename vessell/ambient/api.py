from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from .models import AmbientEvent, ReviewAction
from .store import Conflict, MissingJob, Store

LOG = logging.getLogger(__name__)
MAX_BODY = 64 * 1024


@dataclass(frozen=True)
class Settings:
    database: Path
    admin_token: str
    ingest_token: str
    github_secret: str = ""
    gitlab_secret: str = ""
    reviewer_identity: str = "local-reviewer"

    def __post_init__(self) -> None:
        if len(self.admin_token) < 32 or len(self.ingest_token) < 32:
            raise ValueError("Distinct admin/ingest tokens must each contain at least 32 characters")
        if self.admin_token == self.ingest_token:
            raise ValueError("Admin and ingest tokens must differ")
        if not self.reviewer_identity.strip() or len(self.reviewer_identity) > 200:
            raise ValueError("Reviewer identity must contain 1-200 nonblank characters")
        for secret in (self.github_secret, self.gitlab_secret):
            if secret and len(secret) < 32:
                raise ValueError("Configured webhook secrets must contain at least 32 characters")

    @classmethod
    def environment(cls) -> Settings:
        return cls(
            Path(os.environ.get("VESSELL_AMBIENT_DB", "outputs/ambient.sqlite")),
            os.environ.get("VESSELL_AMBIENT_ADMIN_TOKEN", ""),
            os.environ.get("VESSELL_AMBIENT_INGEST_TOKEN", ""),
            os.environ.get("VESSELL_GITHUB_WEBHOOK_SECRET", ""),
            os.environ.get("VESSELL_GITLAB_WEBHOOK_SECRET", ""),
            os.environ.get("VESSELL_AMBIENT_REVIEWER", "local-reviewer"),
        )


async def body(request: Request) -> bytes:
    chunks = bytearray()
    async for chunk in request.stream():
        if len(chunks) + len(chunk) > MAX_BODY:
            raise HTTPException(413, "Event body exceeds 64 KiB")
        chunks.extend(chunk)
    return bytes(chunks)


def parse(raw: bytes) -> AmbientEvent:
    try:
        return AmbientEvent.model_validate_json(raw)
    except ValidationError as error:
        raise HTTPException(422, "Invalid event envelope; see /openapi.json") from error


def normalize(provider: str, delivery: str, payload: dict[str, Any]) -> AmbientEvent:
    try:
        if provider == "github":
            repository = payload["repository"]["full_name"]
            author = payload["pusher"]["name"]
            timestamp = payload["head_commit"]["timestamp"]
            sha = payload["after"]
        else:
            repository = payload["project"]["path_with_namespace"]
            author = payload["user_username"]
            timestamp = payload["commits"][-1]["timestamp"]
            sha = payload["after"]
        if payload.get("deleted") or sha == "0" * len(sha):
            raise ValueError("Deletion pushes are not supported")
        return parse(json.dumps({
            "event_id": delivery, "source": repository, "event_type": "vcs.push",
            "timestamp": timestamp, "data": {
                "domain": "vcs", "repository": repository, "branch": payload["ref"],
                "commit_sha": sha, "author": author,
            },
        }).encode())
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise HTTPException(422, "Malformed or unsupported push payload") from error


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.environment()
    store = Store(config.database)
    stop = threading.Event()
    worker_errors: list[str] = []

    def worker() -> None:
        while not stop.is_set():
            try:
                worked = store.work_once()
            except (ValueError, KeyError, OSError, sqlite3.Error) as error:
                LOG.exception("Ambient worker stopped; persisted jobs retained for diagnosis")
                worker_errors.append(type(error).__name__)
                return
            if not worked:
                stop.wait(0.25)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        stop.clear()
        worker_errors.clear()
        thread = threading.Thread(target=worker, name="ambient-analysis-worker")
        thread.start()
        app.state.worker = thread
        try:
            yield
        finally:
            stop.set()
            await asyncio.to_thread(thread.join, 15)
            if thread.is_alive():
                raise RuntimeError("Ambient worker did not shut down within 15 seconds")

    app = FastAPI(title="Vessell ambient analysis review", lifespan=lifespan)
    app.state.store = store

    def token(expected: str, authorization: str | None) -> None:
        supplied = authorization or ""
        if not hmac.compare_digest(supplied.encode(), f"Bearer {expected}".encode()):
            raise HTTPException(401, "Valid bearer token required")

    def admin(authorization: Annotated[str | None, Header()] = None) -> str:
        token(config.admin_token, authorization)
        return config.reviewer_identity

    def ingest_auth(authorization: Annotated[str | None, Header()] = None) -> None:
        token(config.ingest_token, authorization)

    @app.exception_handler(Conflict)
    async def conflict_handler(request: Request, error: Conflict) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.exception_handler(MissingJob)
    async def missing_handler(request: Request, error: MissingJob) -> JSONResponse:
        return JSONResponse({"detail": "Workflow not found"}, status_code=404)

    @app.get("/health")
    def health() -> dict[str, str]:
        thread = getattr(app.state, "worker", None)
        if worker_errors or thread is None or not thread.is_alive():
            raise HTTPException(503, "Analysis worker unavailable; inspect server logs")
        return {"status": "healthy", "scope": "analysis-only"}

    @app.post("/api/v1/events", dependencies=[Depends(ingest_auth)])
    async def ingest(request: Request) -> JSONResponse:
        event = parse(await body(request))
        job, created = await asyncio.to_thread(store.ingest, "manual", event)
        return JSONResponse(job, status_code=202 if created else 200)

    @app.post("/api/v1/ingress/{provider}")
    async def webhook(provider: str, request: Request) -> JSONResponse:
        if provider not in ("github", "gitlab"):
            raise HTTPException(404, "Unsupported provider")
        secret = config.github_secret if provider == "github" else config.gitlab_secret
        if not secret:
            raise HTTPException(503, "Provider webhook is disabled until a secret is configured")
        raw = await body(request)
        if provider == "github":
            signature = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
            supplied = request.headers.get("x-hub-signature-256", "")
            event_type = request.headers.get("x-github-event")
            delivery = request.headers.get("x-github-delivery", "")
        else:
            signature = secret
            supplied = request.headers.get("x-gitlab-token", "")
            event_type = request.headers.get("x-gitlab-event")
            delivery = request.headers.get("x-gitlab-event-uuid", "")
        if not hmac.compare_digest(signature.encode(), supplied.encode()):
            raise HTTPException(401, "Webhook authentication failed")
        if event_type != ("push" if provider == "github" else "Push Hook"):
            raise HTTPException(422, "Only push events are supported")
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise HTTPException(422, "Invalid JSON") from error
        if not isinstance(payload, dict):
            raise HTTPException(422, "Push payload must be an object")
        event = normalize(provider, delivery, payload)
        job, created = await asyncio.to_thread(store.ingest, provider, event)
        return JSONResponse(job, status_code=202 if created else 200)

    @app.get("/api/v1/jobs", dependencies=[Depends(admin)])
    def jobs(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        before: Annotated[str | None, Query(max_length=32)] = None,
    ) -> list[dict[str, Any]]:
        return store.list_jobs(limit, before)

    @app.get("/api/v1/jobs/{job_id}", dependencies=[Depends(admin)])
    def job(job_id: str) -> dict[str, Any]:
        return store.get(job_id)

    @app.post("/api/v1/jobs/{job_id}/action")
    def action(job_id: str, review: ReviewAction, actor: str = Depends(admin)) -> dict[str, Any]:
        return store.action(job_id, review.action, actor, review.reason, review.expected_version)

    @app.get("/api/v1/stream", dependencies=[Depends(admin)])
    async def stream(
        request: Request,
        after: Annotated[int, Query(ge=0)] = 0,
        last_event_id: Annotated[str | None, Header()] = None,
    ) -> StreamingResponse:
        if last_event_id is not None:
            try:
                cursor = int(last_event_id)
                if cursor < 0:
                    raise ValueError
                after = max(after, cursor)
            except ValueError as error:
                raise HTTPException(422, "Invalid Last-Event-ID") from error

        async def events() -> AsyncIterator[str]:
            cursor = after
            while not await request.is_disconnected():
                changes = await asyncio.to_thread(store.changes, cursor)
                if changes:
                    for change in changes:
                        cursor = change["seq"]
                        yield f"id: {cursor}\ndata: {json.dumps(change)}\n\n"
                else:
                    yield ": heartbeat\n\n"
                    await asyncio.sleep(1)
        return StreamingResponse(
            events(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app
