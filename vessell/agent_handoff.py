"""Validate and print the owner-provided, observable GitHub agent handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_HANDOFF = Path("data/prompt_session_handoff.json")


def load_handoff(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"GitHub agent handoff not found: {path}")
    with path.open(encoding="utf-8") as stream:
        handoff = json.load(stream)
    if not isinstance(handoff, dict):
        raise TypeError("GitHub agent handoff must contain a JSON object.")
    if handoff.get("schema_version") != "1":
        raise ValueError("Unsupported GitHub agent handoff schema version.")
    required = {
        "source_and_completeness",
        "owner_goal",
        "historical_request_summaries",
        "assistant_visible_rationale_summary",
        "observable_work_and_verification",
        "reasoning_access_boundary",
        "github_agent_task",
    }
    missing = required - handoff.keys()
    if missing:
        raise ValueError(f"GitHub agent handoff is missing fields: {', '.join(sorted(missing))}")
    boundary = handoff["reasoning_access_boundary"]
    if (
        not isinstance(boundary, dict)
        or boundary.get("private_model_chain_of_thought") != "NOT_AVAILABLE"
    ):
        raise ValueError("Private model chain-of-thought must be explicitly marked NOT_AVAILABLE.")
    source = handoff["source_and_completeness"]
    if not isinstance(source, dict) or source.get("is_complete_transcript") is not False:
        raise ValueError("Handoff completeness must explicitly reflect the supplied summary scope.")
    if (
        not isinstance(handoff["github_agent_task"], str)
        or not handoff["github_agent_task"].strip()
    ):
        raise ValueError("GitHub agent task must be a non-empty string.")
    return handoff


def render_agent_handoff(handoff: dict[str, Any]) -> str:
    goal = handoff["owner_goal"]["summary"]
    rationale = handoff["assistant_visible_rationale_summary"]
    allowed = handoff["reasoning_access_boundary"]["available_from_this_handoff"]
    lines = [
        f"# {handoff['handoff_id']}",
        "",
        f"**Owner goal:** {goal}",
        "",
        (
            "**Evidence boundary:** private model chain-of-thought is NOT_AVAILABLE. "
            "Use only supplied user statements, visible rationale summaries, recorded actions, "
            "and verifiable outcomes. Historical items are summaries, not verbatim transcript."
        ),
        "",
        "## Assistant-visible rationale summaries",
    ]
    lines.extend(f"- {item['claim']} (basis: {item['basis']})" for item in rationale)
    lines.extend(["", "## Available evidence"])
    lines.extend(f"- {item}" for item in allowed)
    lines.extend(["", "## Task for the GitHub agent", handoff["github_agent_task"]])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and render the supplied observable GitHub agent handoff."
    )
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--json", action="store_true", help="Print the validated handoff as JSON.")
    args = parser.parse_args()
    try:
        handoff = load_handoff(args.handoff)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(f"GITHUB AGENT HANDOFF FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(handoff, indent=2) if args.json else render_agent_handoff(handoff))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
