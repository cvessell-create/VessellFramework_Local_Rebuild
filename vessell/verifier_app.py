"""Loopback-only browser interface for the deterministic evidence verifier."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from importlib.resources import files
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    ValidationError,
    field_validator,
)
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from vessell.provenance import SourceStatus
from vessell.verify import (
    ClaimCheck,
    JobPosting,
    SourceSighting,
    analyze_planted_news,
    detect_ghost_job,
    group_postings_by_role,
    verify_claim,
)

MAX_BODY_BYTES = 64 * 1024
MAX_ENTRIES = 100


class _InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SightingInput(_InputModel):
    source_name: StrictStr = Field(min_length=1, max_length=200)
    tier: SourceStatus
    url: StrictStr = Field(default="", max_length=2048)
    seen_at: StrictStr = Field(default="", max_length=64)
    published_at: StrictStr = Field(default="", max_length=64)
    text: StrictStr = Field(default="", max_length=10_000)
    root: StrictStr = Field(default="", max_length=200)
    denies: StrictBool = False
    is_official_record: StrictBool = False
    note: StrictStr = Field(default="", max_length=2_000)
    event_clock: StrictStr = Field(default="", max_length=80)

    @field_validator("seen_at", "published_at")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        if value:
            try:
                datetime.fromisoformat(value)
            except ValueError as error:
                raise ValueError("must be an ISO date or timestamp") from error
        return value

    def to_sighting(self) -> SourceSighting:
        return SourceSighting(
            source_name=self.source_name,
            tier=self.tier,
            url=self.url,
            seen_at=self.seen_at,
            published_at=self.published_at,
            text=self.text,
            root=self.root or None,
            denies=self.denies,
            is_official_record=self.is_official_record,
            note=self.note,
            event_clock=self.event_clock or None,
        )


class ClaimInput(_InputModel):
    claim: StrictStr = Field(min_length=1, max_length=2_000)
    sightings: list[SightingInput] = Field(default_factory=list, max_length=MAX_ENTRIES)


class PostingInput(_InputModel):
    title: StrictStr = Field(min_length=1, max_length=300)
    employer: StrictStr = Field(min_length=1, max_length=300)
    location: StrictStr = Field(min_length=1, max_length=300)
    description_text: StrictStr = Field(min_length=1, max_length=10_000)
    salary_text: StrictStr = Field(default="", max_length=500)
    source: StrictStr = Field(min_length=1, max_length=200)
    listing_id: StrictStr = Field(default="", max_length=300)
    claimed_posted: StrictStr = Field(default="", max_length=64)
    first_seen: StrictStr = Field(default="", max_length=64)
    url: StrictStr = Field(default="", max_length=2048)

    @field_validator("claimed_posted", "first_seen")
    @classmethod
    def validate_date(cls, value: str) -> str:
        if value:
            try:
                date.fromisoformat(value[:10])
            except ValueError as error:
                raise ValueError("must be an ISO date") from error
        return value

    def to_posting(self) -> JobPosting:
        return JobPosting(
            title=self.title,
            employer=self.employer,
            location=self.location,
            description_text=self.description_text,
            salary_text=self.salary_text,
            source=self.source,
            listing_id=self.listing_id,
            claimed_posted=self.claimed_posted,
            first_seen=self.first_seen,
            url=self.url,
        )


class JobsInput(_InputModel):
    postings: list[PostingInput] = Field(min_length=1, max_length=MAX_ENTRIES)


async def _read_payload[T: BaseModel](
    request: Request,
    model: type[T],
) -> T | JSONResponse:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        return JSONResponse({"error": "Content-Type must be application/json."}, status_code=415)

    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            return JSONResponse(
                {"error": f"Request body exceeds the {MAX_BODY_BYTES}-byte limit."},
                status_code=413,
            )
        chunks.append(chunk)

    try:
        payload = json.loads(b"".join(chunks))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JSONResponse({"error": "Request body must contain valid JSON."}, status_code=400)
    try:
        return model.model_validate(payload)
    except ValidationError as error:
        details = [
            {"path": list(item["loc"]), "message": item["msg"], "type": item["type"]}
            for item in error.errors(include_input=False)
        ]
        return JSONResponse({"error": "Invalid verifier input.", "details": details}, status_code=422)


def create_app() -> FastAPI:
    app = FastAPI(
        title="VessellFramework Local Verifier",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    page = files("vessell.app").joinpath("claim_verifier.html").read_text(encoding="utf-8")

    @app.middleware("http")
    async def enforce_local_origin(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        host_header = request.headers.get("host", "")
        host = urlsplit(f"//{host_header}").hostname
        if host not in {"127.0.0.1", "localhost"}:
            return JSONResponse({"error": "This verifier only accepts loopback requests."}, status_code=403)
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{host_header}":
            return JSONResponse({"error": "Cross-origin requests are not accepted."}, status_code=403)

        response = await call_next(request)
        response.headers.update({
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
            ),
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        })
        return response

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(page)

    @app.post("/api/v1/verification/claims")
    async def verify_claims(request: Request) -> JSONResponse:
        payload = await _read_payload(request, ClaimInput)
        if isinstance(payload, JSONResponse):
            return payload
        check = ClaimCheck(
            claim=payload.claim,
            sightings=tuple(sighting.to_sighting() for sighting in payload.sightings),
        )
        return JSONResponse({
            "source_access": "NOT_PERFORMED",
            "note": "Only supplied sightings were analyzed; URLs were not fetched or authenticated.",
            "verification": verify_claim(check).to_dict(),
            "planted_news": analyze_planted_news(check).to_dict(),
        })

    @app.post("/api/v1/verification/jobs")
    async def verify_jobs(request: Request) -> JSONResponse:
        payload = await _read_payload(request, JobsInput)
        if isinstance(payload, JSONResponse):
            return payload
        postings = [posting.to_posting() for posting in payload.postings]
        role_reports = [
            detect_ghost_job(role_postings).to_dict()
            for role_postings in group_postings_by_role(postings).values()
        ]
        return JSONResponse({
            "source_access": "NOT_PERFORMED",
            "note": "Only supplied postings were analyzed; URLs were not fetched or authenticated.",
            "postings_received": len(postings),
            "roles": role_reports,
        })

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local VessellFramework verifier UI.")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    import uvicorn

    print(f"Local verifier: http://127.0.0.1:{args.port}/")
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
