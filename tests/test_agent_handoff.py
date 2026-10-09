from __future__ import annotations

import json
from pathlib import Path

import pytest

from vessell.agent_handoff import load_handoff, render_agent_handoff

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "data" / "prompt_session_handoff.json"


def test_owner_handoff_is_valid_and_explicitly_bounds_reasoning_access() -> None:
    handoff = load_handoff(HANDOFF)
    rendered = render_agent_handoff(handoff)

    assert handoff["source_and_completeness"]["is_complete_transcript"] is False
    assert all(not item["verbatim"] for item in handoff["current_message_summaries"])
    assert all(not item["verbatim"] for item in handoff["assistant_visible_rationale_summary"])
    assert handoff["reasoning_access_boundary"]["private_model_chain_of_thought"] == "NOT_AVAILABLE"
    assert "private model chain-of-thought is NOT_AVAILABLE" in rendered
    assert "Historical items are summaries, not verbatim transcript." in rendered
    assert "No GitHub agent was launched from this session." in str(
        handoff["observable_work_and_verification"]["actions_not_performed"]
    )


def test_handoff_rejects_missing_or_misrepresented_private_reasoning(tmp_path: Path) -> None:
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    handoff["reasoning_access_boundary"]["private_model_chain_of_thought"] = "captured"
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps(handoff), encoding="utf-8")

    with pytest.raises(ValueError, match="NOT_AVAILABLE"):
        load_handoff(invalid)


def test_handoff_rejects_claim_of_complete_transcript(tmp_path: Path) -> None:
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    handoff["source_and_completeness"]["is_complete_transcript"] = True
    invalid = tmp_path / "incomplete.json"
    invalid.write_text(json.dumps(handoff), encoding="utf-8")

    with pytest.raises(ValueError, match="completeness"):
        load_handoff(invalid)
