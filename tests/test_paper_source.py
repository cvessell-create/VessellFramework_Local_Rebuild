"""Keep author-source text and reconstructed evaluation provenance aligned."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHOR_SOURCE_SHA256 = "42b20766faa8192fb720f938980dc824b84f138ec34c60965d2aef3792305b75"


def test_canonical_paper_matches_author_designated_source():
    record = json.loads((ROOT / "docs/paper-source-reconciliation.json").read_text())
    paper = ROOT / record["canonical_path"]
    assert hashlib.sha256(paper.read_bytes()).hexdigest() == AUTHOR_SOURCE_SHA256
    assert record["source_document_sha256"] == AUTHOR_SOURCE_SHA256
    assert record["source_preservation"] == "BYTE_IDENTICAL"
    assert paper.read_text().splitlines()[0] == f'# {record["source_title"]}'


def test_comparison_spec_pins_corrected_author_source():
    record = json.loads((ROOT / "docs/paper-source-reconciliation.json").read_text())
    path = ROOT / "case_studies/claim_correction/spec.json"
    spec = json.loads(path.read_text())
    assert spec["source_document_sha256"] == AUTHOR_SOURCE_SHA256
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["corrected_evaluation_spec_sha256"]
    assert record["previous_evaluation_source_document_sha256"] != AUTHOR_SOURCE_SHA256
    assert record["historical_external_records_verified"] is False


def test_source_and_reconciliation_are_in_distribution_manifest():
    manifest = json.loads((ROOT / "VessellFramework_v3.8.1_SHA256_Manifest.json").read_text())
    entries = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
    for path in (
        "docs/claim-correction-case-study.md",
        "docs/paper-source-reconciliation.md",
        "docs/paper-source-reconciliation.json",
        "case_studies/claim_correction/spec.json",
    ):
        assert entries[path] == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
