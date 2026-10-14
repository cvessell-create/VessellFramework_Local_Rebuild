"""Strict current-run conjunction; case compliance does not establish evidence truth."""
from __future__ import annotations

from typing import Any

SCHEMA = "vessell-formula/v1"


def evaluate(required: list[str], observations: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
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
