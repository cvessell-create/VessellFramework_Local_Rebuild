"""ASCII case-policy correction and a separate strict current-run conjunction."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict, TypeIs

SCHEMA = "vessell-formula/v1"


class CasePolicyResult(TypedDict):
    text: str
    initial_product: int
    product: int
    state: str
    mismatches_before: int
    correction_passes: int


def _ascii_text(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("Case-policy text must be a string.")
    if not value.isascii():
        raise ValueError("Case-policy text must be ASCII.")
    return value


def case_state(character: str) -> int | None:
    """Return uppercase=1, lowercase=0 or neutral=None for one ASCII character."""
    character = _ascii_text(character)
    if len(character) != 1:
        raise ValueError("Expected one ASCII character.")
    if "A" <= character <= "Z":
        return 1
    if "a" <= character <= "z":
        return 0
    return None


def _is_mapping(value: object) -> TypeIs[Mapping[object, object]]:
    return isinstance(value, Mapping)


def _validate_case_policy(text: str, mask: object) -> None:
    _ascii_text(text)
    if not _is_mapping(mask):
        raise TypeError("Case-policy mask must map one-based positions to 0 or 1.")
    for position, required in mask.items():
        if type(position) is not int or not 1 <= position <= len(text):
            raise ValueError("Masked positions must be one-based integers within the string.")
        if type(required) is not int or required not in (0, 1):
            raise ValueError("Required case must be the integer 0 or 1.")
        if case_state(text[position - 1]) is None:
            raise ValueError("A case-policy mask may target only ASCII letters.")


def case_gate(text: str, mask: Mapping[int, int]) -> int:
    """Check current compliance, including PASS for a valid empty mask."""
    _validate_case_policy(text, mask)
    return int(all(case_state(text[position - 1]) == required
                   for position, required in mask.items()))


def transform_case(text: str, mask: Mapping[int, int]) -> str:
    """Apply a fixed valid case policy, preserving every unmasked character."""
    _validate_case_policy(text, mask)
    characters = list(text)
    for position, required in mask.items():
        character = characters[position - 1]
        characters[position - 1] = character.upper() if required else character.lower()
    return "".join(characters)


def correct_case(text: str, mask: Mapping[int, int]) -> CasePolicyResult:
    """Check, correct at most once, verify, then stop; never retry in a loop."""
    before = case_gate(text, mask)
    mismatches = sum(case_state(text[position - 1]) != required
                     for position, required in mask.items())
    output = text if before else transform_case(text, mask)
    product = case_gate(output, mask)
    if product != 1:
        raise RuntimeError("Case-policy correction failed verification.")
    return {"text": output, "initial_product": before, "product": product,
            "state": "PASS", "mismatches_before": mismatches,
            "correction_passes": 1 - before}


def evaluate(required: list[str], observations: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    """Require nonempty evidence checks; never transform observations into passes."""
    problems: list[str] = []
    if not run_id:
        problems.append("missing run id")
    if not required or len(set(required)) != len(required):
        problems.append("required ids must be nonempty and unique")
    ids = [row.get("id") for row in observations]
    if len(ids) != len(set(ids)):
        problems.append("duplicate observation id")
    if set(ids) != set(required):
        problems.append("observation ids do not match required ids")
    for row in observations:
        if row.get("run_id") != run_id:
            problems.append(f"{row.get('id')}: wrong run")
        if row.get("passed") is not True:
            problems.append(f"{row.get('id')}: not confirmed UP")
    up = not problems
    return {"schema": SCHEMA, "run_id": run_id, "required": required,
            "checks": observations, "problems": problems,
            "product": int(up), "state": "UP" if up else "DOWN",
            "scope": "current-run check compliance, not evidence truth or authorization"}
