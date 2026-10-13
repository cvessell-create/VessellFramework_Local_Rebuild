# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Unit tests for Superintelligence (SI) progression architecture and orchestrator."""

from __future__ import annotations

import pytest

from vessell.provenance import SourceStatus
from vessell.si_agent import (
    AutonomousSIOrchestrator,
    SILevel,
    get_si_progression_matrix,
    main,
)


def test_si_level_enumeration_and_metadata() -> None:
    levels = list(SILevel)
    assert len(levels) == 5
    assert SILevel.LEVEL_1_CHATBOT.value == 1
    assert "Chatbots" in SILevel.LEVEL_1_CHATBOT.label
    assert "Reasoners" in SILevel.LEVEL_2_REASONER.label
    assert "Agents" in SILevel.LEVEL_3_AGENT.label
    assert "Innovators" in SILevel.LEVEL_4_INNOVATOR.label
    assert "Organizations" in SILevel.LEVEL_5_ORGANIZATION.label


def test_si_progression_matrix_structure() -> None:
    matrix = get_si_progression_matrix()
    assert len(matrix) == 5
    for item in matrix:
        assert item.implemented is True
        assert len(item.algorithms) > 0
        assert len(item.supporting_repos) > 0
        assert len(item.ai_models_or_spaces) > 0
        assert len(item.evidence_constraints) > 0


def test_orchestrator_select_models_for_level() -> None:
    orchestrator = AutonomousSIOrchestrator()
    reasoner_models = orchestrator.select_models_for_level(SILevel.LEVEL_2_REASONER)
    assert isinstance(reasoner_models, list)
    assert len(reasoner_models) > 0
    # Must contain models or spaces related to fact-checking, NLI, or verification
    repo_ids = [m.get("id") or m.get("repo_id") for m in reasoner_models]
    assert any("deberta" in rid or "fact-check" in rid or "loren" in rid for rid in repo_ids if rid)


def test_orchestrator_coordinate_tactical_step_allowed() -> None:
    orchestrator = AutonomousSIOrchestrator()
    proposal = {"forward": 1.0, "strafe": 0.0, "turn": 0.1, "fire": True}
    res = orchestrator.coordinate_tactical_step(
        assertion="Counter-agent sighted in north corridor",
        tactical_proposal=proposal,
        is_official=True,
        source_status=SourceStatus.SOURCE_ESTABLISHED,
    )
    assert res.target_level == SILevel.LEVEL_3_AGENT
    assert res.event_chain_verified is True
    assert res.gate_decision["allowed"] is True
    assert res.tactical_action["fire"] is True
    assert len(res.events) > 0


def test_orchestrator_coordinate_tactical_step_blocked_unverified() -> None:
    orchestrator = AutonomousSIOrchestrator()
    proposal = {"forward": 1.0, "strafe": 0.0, "turn": 0.0, "fire": True}
    res = orchestrator.coordinate_tactical_step(
        assertion="Unverified whisper of ambush in south exit",
        tactical_proposal=proposal,
        is_official=False,
        source_status=SourceStatus.WORKING_HYPOTHESIS,
    )
    assert res.target_level == SILevel.LEVEL_3_AGENT
    assert res.event_chain_verified is True
    # Working hypothesis without corroboration cannot pass consequential gate
    assert res.gate_decision["allowed"] is False
    assert res.tactical_action["fire"] is False
    assert res.tactical_action["blocked_by_gate"] is True


def test_si_cli_matrix_and_coordinate(capsys: pytest.CaptureFixture[str]) -> None:
    ret_matrix = main(["matrix"])
    assert ret_matrix == 0
    captured = capsys.readouterr()
    assert "SUPERINTELLIGENCE (SI) CAPABILITY MATRIX" in captured.out

    ret_coord = main(["coordinate", "--claim", "Official map clearance verified", "--forward", "0.5"])
    assert ret_coord == 0
    captured_coord = capsys.readouterr()
    assert "SI Level 3 autonomous coordination complete" in captured_coord.out


def test_orchestrator_run_autonomous_simulation_loop() -> None:
    orchestrator = AutonomousSIOrchestrator()
    res = orchestrator.run_autonomous_simulation_loop(steps=5)
    assert res["event_chain_verified"] is True
    assert res["steps_executed"] == 5
    assert len(res["receipts"]) > 0
    assert len(res["learning_insights"]) > 0

