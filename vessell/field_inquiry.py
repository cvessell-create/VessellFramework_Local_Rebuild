"""Record validation for human-led Knowing Field inquiry, never simulated presencing."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any

from vessell.validation import validate_record

PILLARS = ("PARADOX", "BOTTLENECK", "DUAL LAYER", "XFACTOR", "KNOWING FIELD")
FIELD_POLICY = "knowing-field-v1"
FIELD_LIMIT = 32 * 1024


class InvalidFieldInquiry(ValueError):
    pass


@dataclass(frozen=True)
class FieldInquiryResult:
    status: str
    assessment: dict[str, Any] | None
    limitations: tuple[str, ...]
    human_completion_required: bool = True
    validates_experience: bool = False
    grants_authority: bool = False
    policy: str = FIELD_POLICY


def assess_field_inquiry(raw: Any, evidence_ids: set[str]) -> FieldInquiryResult:
    if raw is None:
        return FieldInquiryResult(
            "MISSING", None,
            ("No field inquiry supplied; a source-bound human assessment is required before release.",),
        )
    try:
        validate_record(raw, "field-inquiry.schema.json")
    except ValueError as error:
        raise InvalidFieldInquiry(str(error)) from error
    text = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(text.encode()) > FIELD_LIMIT:
        raise InvalidFieldInquiry("Field inquiry exceeds 32 KiB")
    assessment: dict[str, Any] = copy.deepcopy(raw)
    parties = [party["id"] for party in assessment["affected_parties"]]
    if len(parties) != len(set(parties)):
        raise InvalidFieldInquiry("Field inquiry affected-party IDs must be unique")
    unknown = set(assessment["evidence_ids"]) - evidence_ids
    if unknown:
        raise InvalidFieldInquiry("Field inquiry references unknown evidence IDs: " + ", ".join(sorted(unknown)))
    return FieldInquiryResult(
        "DOCUMENTED_UNREVIEWED", assessment, tuple(assessment["limitations"]),
    )


def field_template(evidence_ids: list[str]) -> dict[str, Any]:
    """Blank scaffold; the human must supply accounts or explicit collection gaps."""
    return {
        "boundary": "", "observer_position": "",
        "affected_parties": [{"id": "", "role": "", "participation": "not_contacted"}],
        "first_person": "", "second_person": "", "third_person": "", "fourth_person": "",
        "evidence_ids": evidence_ids, "dissent": "", "blind_spots": [""],
        "attention": "", "intention": "", "agency": "", "alternatives": [""],
        "test_plan": "", "limitations": [""],
    }
