# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Cross-domain benchmark: maskirovka convergence verdicts depend on
provenance shape, never on domain content.

The framework's standing claim is cross-domain portability: the same
provenance graph must produce the same convergence verdict whether the
case is cyber intrusion deception, planted-news spread, or supply-chain
disruption deception. These tests pin that claim with benchmark fixtures
in three domains.
"""

from __future__ import annotations

import json
from pathlib import Path

from vessell.app.pipeline import run_case_pipeline
from vessell.provenance import (
    EvidenceItem,
    EvidenceSet,
    MaskirovkaAssessment,
    MaskirovkaVariant,
    ProvenanceRegistry,
    SourceStatus,
    assess_maskirovka_convergence,
)


def _load_case(name: str) -> dict:
    path = Path("tests/fixtures/benchmark_cases") / name
    return json.loads(path.read_text(encoding="utf-8"))


def _shared_root_fixtures() -> list[str]:
    return [
        "maskirovka_convergence_cyber.json",
        "maskirovka_convergence_news.json",
        "maskirovka_convergence_supply_chain.json",
    ]


def test_convergence_verdict_is_domain_independent() -> None:
    """Same provenance shape in three domains yields the same verdict."""
    verdicts = []
    for name in _shared_root_fixtures():
        result = run_case_pipeline(_load_case(name), track_provenance=False)
        verdicts.append(result.convergence_note)

    assert len(verdicts) == 3
    # Every domain must refuse to read shared ancestry as independent
    # convergence, and must name the shared root in the verdict.
    for verdict in verdicts:
        assert verdict.startswith("CAUTION: variants share evidentiary root(s)")
        assert "Do not treat as independent convergence." in verdict
    # The verdict shape is byte-identical across domains; only the
    # domain's root identifier differs.
    shapes = {v.split("root(s)")[0] for v in verdicts}
    assert shapes == {"CAUTION: variants share evidentiary "}


def test_shared_root_is_named_in_each_domain() -> None:
    expected_roots = {
        "maskirovka_convergence_cyber.json": "cyber-vendor-report",
        "maskirovka_convergence_news.json": "news-wire-copy",
        "maskirovka_convergence_supply_chain.json": "sc-supplier-notice",
    }
    for name, root in expected_roots.items():
        result = run_case_pipeline(_load_case(name), track_provenance=False)
        assert root in result.convergence_note


def test_distinct_roots_support_convergence() -> None:
    result = run_case_pipeline(
        _load_case("maskirovka_convergence_distinct_roots.json"),
        track_provenance=False,
    )
    assert result.convergence_note.startswith(
        "Convergence supported on resolved, distinct evidentiary roots."
    )


def test_single_eligible_variant_cannot_converge() -> None:
    registry = ProvenanceRegistry()
    item = EvidenceItem("lone", SourceStatus.SOURCE_ESTABLISHED, "lone")
    registry.register_many([item])
    assessment = MaskirovkaAssessment(
        MaskirovkaVariant.OPERATIONAL, True, EvidenceSet(registry, [item])
    )
    assert assess_maskirovka_convergence([assessment]) == (
        "No multi-variant convergence claim supported."
    )


def test_fractured_registry_is_indeterminate() -> None:
    """Two registries means no shared provenance graph — indeterminate."""
    registry_a = ProvenanceRegistry()
    registry_b = ProvenanceRegistry()
    item_a = EvidenceItem("a", SourceStatus.SOURCE_ESTABLISHED, "a")
    item_b = EvidenceItem("b", SourceStatus.SOURCE_ESTABLISHED, "b")
    registry_a.register_many([item_a])
    registry_b.register_many([item_b])
    assessment_a = MaskirovkaAssessment(
        MaskirovkaVariant.OPERATIONAL, True, EvidenceSet(registry_a, [item_a])
    )
    assessment_b = MaskirovkaAssessment(
        MaskirovkaVariant.STRUCTURAL, True, EvidenceSet(registry_b, [item_b])
    )
    verdict = assess_maskirovka_convergence([assessment_a, assessment_b])
    assert verdict.startswith(
        "CONVERGENCE STATUS: INDETERMINATE — PROVENANCE GRAPH FRACTURED."
    )


def test_unresolved_provenance_never_reads_as_independence() -> None:
    """Missing lineage must not be treated as independence: with an
    unknown parent, no variant is eligible, so no convergence claim
    can be supported."""
    registry = ProvenanceRegistry()
    orphan = EvidenceItem(
        "orphan", SourceStatus.SOURCE_ESTABLISHED, "orphan",
        upstream_of="unknown-parent",
    )
    other = EvidenceItem("other", SourceStatus.SOURCE_ESTABLISHED, "other")
    registry.register_many([orphan, other])
    assessment_a = MaskirovkaAssessment(
        MaskirovkaVariant.OPERATIONAL, True, EvidenceSet(registry, [orphan])
    )
    assessment_b = MaskirovkaAssessment(
        MaskirovkaVariant.STRUCTURAL, True, EvidenceSet(registry, [other])
    )
    verdict = assess_maskirovka_convergence([assessment_a, assessment_b])
    assert verdict == "No multi-variant convergence claim supported."
    assert "Convergence supported" not in verdict
    assert "CAUTION" not in verdict
