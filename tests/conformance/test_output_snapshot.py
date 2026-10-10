# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""End-to-end output snapshot: the full-program CLI writers must emit
deterministic machine/human outputs for case review.

Doctrine claim under test: every verdict reproduces byte-identically from
its evidence. The only volatile fields are the run timestamp in the file
stem and the random claim IDs; everything else must be stable across runs.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from vessell import provenance
from vessell.app.main import main

_FIXTURE = "tests/fixtures/benchmark_cases/mixed_status_case.json"


@pytest.fixture(autouse=True)
def _clean_lifecycle():
    provenance.reset_claim_lifecycle()
    yield
    provenance.reset_claim_lifecycle()


def _run_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> tuple[int, str]:
    monkeypatch.setattr(
        sys,
        "argv",
        ["vf-program", "--input", _FIXTURE, "--output-dir", str(tmp_path)],
    )
    rc = main()
    return rc, capsys.readouterr().out


def _normalize(text: str) -> str:
    text = re.sub(r"claim-[0-9a-f]{12}", "claim-NORMALIZED", text)
    text = re.sub(r"\d{8}T\d{6}Z", "TIMESTAMP", text)
    return text


def _read_reports(tmp_path: Path) -> tuple[str, str]:
    markdown_files = sorted(tmp_path.glob("*.md"))
    json_files = sorted(tmp_path.glob("*.json"))
    assert len(markdown_files) == 1, f"expected one markdown report, got {markdown_files}"
    assert len(json_files) == 1, f"expected one machine report, got {json_files}"
    return (
        _normalize(markdown_files[0].read_text(encoding="utf-8")),
        _normalize(json_files[0].read_text(encoding="utf-8")),
    )


def test_end_to_end_outputs_reproduce_byte_identically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Two runs of the same case produce byte-identical reports."""
    rc1, _ = _run_main(tmp_path / "run1", monkeypatch, capsys)
    assert rc1 == 0
    rc2, _ = _run_main(tmp_path / "run2", monkeypatch, capsys)
    assert rc2 == 0

    markdown1, json1 = _read_reports(tmp_path / "run1")
    markdown2, json2 = _read_reports(tmp_path / "run2")

    assert markdown1 == markdown2
    assert json1 == json2


def test_end_to_end_reports_carry_doctrine_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Snapshot landmarks: the reports carry the pipeline's doctrine result."""
    rc, stdout = _run_main(tmp_path, monkeypatch, capsys)
    assert rc == 0
    assert "RUN COMPLETE" in stdout

    markdown, machine = _read_reports(tmp_path)

    # Human-readable landmarks
    assert "# Mixed status benchmark" in markdown
    assert "Confidence ceiling: LOW" in markdown
    assert "- source_established: 1" in markdown
    assert "- framework_synthesis: 1" in markdown
    assert "- working_hypothesis: 1" in markdown
    assert "- illustrative: 1" in markdown
    assert "Maintain explicit status distinctions in downstream claims." in markdown

    # Machine-readable landmarks
    payload = json.loads(machine)
    assert payload["title"] == "Mixed status benchmark"
    assert payload["confidence_ceiling"] == "LOW"
    assert payload["counts"]["total_evidence"] == 4
    assert payload["counts"]["independent_roots"] == 4
    assert payload["convergence_note"] == "No multi-variant convergence claim supported."
    assert len(payload["claim_ids"]) == 4


def test_end_to_end_outputs_register_dependents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Written reports register themselves against the claims they consumed,
    so a later correction propagates to the exact report files."""
    rc, _ = _run_main(tmp_path, monkeypatch, capsys)
    assert rc == 0

    # Claim IDs are random per run: read the raw (unnormalized) machine
    # report for the lookup, not the normalized snapshot text.
    raw_machine = json.loads(min(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    claim_ids = raw_machine["claim_ids"]
    assert claim_ids, "pipeline should intake evidence as claims"

    reporting_artifacts = set()
    pipeline_registrations = 0
    for claim_id in claim_ids:
        for dependent in provenance._DEPENDENTS.get(claim_id, []):
            if dependent.artifact == "vessell.app.reporting.case-report":
                reporting_artifacts.add(dependent.location)
            if dependent.artifact == "vessell.app.pipeline.PipelineResult":
                pipeline_registrations += 1

    # Two report files (markdown + json) registered per claim...
    assert len(reporting_artifacts) == 2
    assert all(str(tmp_path) in location for location in reporting_artifacts)
    # ...and the pipeline result registered itself once per claim.
    assert pipeline_registrations == len(claim_ids)
