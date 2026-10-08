import copy
import itertools
import json
import math
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vessell.ambient.api import Settings, create_app
from vessell.app.pipeline import run_case_pipeline
from vessell.app.reporting import render_markdown_report
from vessell.game_theory import assess_game_theory
from vessell.validation import validate_record

ROOT = Path(__file__).parents[1]


def case():
    return json.loads((ROOT / "examples/game-theory-case.json").read_text())


def evaluate(value):
    return assess_game_theory(value, {"hail-log"})


def fraction(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def model(kind, body, players=None):
    value = case()["game_theory"]
    value.update(kind=kind, model=body)
    if players:
        value["players"] = players
    return value


def test_chicken_exact_probabilities_expected_payoffs_and_no_constant_sum():
    result = evaluate(case()["game_theory"])
    mixed = result.calculations["interior_mixed"]
    assert [fraction(x) for x in mixed["first_action_probabilities"]] == [Fraction(9, 10)] * 2
    assert [fraction(x) for x in mixed["expected_utilities"]] == [Fraction(-1, 10)] * 2
    assert result.calculations["pure_nash"] == [["Yield", "Charge"], ["Charge", "Yield"]]
    assert result.calculations["dominance"] == []
    assert not result.calculations["constant_sum"]
    assert not result.grants_authority and not result.validates_motives


def test_sequential_chicken_is_a_different_information_structure():
    root = {"actor": "A", "choices": [
        {"action": "Yield", "next": {"actor": "B", "choices": [
            {"action": "Yield", "next": {"payoff": [0, 0]}},
            {"action": "Charge", "next": {"payoff": [-1, 1]}}]}},
        {"action": "Charge", "next": {"actor": "B", "choices": [
            {"action": "Yield", "next": {"payoff": [1, -1]}},
            {"action": "Charge", "next": {"payoff": [-10, -10]}}]}},
    ]}
    output = evaluate(model("tree", {"root": root})).calculations
    assert output["path"] == ["Charge", "Yield"]
    assert [fraction(x) for x in output["payoff"]] == [1, -1]
    assert output["visited_nodes"] == 7


def test_dominance_constant_sum_and_degenerate_matrix_are_explicit():
    value = model("matrix", {"actions": [["a", "b"], ["c", "d"]],
                            "payoffs": [[[2, -2], [2, -2]], [[1, -1], [1, -1]]]})
    output = evaluate(value).calculations
    assert output["constant_sum"] and output["constant"] == 0
    assert output["interior_mixed"] is None
    assert output["dominance"] == [{"player": "A", "better": "a", "worse": "b", "kind": "strict"}]
    value["model"]["payoffs"][1][1] = [2, -2]
    assert evaluate(value).calculations["dominance"][0]["kind"] == "weak"


@pytest.mark.parametrize("weights,quota,veto", [
    ([27, 27], 31, []), ([10, 0, 1], 10, []),
    ([3, 2, 1], 4, ["C"]), ([1, 1, 1], 3, []),
])
def test_power_indices_match_independent_permutation_enumeration(weights, quota, veto):
    players = list("ABC")[:len(weights)]
    output = evaluate(model("coalition", {
        "weights": weights, "quota": quota, "veto": veto, "cap": 300,
    }, players)).calculations
    counts = [0] * len(weights)
    for order in itertools.permutations(range(len(weights))):
        active = set()
        for i in order:
            active.add(i)
            if sum(weights[j] for j in active) >= quota and all(players.index(v) in active for v in veto):
                counts[i] += 1
                break
    shares = output["players"]
    assert [fraction(x["shapley_shubik"]) for x in shares] == [
        Fraction(x, math.factorial(len(weights))) for x in counts]
    assert sum(fraction(x["banzhaf_normalized"]) for x in shares) == 1
    assert sum(fraction(x["base_reserve"]) for x in shares) == 300


def test_savings_exact_owner_trace_no_interest_or_extra_xp():
    body = {"bank": 0, "available": 0, "earned": 0, "yield_remaining": 0,
            "award": 175, "reserve": 150, "requested": 100}
    first = evaluate(model("savings", body, ["A"])).calculations
    assert first["next"] == {"bank": 43, "available": 132, "earned": 175, "yield_remaining": 43}
    second = evaluate(model("savings", {
        **first["next"], "award": 175, "reserve": 150, "requested": 100,
    }, ["A"])).calculations
    assert second["harvested"] == 11
    assert second["next"] == {"bank": 75, "available": 275, "earned": 350, "yield_remaining": 75}
    assert second["reverse_award"] == 175 and second["reverse_harvest"] == 11
    third = evaluate(model("savings", {
        **second["next"], "award": 0, "reserve": 150.5, "requested": 100,
    }, ["A"])).calculations
    assert third["harvested"] == 0 and third["conserved"]


@pytest.mark.parametrize("mutation", [
    "missing", "unknown-source", "boolean-payoff", "null-payoff", "ragged", "extra-model",
    "oversize", "duplicate-player", "invalid-quota", "tree-depth", "ledger-corruption",
])
def test_invalid_models_fail_explicitly(mutation):
    value = case()["game_theory"]
    if mutation == "missing":
        del value["utility_units"]
    elif mutation == "unknown-source":
        value["evidence_ids"] = ["not-a-source"]
    elif mutation == "boolean-payoff":
        value["model"]["payoffs"][0][0][0] = True
    elif mutation == "null-payoff":
        value["model"]["payoffs"][0][0][0] = None
    elif mutation == "ragged":
        value["model"]["payoffs"][0].pop()
    elif mutation == "extra-model":
        value["model"]["force_approval"] = True
    elif mutation == "oversize":
        value["limitations"] = ["x" * 2000] * 24
    elif mutation == "duplicate-player":
        value["players"] = ["A", "A"]
    elif mutation == "invalid-quota":
        value = model("coalition", {"weights": [1, 1], "quota": 3, "veto": [], "cap": 300})
    elif mutation == "tree-depth":
        root = {"payoff": [0, 0]}
        for _ in range(18):
            root = {"actor": "A", "choices": [{"action": "next", "next": root}]}
        value = model("tree", {"root": root})
    else:
        value = model("savings", {"bank": 1, "available": 1, "earned": 99,
                                 "yield_remaining": 1, "award": 0, "reserve": 0, "requested": 1}, ["A"])
    with pytest.raises(ValueError):
        evaluate(value)


def test_pipeline_reports_legacy_runner_and_agent_load_same_pillar_without_confidence_uplift():
    from vesselframework_agent import read_instructions
    from vesselframework_case_runner import load_reference_module, markdown_report

    value = case()
    validate_record(value, "case.schema.json")
    baseline = run_case_pipeline({k: v for k, v in value.items() if k != "game_theory"},
                                 track_provenance=False)
    result = run_case_pipeline(value, track_provenance=False)
    assert result.confidence_ceiling == baseline.confidence_ceiling
    assert result.counts == baseline.counts
    assert result.pillars[-1] == "GAME THEORY"
    assert result.release_status == baseline.release_status
    assert "## Game Theory: Sixth Pillar" in render_markdown_report(result)
    text, _ = markdown_report(value, load_reference_module())
    assert "COMPUTED_CONDITIONAL" in text
    for name in ("Game_Theory_Theory_SKILL_v0.1.md", "VesselFramework_Game_Theory_SKILL_v0.1.md"):
        assert (ROOT / name).read_text() in read_instructions()
    original = copy.deepcopy(asdict(result.game_theory))
    value["game_theory"]["model"]["payoffs"][0][0][0] = 99
    assert asdict(result.game_theory) == original


def test_specialist_model_is_source_bound_unreviewed_and_replay_identity_preserved(tmp_path):
    admin, token = "game-theory-admin-" * 4, "game-theory-ingest-" * 4
    app = create_app(Settings(tmp_path / "game.sqlite", admin, token))
    value = {"task_id": "strategy", "caller": "parent", "timestamp": "2026-10-07T12:00:00Z",
             "question": "Analyze a supplied game.", "evidence": [
                 {"source_id": "hail-log", "description": "Unverified caller model"}],
             "game_theory": case()["game_theory"]}
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        accepted = client.post("/api/v1/agent/tasks", json=value, headers=headers)
        assert accepted.status_code == 202
        job_id = accepted.json()["id"]
        assert app.state.store.work_once()
        job = app.state.store.get(job_id)
        assert job["preview"]["pipeline"]["game_theory"]["status"] == "COMPUTED_CONDITIONAL"
        assert job["preview"]["pipeline"]["confidence_ceiling"] == "VERY LOW"
        assert job["field_review"]["status"] == "MISSING"
        assert job["result"] is None
        assert client.post("/api/v1/agent/tasks", json=value, headers=headers).status_code == 200
        value["game_theory"]["model"]["payoffs"][0][0][0] = 1
        assert client.post("/api/v1/agent/tasks", json=value, headers=headers).status_code == 409
        value["task_id"] = "invalid-source"
        value["game_theory"]["evidence_ids"] = ["unknown"]
        assert client.post("/api/v1/agent/tasks", json=value, headers=headers).status_code == 422
