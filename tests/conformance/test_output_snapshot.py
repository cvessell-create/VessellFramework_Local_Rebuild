# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Compare unreleased CLI previews after normalizing random claim IDs.

The fixture intentionally omits Harm Gate answers and human inquiry.
Writing a reproducible preview must not turn those omissions into clearance.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from vessell import provenance
from vessell.app.main import main
from vessell.harm_gate import REQUIRED_FIELDS

_FIXTURE = "tests/fixtures/benchmark_cases/mixed_status_case.json"


@pytest.fixture(autouse=True)
def _clean_lifecycle() -> Iterator[None]:
    provenance.reset_claim_lifecycle()
    yield
    provenance.reset_claim_lifecycle()


def _run_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> tuple[int, str]:
    monkeypatch.setattr(
        sys,
        "argv",
        ["vf-program", "--input", _FIXTURE, "--output-dir", str(tmp_path)],
    )
    rc = main()
    return rc, capsys.readouterr().out


def _read_reports(tmp_path: Path) -> tuple[str, str]:
    markdown_files = sorted(tmp_path.glob("*.md"))
    json_files = sorted(tmp_path.glob("*.json"))
    assert len(markdown_files) == 1, f"expected one markdown report, got {markdown_files}"
    assert len(json_files) == 1, f"expected one machine report, got {json_files}"
    payload = json.loads(json_files[0].read_text(encoding="utf-8"))
    payload["claim_ids"] = [f"claim-{index}" for index in range(len(payload["claim_ids"]))]
    return markdown_files[0].read_text(encoding="utf-8"), json.dumps(payload, indent=2)


def test_end_to_end_previews_reproduce_after_claim_id_normalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    rc1, stdout1 = _run_main(tmp_path / "run1", monkeypatch, capsys)
    assert rc1 == 1, stdout1
    rc2, stdout2 = _run_main(tmp_path / "run2", monkeypatch, capsys)
    assert rc2 == 1, stdout2
    assert "RUNNER STATUS: REVIEW REQUIRED (Harm Gate)" in stdout1
    assert "RUNNER STATUS: REVIEW REQUIRED (Harm Gate)" in stdout2

    markdown1, json1 = _read_reports(tmp_path / "run1")
    markdown2, json2 = _read_reports(tmp_path / "run2")

    assert markdown1 == markdown2
    assert json1 == json2


def test_end_to_end_reports_carry_doctrine_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Snapshot landmarks: the reports carry the pipeline's doctrine result."""
    rc, stdout = _run_main(tmp_path, monkeypatch, capsys)
    assert rc == 1, stdout
    assert "RUN COMPLETE" in stdout
    assert "RUNNER STATUS: REVIEW REQUIRED (Harm Gate)" in stdout

    markdown, machine = _read_reports(tmp_path)

    # Human-readable landmarks
    assert "# Mixed status benchmark" in markdown
    assert "Confidence ceiling: LOW" in markdown
    assert "- source_established: 1" in markdown
    assert "- framework_synthesis: 1" in markdown
    assert "- working_hypothesis: 1" in markdown
    assert "- illustrative: 1" in markdown
    assert "Maintain explicit status distinctions in downstream claims." in markdown
    assert "- Report status: PREVIEW_REQUIRES_HUMAN_FIELD_COMPLETION" in markdown
    assert "- Human completion and a separate release decision are required." in markdown

    # Machine-readable landmarks
    payload = json.loads(machine)
    assert payload["title"] == "Mixed status benchmark"
    assert payload["confidence_ceiling"] == "LOW"
    assert payload["counts"]["total_evidence"] == 4
    assert payload["counts"]["independent_roots"] == 4
    assert payload["convergence_note"] == "No multi-variant convergence claim supported."
    assert len(payload["claim_ids"]) == 4
    assert payload["harm_gate"]["cleared"] is False
    assert payload["harm_gate"]["exposure"] == "UNKNOWN"
    assert payload["harm_gate"]["missing_fields"] == list(REQUIRED_FIELDS)
    assert payload["release_status"] == "PREVIEW_REQUIRES_HUMAN_FIELD_COMPLETION"
    assert payload["game_theory"]["status"] == "NOT_SUPPLIED"


def test_end_to_end_outputs_register_dependents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Written reports register themselves against the claims they consumed,
    so a later correction propagates to the exact report files."""
    rc, stdout = _run_main(tmp_path, monkeypatch, capsys)
    assert rc == 1, stdout

    # Claim IDs are random per run: read the raw (unnormalized) machine
    # report for the lookup, not the normalized snapshot text.
    raw_machine = json.loads(min(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    claim_ids = raw_machine["claim_ids"]
    assert claim_ids, "pipeline should intake evidence as claims"

    reporting_artifacts = set()
    pipeline_registrations = 0
    for claim_id in claim_ids:
        for dependent in provenance.propagate_correction(claim_id):
            if dependent.artifact == "vessell.app.reporting.case-report":
                reporting_artifacts.add(dependent.location)
            if dependent.artifact == "vessell.app.pipeline.PipelineResult":
                pipeline_registrations += 1

    # Two report files (markdown + json) registered per claim...
    assert len(reporting_artifacts) == 2
    assert all(str(tmp_path) in location for location in reporting_artifacts)
    # ...and the pipeline result registered itself once per claim.
    assert pipeline_registrations == len(claim_ids)
