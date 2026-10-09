"""Summarize sourced, observable prompt-audit cases without inferring private reasoning."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def summarize_prompt_audit(database: Path) -> dict[str, Any]:
    """Return aggregate outcomes and explicit evidence limits from the audit catalog."""
    if not database.is_file():
        raise FileNotFoundError(f"Prompt audit catalog not found: {database}")
    uri = f"file:{database.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        required = {"metadata", "prompt_audit_cases"}
        if not required.issubset(tables):
            raise ValueError("Database does not contain prompt-audit catalog tables.")
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        case_count = connection.execute("SELECT COUNT(*) FROM prompt_audit_cases").fetchone()[0]
        outcomes = dict(
            connection.execute(
                """
                SELECT outcome_status, COUNT(*)
                FROM prompt_audit_cases
                GROUP BY outcome_status
                ORDER BY outcome_status
                """
            )
        )
        dialect_guidance = dict(
            connection.execute(
                """
                SELECT dialect_id, COUNT(*)
                FROM prompt_guidance
                GROUP BY dialect_id
                ORDER BY dialect_id
                """
            )
        )
        source_rows = connection.execute(
            """
            SELECT source_id, title, url, source_type, finding_and_limit
            FROM llm_research_sources
            ORDER BY source_id
            """
        ).fetchall()
        guidance_sources = connection.execute(
            """
            SELECT source_kind, COUNT(*)
            FROM repository_guidance_sources
            GROUP BY source_kind ORDER BY source_kind
            """
        ).fetchall()
    return {
        "audit_cases": case_count,
        "outcomes": outcomes,
        "prompt_templates_by_dialect": dialect_guidance,
        "research_sources": [
            {
                "source_id": row[0],
                "title": row[1],
                "url": row[2],
                "type": row[3],
                "finding_and_limit": row[4],
            }
            for row in source_rows
        ],
        "repository_guidance_sources": {
            "total": sum(row[1] for row in guidance_sources),
            "by_kind": dict(guidance_sources),
            "interpretation_limit": (
                "Counts and hashes inventory repository guidance; it does not establish "
                "whether or how any prompt influenced an assistant or code change."
            ),
        },
        "source_archive_sha256": metadata.get("llm_audit_source_sha256", "NOT_SUPPLIED"),
        "hidden_chain_of_thought": "NOT_ACCESSIBLE; not inferred from user prompts or visible outputs",
        "scope_limit": (
            "Only imported, selected analyst summaries are counted. This is not a full account "
            "export, model-internal trace, representative frequency sample, or causal evaluation."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report visible prompt-audit outcomes; never infer hidden chain-of-thought."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/sql_reference.sqlite"),
        help="SQL reference catalog, optionally built with --prompt-audit-zip",
    )
    parser.add_argument("--json", action="store_true", help="Emit the result as JSON.")
    args = parser.parse_args(argv)
    try:
        result = summarize_prompt_audit(args.database)
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"PROMPT AUDIT FAILED: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Selected audit summaries: {result['audit_cases']}")
    print("Visible outcome classes:")
    for status, count in result["outcomes"].items():
        print(f"  {status}: {count}")
    print("Private chain-of-thought: NOT_ACCESSIBLE; no mental-state inference made.")
    guidance = result["repository_guidance_sources"]
    print(
        "Repository prompt/skill guidance inventory: "
        f"{guidance['total']} documents (metadata and marker counts only)."
    )
    print(result["scope_limit"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
