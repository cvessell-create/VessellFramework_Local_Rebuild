"""Bounded public-safe analysis previews and repository reference discovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    Field,
    StrictBool,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from vessell.ambient.models import Sha256, StrictModel, Text
from vessell.ambient.specialist import SpecialistTask
from vessell.ambient.store import analyze
from vessell.provenance import SourceStatus
from vessell.verifier_app import PostingInput, SightingInput
from vessell.verify import (
    ClaimCheck,
    analyze_planted_news,
    detect_ghost_job,
    group_postings_by_role,
    verify_claim,
)

REPOSITORY = "cvessell-create/VessellFramework_Local_Rebuild"
PAGES = "https://cvessell-create.github.io/VessellFramework_Local_Rebuild/"
MAX_REQUEST_BYTES = 32 * 1024
REFERENCE_PATHS = (
    "VISION_AND_SCOPE.md",
    "PROFESSOR_README.md",
    "docs/specialist-agent.md",
    "docs/github-agent-integration.md",
    "docs/claim-verifier.md",
    "docs/personal-family-agent-spec.md",
    "docs/personal-family-protection-guide.md",
    "docs/state-law-protections.md",
    "docs/platform-accountability-laws.md",
    "docs/pillar-scientific-foundations.md",
    "VesselFramework_Knowing_Field_SKILL_v0.1.md",
    "VesselFramework_Game_Theory_SKILL_v0.1.md",
)
RESOURCE_ROOT = Path(__file__).parent / "_resources" / "agent"
INDEX_PATH = (
    RESOURCE_ROOT / "agent-reference-index.json"
    if RESOURCE_ROOT.is_dir()
    else Path(__file__).parents[1] / "docs" / "agent-reference-index.json"
)


class RequestBase(StrictModel):
    contract_version: Literal["1.0"]
    request_id: Annotated[str, Field(min_length=36, max_length=36)]
    data_classification: Literal["public-non-sensitive"]

    @field_validator("request_id")
    @classmethod
    def canonical_uuid(cls, value: str) -> str:
        if str(UUID(value)) != value:
            raise ValueError("request_id must be a canonical lowercase UUID")
        return value


class EvidenceRequest(RequestBase):
    operation: Literal["evidence-analysis"]
    payload: SpecialistTask

    @model_validator(mode="after")
    def valid_event(self) -> EvidenceRequest:
        self.payload.event()
        return self


class HostedSighting(SightingInput):
    tier: SourceStatus = Field(
        default=SourceStatus.WORKING_HYPOTHESIS,
        json_schema_extra={"const": "WORKING HYPOTHESIS"},
    )
    is_official_record: StrictBool = Field(default=False, json_schema_extra={"const": False})

    @model_validator(mode="after")
    def no_asserted_authority(self) -> HostedSighting:
        if self.tier != SourceStatus.WORKING_HYPOTHESIS or self.is_official_record:
            raise ValueError(
                "Hosted sightings must be WORKING HYPOTHESIS and not asserted official records"
            )
        return self


class ClaimPayload(StrictModel):
    claim: Text
    sightings: Annotated[list[HostedSighting], Field(min_length=1, max_length=24)]


class ClaimRequest(RequestBase):
    operation: Literal["claim-analysis", "spread-analysis"]
    payload: ClaimPayload


class JobPayload(StrictModel):
    postings: list[PostingInput] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def one_role(self) -> JobPayload:
        if len(group_postings_by_role([row.to_posting() for row in self.postings])) != 1:
            raise ValueError("Compare one employer/title/location per request")
        return self


class JobRequest(RequestBase):
    operation: Literal["job-analysis"]
    payload: JobPayload


class SearchPayload(StrictModel):
    query: Annotated[str, Field(min_length=1, max_length=200)]
    limit: Annotated[int, Field(ge=1, le=10)] = 5

    @field_validator("query")
    @classmethod
    def searchable(cls, value: str) -> str:
        if not search_terms(value):
            raise ValueError("query must contain letters or digits")
        return value


class SearchRequest(RequestBase):
    operation: Literal["reference-search"]
    payload: SearchPayload


HostedRequest = Annotated[
    EvidenceRequest | ClaimRequest | JobRequest | SearchRequest,
    Field(discriminator="operation"),
]
REQUEST_ADAPTER: TypeAdapter[HostedRequest] = TypeAdapter(HostedRequest)


class ExecutionIdentity(StrictModel):
    repository: Literal["cvessell-create/VessellFramework_Local_Rebuild"]
    ref: Literal["refs/heads/master"]
    actor: Literal["cvessell-create"]
    source_revision: Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")]
    run_id: Annotated[str, Field(pattern=r"^[1-9][0-9]*$")]
    run_attempt: Annotated[str, Field(pattern=r"^[1-9][0-9]*$")]


class PreviewResult(StrictModel):
    contract_version: Literal["1.0"] = "1.0"
    request_id: Annotated[str, Field(
        pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
    )]
    operation: Literal[
        "evidence-analysis", "claim-analysis", "spread-analysis", "job-analysis", "reference-search",
    ]
    state: Literal["UNRELEASED_PREVIEW"] = "UNRELEASED_PREVIEW"
    analysis_only: Literal[True] = True
    report_released: Literal[False] = False
    execution_authorized: Literal[False] = False
    human_field_completion_required: Literal[True] = True
    human_release_required: Literal[True] = True
    input_standing: Literal["WORKING HYPOTHESIS"] = "WORKING HYPOTHESIS"
    external_claim_state: Literal[
        "FRAMEWORK STATE: DEGRADED — UNVERIFIED EXTERNAL CLAIM"
    ] = "FRAMEWORK STATE: DEGRADED — UNVERIFIED EXTERNAL CLAIM"
    request_sha256: Sha256
    preview_sha256: Sha256
    execution: ExecutionIdentity | None
    preview: dict[str, Any]
    limits: list[str]


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON keys are not supported")
        value[key] = item
    return value


def invalid_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant {value} is not supported")


def search_terms(query: str) -> list[str]:
    return re.findall(r"[^\W_]+", query.lower())


def build_index(root: Path) -> dict[str, Any]:
    documents: list[dict[str, Any]] = []
    for relative in REFERENCE_PATHS:
        data = (root / relative).read_bytes()
        if len(data) > 1024 * 1024:
            raise ValueError("Reference exceeds 1 MiB")
        text = data.decode("utf-8")
        documents.append({
            "path": relative, "sha256": digest(data), "text": text,
            "title": next((line.lstrip("# ").strip() for line in text.splitlines()
                           if line.startswith("# ")), relative),
        })
    return {
        "contract_version": "1.0",
        "scope": "Fixed public repository reference snapshots; not live web or all repository files",
        "documents": documents,
    }


def search_references(payload: SearchPayload) -> dict[str, Any]:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    documents = index["documents"]
    if [row["path"] for row in documents] != list(REFERENCE_PATHS):
        raise ValueError("Reference index does not match the fixed corpus")
    terms = search_terms(payload.query)
    hits: list[dict[str, Any]] = []
    for row in documents:
        if digest(row["text"].encode("utf-8")) != row["sha256"]:
            raise ValueError("Reference index digest mismatch")
        for number, line in enumerate(row["text"].splitlines(), start=1):
            if all(term in search_terms(line) for term in terms):
                hits.append({
                    "path": row["path"], "title": row["title"], "line": number,
                    "snippet": line[:1000], "source_sha256": row["sha256"],
                    "url": f"https://github.com/{REPOSITORY}/blob/master/{row['path']}#L{number}",
                    "standing": "REPOSITORY REFERENCE ONLY",
                })
    return {
        "query": payload.query, "scope": list(REFERENCE_PATHS),
        "document_count": len(documents), "total_matches": len(hits),
        "result_count": min(len(hits), payload.limit), "limit_hit": len(hits) > payload.limit,
        "status": "MATCHES IN SCOPE" if hits else "NOT FOUND IN SCOPE",
        "index_sha256": digest(INDEX_PATH.read_bytes()),
        "results": hits[:payload.limit],
        "what_was_not_checked": [
            "Live sources, other files, legal applicability, freshness and independent corroboration",
            "A master link may change; the index digest binds the searched snapshot",
        ],
    }


def run_request(raw: bytes, execution: ExecutionIdentity | None = None) -> PreviewResult:
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("Request exceeds 32768 bytes")
    json.loads(raw, object_pairs_hook=unique_keys, parse_constant=invalid_constant)
    request = REQUEST_ADAPTER.validate_json(raw)
    if isinstance(request, EvidenceRequest):
        preview = analyze(request.payload.event().model_dump(mode="json"))
    elif isinstance(request, ClaimRequest):
        check = ClaimCheck(
            claim=request.payload.claim,
            sightings=tuple(row.to_sighting() for row in request.payload.sightings),
        )
        preview = (
            verify_claim(check).to_dict() if request.operation == "claim-analysis"
            else analyze_planted_news(check).to_dict()
        )
    elif isinstance(request, JobRequest):
        preview = detect_ghost_job([row.to_posting() for row in request.payload.postings]).to_dict()
    else:
        preview = search_references(request.payload)
    return PreviewResult(
        request_id=request.request_id, operation=request.operation,
        request_sha256=digest(canonical(request.model_dump(mode="json"))),
        preview_sha256=digest(canonical(preview)), execution=execution, preview=preview,
        limits=[
            "Public-non-sensitive is caller-declared; no sensitive-data detector or family isolation",
            "Caller identity and source contents are not authenticated by the analysis",
            "No URL retrieval, model calls, private account access, filings or external actions",
            "Heuristic classifications and source digests do not establish external truth",
            "No durable replay deduplication or report-release path; retries are separate runs",
        ],
    )


def discovery(root: Path) -> dict[str, Any]:
    return {
        "name": "VessellFramework public evidence previews",
        "contract_version": "1.0",
        "repository": f"https://github.com/{REPOSITORY}",
        "documentation": PAGES + "agents.html",
        "deployment_status": "NOT_VERIFIED",
        "transport": "authenticated GitHub workflow_dispatch; asynchronous artifacts",
        "workflow": ".github/workflows/agent-analysis.yml",
        "allowed_ref": "master",
        "allowed_actor": "cvessell-create",
        "workflow_input": "request_json",
        "artifact_name": "agent-preview-RUN_ID-RUN_ATTEMPT",
        "result_file": "preview.json",
        "reference_index": PAGES + "agent-reference-index.json",
        "reference_index_sha256": digest(canonical(build_index(root))),
        "operations": [
            "evidence-analysis", "claim-analysis", "spread-analysis",
            "job-analysis", "reference-search",
        ],
        "request_max_bytes": MAX_REQUEST_BYTES,
        "input_schema": REQUEST_ADAPTER.json_schema(),
        "result_schema": PreviewResult.model_json_schema(),
        "human_release_required": True,
        "anonymous_api": False,
        "private_family_intake": False,
        "protocol": "Repository-defined contract, not an MCP or A2A endpoint",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--request", type=Path, help="Public-non-sensitive JSON request")
    source.add_argument("--github", action="store_true", help="Read VF_REQUEST_JSON and GitHub identity")
    source.add_argument("--build-discovery", type=Path, help="Repository root for generated Pages files")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.build_discovery:
            if args.output:
                raise ValueError("--output cannot be combined with --build-discovery")
            root = args.build_discovery.resolve()
            (root / "docs/agent-reference-index.json").write_bytes(canonical(build_index(root)))
            (root / "docs/agent-capabilities.json").write_bytes(canonical(discovery(root)))
            return 0
        execution = None
        if args.github:
            execution = ExecutionIdentity.model_validate({
                "repository": os.environ.get("GITHUB_REPOSITORY"),
                "ref": os.environ.get("GITHUB_REF"),
                "actor": os.environ.get("GITHUB_ACTOR"),
                "source_revision": os.environ.get("GITHUB_SHA"),
                "run_id": os.environ.get("GITHUB_RUN_ID"),
                "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            })
            if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
                raise ValueError("Only workflow_dispatch is supported")
            raw = os.environ.get("VF_REQUEST_JSON", "").encode("utf-8")
        else:
            if args.output and args.output.resolve() == args.request.resolve():
                raise ValueError("Output must not overwrite the request")
            with args.request.open("rb") as file:
                raw = file.read(MAX_REQUEST_BYTES + 1)
        result = run_request(raw, execution)
        output = result.model_dump_json(indent=2) + "\n"
        if len(output.encode("utf-8")) > 1024 * 1024:
            raise ValueError("Preview exceeds 1 MiB")
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    except ValidationError as error:
        categories = sorted({
            row["type"] for row in error.errors(include_input=False, include_context=False)
        })
        print("AGENT INPUT REJECTED (see input schema): " + ", ".join(categories), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        print(f"AGENT FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
