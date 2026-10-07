from __future__ import annotations

import json
import re
from typing import Annotated, Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import AwareDatetime, Field

from .models import AgentEvidence, AmbientEvent, Identifier, SpecialistData, StrictModel, Text
from .store import TRANSITIONS


class SpecialistTask(StrictModel):
    task_id: Identifier
    caller: Identifier
    timestamp: AwareDatetime
    question: Text
    evidence: Annotated[list[AgentEvidence], Field(min_length=1, max_length=24)]
    field_inquiry: dict[str, object] | None = None

    def event(self) -> AmbientEvent:
        data = SpecialistData(
            domain="specialist", question=self.question, evidence=self.evidence,
            field_inquiry=self.field_inquiry,
        )
        return AmbientEvent(
            event_id=self.task_id, source=self.caller, timestamp=self.timestamp,
            event_type="agent.analysis.requested", data=data,
        )


class SpecialistClientError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str,
    ) -> None:
        raise SpecialistClientError("Specialist API redirects are not allowed; check the configured origin")


class SpecialistClient:
    """Submission/read capability only; never holds the human-review credential."""

    def __init__(self, base_url: str, ingest_token: str) -> None:
        parsed = urlparse(base_url)
        if (
            parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/") or not parsed.hostname
            or (parsed.scheme != "https" and not (
                parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")
            ))
        ):
            raise ValueError("Specialist origin requires HTTPS or loopback HTTP without credentials/path/query")
        if len(ingest_token) < 32 or not ingest_token.isascii() or any(
            ord(character) < 33 or ord(character) > 126 for character in ingest_token
        ):
            raise ValueError("A private printable ASCII ingest token of at least 32 characters is required")
        self.base_url = base_url.rstrip("/")
        self.token = ingest_token
        self.opener = build_opener(NoRedirect())

    def _request(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        request = Request(
            self.base_url + "/api/v1/agent/tasks" + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=15) as response:
                raw = response.read(1024 * 1024 + 1)
        except HTTPError as error:
            raise SpecialistClientError(f"Specialist API rejected the request (HTTP {error.code})") from error
        if len(raw) > 1024 * 1024:
            raise SpecialistClientError("Specialist response exceeds 1 MiB")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise SpecialistClientError("Specialist API returned invalid JSON") from error
        if (
            not isinstance(value, dict)
            or not {"id", "provider", "state", "version", "event", "preview", "result", "history", "artifacts"}.issubset(value)
            or not isinstance(value["id"], str) or not re.fullmatch(r"[a-f0-9]{32}", value["id"])
            or value["provider"] != "agent" or not isinstance(value["state"], str)
            or value["state"] not in TRANSITIONS
            or (value["result"] is not None and not isinstance(value["result"], dict))
            or type(value["version"]) is not int or value["version"] < 0
            or not isinstance(value["event"], dict) or not isinstance(value["history"], list)
            or not isinstance(value["artifacts"], list)
            or (value["state"] == "COMPLETED") != isinstance(value["result"], dict)
        ):
            raise SpecialistClientError("Specialist API returned an invalid response shape")
        return value

    def submit(self, task: SpecialistTask) -> dict[str, Any]:
        return self._request("", task.model_dump(mode="json"))

    @staticmethod
    def tool_contract() -> dict[str, Any]:
        return {
            "name": "vessell_evidence_specialist",
            "description": "Submit bounded evidence for durable human-reviewed analysis; never authorizes execution.",
            "input_schema": SpecialistTask.model_json_schema(),
            "capabilities": ["submit", "read-specialist-task"],
            "human_release_required": True,
            "human_field_completion_required": True,
        }

    def get(self, job_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise ValueError("Invalid specialist job ID")
        return self._request("/" + job_id)
