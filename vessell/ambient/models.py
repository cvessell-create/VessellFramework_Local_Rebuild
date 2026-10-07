from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from vessell.field_inquiry import assess_field_inquiry

Identifier = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:/@-]+$")]
Text = Annotated[str, Field(min_length=1, max_length=2000)]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class PushData(StrictModel):
    domain: Literal["vcs"]
    repository: Identifier
    branch: Identifier
    commit_sha: Annotated[str, Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")]
    author: Text


class AlertData(StrictModel):
    domain: Literal["monitoring"]
    alert_id: Identifier
    service_name: Identifier
    severity: Literal["info", "warning", "critical"]
    summary: Text


class SnapshotData(StrictModel):
    domain: Literal["snapshot"]
    declared_intent: Text
    source_html: Annotated[str, StringConstraints(
        strip_whitespace=False, min_length=1, max_length=32768,
    )]
    source_sha256: Sha256
    request_sha256: Sha256
    image_id: Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
    screenshot_sha256: Sha256
    checks_sha256: Sha256
    log_sha256: Sha256
    execution_reviewer: Text
    execution_reason: Text
    model_status: Literal["not_configured"] = "not_configured"


class AgentEvidence(StrictModel):
    source_id: Identifier
    description: Text
    upstream_of: Identifier | None = None


class SpecialistData(StrictModel):
    domain: Literal["specialist"]
    question: Text
    evidence: Annotated[list[AgentEvidence], Field(min_length=1, max_length=24)]
    field_inquiry: dict[str, object] | None = None

    @model_validator(mode="after")
    def unique_sources(self) -> SpecialistData:
        ids = [item.source_id for item in self.evidence]
        if len(set(ids)) != len(ids):
            raise ValueError("Specialist evidence source IDs must be unique")
        if self.field_inquiry is not None:
            assess_field_inquiry(self.field_inquiry, set(ids))
        return self


class AmbientEvent(StrictModel):
    event_id: Identifier
    source: Identifier
    event_type: Literal["vcs.push", "alert.triggered", "static.snapshot", "agent.analysis.requested"]
    timestamp: datetime
    data: Annotated[PushData | AlertData | SnapshotData | SpecialistData, Field(discriminator="domain")]

    @field_validator("timestamp")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must have an explicit timezone")
        return value

    @model_validator(mode="after")
    def matching_type(self) -> AmbientEvent:
        expected = {
            "vcs.push": "vcs", "alert.triggered": "monitoring", "static.snapshot": "snapshot",
            "agent.analysis.requested": "specialist",
        }
        if self.data.domain != expected[self.event_type]:
            raise ValueError("event_type and data.domain must agree")
        return self


class ReviewAction(StrictModel):
    action: Literal["approve", "reject"]
    reason: Text
    expected_version: Annotated[int, Field(ge=0)]
    expected_field_version: Annotated[int, Field(ge=1)] | None = None


class FieldInquiryAction(StrictModel):
    expected_version: Annotated[int, Field(ge=0)]
    expected_field_version: Annotated[int, Field(ge=0)]
    assessment: dict[str, object]


Folder = Literal[
    "inbox", "action", "strategic", "market", "policy", "industry", "network",
    "education", "courses", "certifications", "watchlist", "administrative", "archive",
]
CategoryColor = Literal["red", "orange", "yellow", "green", "blue", "purple"]


class FilingState(StrictModel):
    folder: Folder = "inbox"
    is_read: bool = False
    flagged: bool = False
    category_color: CategoryColor | None = None
    version: Annotated[int, Field(ge=0)]
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Filing timestamp must have an explicit timezone")
        return value


class FilingAction(StrictModel):
    expected_version: Annotated[int, Field(ge=0)]
    folder: Folder = "inbox"
    is_read: bool = False
    flagged: bool = False
    category_color: CategoryColor | None = None

    @model_validator(mode="after")
    def meaningful_patch(self) -> FilingAction:
        if not self.model_fields_set.intersection(
            {"folder", "is_read", "flagged", "category_color"},
        ):
            raise ValueError("Provide at least one filing field")
        return self
