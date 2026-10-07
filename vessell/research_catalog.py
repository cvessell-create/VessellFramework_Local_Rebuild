# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Validate and render a human-authored organizational-psychology literature catalog."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from vessell.validation import validate_record


def validate_catalog(catalog: Any) -> None:
    """Validate the catalog contract and enforce unique record identifiers."""
    validate_record(catalog, "research-evidence-catalog.schema.json")
    identifiers = [record["id"] for record in catalog["records"]]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Catalog record IDs must be unique.")


def _items(values: list[str]) -> str:
    return ", ".join(values) if values else "Not specified"


def render_catalog(catalog: dict[str, Any]) -> str:
    """Render deterministic review notes without scoring or synthesizing evidence."""
    validate_catalog(catalog)
    lines = [
        "# Organizational Psychology Literature Catalog",
        "",
        "> This report renders human-entered catalog records. It does not verify",
        "> citations or extracted claims, assess study quality, synthesize effects,",
        "> or recommend workplace policy. Appraisal fields record reviewer notes,",
        "> not a validated quality score. No employee or participant data belong",
        "> in this catalog.",
        "",
        "## Research question",
        "",
        catalog["research_question"],
        "",
        f"Cataloged records: {len(catalog['records'])}",
        "",
    ]
    if not catalog["records"]:
        lines.extend(["No sources are cataloged yet.", ""])
        return "\n".join(lines)

    for record in catalog["records"]:
        locator = record["source_locator"]
        lines.extend(
            [
                f"## {record['id']} — {record['citation']}",
                "",
                f"- Source type: {record['source_type']}",
                f"- Locator ({locator['kind']}): {locator['value']}",
                f"- Screening: {record['screening_decision']}",
                f"- Source check (reviewer-entered): {record['source_check_status']}",
                f"- Extraction basis: {record['extraction_basis']}",
                f"- Population and setting: {record['population_and_setting']}",
                f"- Design: {record['design']}",
                f"- Constructs: {_items(record['constructs'])}",
                f"- Measures: {_items(record['measures'])}",
                f"- Outcomes: {_items(record['outcomes'])}",
                f"- Reviewer-entered findings summary: {record['findings_summary']}",
                f"- Limitations: {_items(record['limitations'])}",
                f"- Applicability: {record['applicability_note']}",
                f"- Appraisal status: {record['appraisal_status']}",
            ]
        )
        if "screening_reason" in record:
            lines.append(f"- Screening reason: {record['screening_reason']}")
        if "source_check_note" in record:
            lines.append(f"- Source-check note: {record['source_check_note']}")
        if "supporting_location" in record:
            lines.append(f"- Supporting location: {record['supporting_location']}")
        if "appraisal_method" in record:
            lines.append(f"- Appraisal method: {record['appraisal_method']}")
            lines.append(f"- Appraisal notes: {record['appraisal_notes']}")
        lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vessell-research-catalog",
        description="Validate and render a human-authored organizational-psychology literature catalog.",
    )
    parser.add_argument("catalog", type=Path, help="Path to catalog JSON")
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the Markdown report to this path instead of standard output",
    )
    args = parser.parse_args(argv)
    try:
        with args.catalog.open("r", encoding="utf-8") as file:
            catalog = json.load(file)
        validate_catalog(catalog)
        report = render_catalog(catalog)
        if args.output:
            args.output.write_text(report, encoding="utf-8")
        else:
            sys.stdout.write(report)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"CATALOG FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
