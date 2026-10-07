from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:/@-]+$")]
Text = Annotated[str, Field(min_length=1, max_length=2000)]


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


class AmbientEvent(StrictModel):
    event_id: Identifier
    source: Identifier
    event_type: Literal["vcs.push", "alert.triggered"]
    timestamp: datetime
    data: Annotated[PushData | AlertData, Field(discriminator="domain")]

    @field_validator("timestamp")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must have an explicit timezone")
        return value

    @model_validator(mode="after")
    def matching_type(self) -> AmbientEvent:
        if (self.event_type == "vcs.push") != isinstance(self.data, PushData):
            raise ValueError("event_type and data.domain must agree")
        return self


class ReviewAction(StrictModel):
    action: Literal["approve", "reject"]
    reason: Text
    expected_version: Annotated[int, Field(ge=0)]
