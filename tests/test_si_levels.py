# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
import json

from vessell import si_chat, si_levels
from tests.test_si_chat import SIBackend


def _t(ok):
    return {"check": "c", "passed": ok, "detail": ""}


def test_gate_is_bottom_up():
    rows = si_levels.gate([[_t(True)] * 3, [_t(False)] * 3, [_t(True)] * 3, [_t(True)] * 3, [_t(True)] * 3])
    assert [r["state"] for r in rows] == ["up", "down", "down", "down", "down"]
    assert rows[0]["posterior_mean"] == 0.8 and rows[1]["posterior_mean"] == 0.2


def test_gate_requires_trials():
    assert si_levels.gate([[]] + [[_t(True)]] * 4)[0]["state"] == "down"


def test_measured_formula_route_mismatch_has_two_judgments(tmp_path, monkeypatch):
    mem = si_chat.LoopMemory(tmp_path / "memory.jsonl")
    mem.append("chat", {"message": "Vessell formula Phase 0 to Phase 1", "speaker": "player"})
    si = si_chat.SIChat(backend=SIBackend(), memory=mem, myth=[])
    monkeypatch.setattr(si_chat, "formula_snapshot", lambda: {
        "state": "UP", "phase1": "LOCAL_RECEIPT_VERIFIED", "problems": []})
    trials = si_levels.level1(si)
    assert trials[0]["passed"] is False
    assert si.backend.seen == [], "formula telemetry deliberately bypasses generation"
    assert trials[0]["measurement"]["result"] == "CONTRACT_MISMATCH_MEASURED"
    rows = si_levels.gate([trials] + [[_t(True)] * 3] * 4)
    first = rows[0]["judgments"]
    assert first["gate"]["outcome"] == "DOWN"
    assert first["gate"]["boundary"] == "promotion withheld as coded"
    assert first["measurement"]["conclusion"] == "CONTRACT_MISMATCH_MEASURED"
    assert "telemetry correctness" in first["measurement"]["next_evaluation"]
    assert rows[1]["judgments"]["gate"]["local_requirement"] == "MET"
    assert rows[1]["judgments"]["gate"]["blocked_by"] == "L1 Chatbot"
    assert rows[1]["judgments"]["measurement"]["conclusion"] == "UPSTREAM_GATE_HOLD"


def test_bad_answers_and_unclassified_telemetry_are_not_measured_mismatches(tmp_path):
    class Reply:
        memory = si_chat.LoopMemory(tmp_path / "memory.jsonl")

        def reply(self, *args, **kwargs):
            return self.result

    si = Reply()
    for result in [
        {"kind": "telemetry", "text": "state", "error": None},
        {"kind": "telemetry", "text": "", "route": "formula_telemetry", "error": None},
        {"kind": "telemetry", "text": "state", "route": "formula_telemetry", "error": "OSError"},
        {"kind": "owner", "text": "fallback", "error": None},
    ]:
        si.result = result
        trials = si_levels.level1(si)
        assert all(t["measurement"]["result"] == "REQUIREMENT_NOT_MET" for t in trials)
        assert si_levels.gate([trials])[0]["judgments"]["measurement"]["conclusion"] == "LOCAL_CHECKS_NOT_MET"


def test_mismatch_does_not_hide_another_failed_check():
    mismatch = {**_t(False), "measurement": {"result": "CONTRACT_MISMATCH_MEASURED"}}
    row = si_levels.gate([[mismatch, _t(False)]])[0]
    assert row["state"] == "down"
    assert row["judgments"]["measurement"]["conclusion"] == "MISMATCH_AND_UNMET_CHECKS"


def test_run_scripted_end_to_end(tmp_path):
    mem = si_chat.LoopMemory(tmp_path / "m.jsonl")
    mem.append("episode", {"generation": 1, "mission": 0, "outcome": "dead", "kills": 2, "fitness": 10, "seconds": 9})
    mem.append("chat", {"message": "where is the exit?", "text": "x", "reply_kind": "generated"})
    web = si_chat.WebSearch(fetch=lambda q: {"AbstractText": "Cyberpunk is science fiction.", "Heading": "C",
                                             "AbstractURL": "https://en.wikipedia.org/wiki/Cyberpunk"})
    lines = ["Hold steady, Analyst.", "Watch the corridor.", "Restock first.", "Cyberpunk is science fiction.",
             "Move up slow.", "Check your six."]
    si = si_chat.SIChat(backend=SIBackend(text=lines), memory=mem, myth=[], web=web)

    def si_model(model, messages, max_tokens):
        sys = messages[0]["content"]
        if "LESSON" in sys:
            return "LESSON: Name one concrete next move."
        if "pitching game ideas" in sys:
            return "Add sniper drones."
        if "Rook" in sys:
            return "Why trust you?"
        return "IDEA: Sniper drones\nEVIDENCE: E1\nDISCONFIRMER: none\nSLICE: one drone"

    report = si_levels.run(si=si, generate=si_model, model="test", report_path=tmp_path / "r.jsonl")
    states = {r["level"]: r["state"] for r in report["levels"]}
    fails = [(r["level"], t) for r in report["levels"] for t in r["checks"] if not t["passed"]]
    assert all(s == "up" for s in states.values()), fails
    assert report["status"] == "RECORDED TRIAL RESULTS / PENDING_HUMAN_REVIEW"
    assert json.loads((tmp_path / "r.jsonl").read_text())["levels"][4]["level"] == "L5 Organization"
    # Probe traffic is not treated as playtester questions.
    from vessell import chat_duel
    assert chat_duel.player_questions(mem) == ["where is the exit?"]
