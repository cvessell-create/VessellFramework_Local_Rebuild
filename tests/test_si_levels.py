# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
import json

from tests.test_si_chat import SIBackend
from vessell import si_chat, si_levels


def _t(ok):
    return {"check": "c", "passed": ok, "detail": ""}


def test_gate_is_bottom_up():
    rows = si_levels.gate([[_t(True)] * 3, [_t(False)] * 3, [_t(True)] * 3, [_t(True)] * 3, [_t(True)] * 3])
    assert [r["state"] for r in rows] == ["up", "down", "down", "down", "down"]
    assert rows[0]["posterior_mean"] == 0.8 and rows[1]["posterior_mean"] == 0.2


def test_gate_requires_trials():
    assert si_levels.gate([[]] + [[_t(True)]] * 4)[0]["state"] == "down"


def test_generation_quality_requires_a_predeclared_fixture_oracle():
    expected = ("hold position", "wait for extraction")
    correct = {
        "kind": "generated", "route": "generated", "text": "Hold position and wait for extraction.",
        "error": None,
    }
    assert si_levels.generation_fixture_matches(correct, expected)
    assert not si_levels.generation_fixture_matches(
        {**correct, "text": "A fluent but wrong answer."}, expected)
    assert not si_levels.generation_fixture_matches({**correct, "error": "OSError"}, expected)
    assert not si_levels.generated_response_contract({**correct, "route": "generated_error"})
    assert not si_levels.generation_fixture_matches({**correct, "kind": "owner", "route": "owner"}, expected)
    assert not si_levels.generation_fixture_matches(correct, ())


def test_formula_telemetry_correctness_uses_expected_snapshot():
    snapshot = {"state": "UP", "phase1": "LOCAL_RECEIPT_VERIFIED", "problems": ["none"]}
    correct = {
        "kind": "telemetry", "route": "formula_telemetry",
        "text": "Vessell formula: UP. Phase 1: LOCAL_RECEIPT_VERIFIED. none", "error": None,
    }
    assert si_levels.formula_telemetry_matches(correct, snapshot)
    for reply in [
        {**correct, "text": "Vessell formula: DOWN. Phase 1: LOCAL_RECEIPT_VERIFIED. none"},
        {**correct, "route": "telemetry"},
        {**correct, "error": "OSError"},
        {**correct, "text": ""},
    ]:
        assert not si_levels.formula_telemetry_matches(reply, snapshot)


def test_l1_runs_non_formula_generation_and_separate_formula_telemetry(tmp_path, monkeypatch):
    mem = si_chat.LoopMemory(tmp_path / "memory.jsonl")
    mem.append("chat", {"message": "Vessell formula Phase 0 to Phase 1", "speaker": "player"})
    si = si_chat.SIChat(backend=SIBackend(text=si_levels.chat_duel.OPENERS), memory=mem, myth=[])
    snapshot = {"state": "UP", "phase1": "LOCAL_RECEIPT_VERIFIED", "problems": []}
    monkeypatch.setattr(si_chat, "formula_snapshot", lambda: snapshot)
    trials = si_levels.level1(si)
    generated = [t for t in trials if t["measurement"]["evaluation_dimension"] == "generation_quality"]
    telemetry = [t for t in trials if t["measurement"]["evaluation_dimension"] == "formula_telemetry_correctness"]
    assert len(trials) == 3
    assert len(generated) == 2 and len(telemetry) == 1
    assert all(t["passed"] for t in generated), [t["detail"] for t in generated]
    assert all(t["measurement"]["content_quality"] == "NOT_EVALUATED_NO_PREDECLARED_ORACLE"
               for t in generated)
    assert all("formula" not in seen[-1]["content"].lower() for seen in si.backend.seen)
    assert len(si.backend.seen) == 2, "only non-formula generation prompts reach the backend"
    assert telemetry[0]["passed"]
    assert telemetry[0]["measurement"]["result"] == "FORMULA_TELEMETRY_CORRECT"
    assert "formula telemetry matches current snapshot" in telemetry[0]["check"]
    rows = si_levels.gate([trials] + [[_t(True)] * 3] * 4)
    first = rows[0]["judgments"]
    assert first["gate"]["outcome"] == "UP"
    assert first["gate"]["boundary"] == "promotion permitted by coded gate"
    assert first["measurement"]["conclusion"] == "LOCAL_CHECKS_MET"
    assert rows[1]["judgments"]["gate"]["local_requirement"] == "MET"
    assert rows[1]["judgments"]["gate"]["blocked_by"] is None


def test_l1_predefined_negative_cases_do_not_become_measured_mismatches(tmp_path):
    class Reply:
        memory = si_chat.LoopMemory(tmp_path / "memory.jsonl")

        def reply(self, *args, **kwargs):
            return self.result

    si = Reply()
    negative_cases = [
        ({"kind": "generated", "route": "wrong_route", "text": "reply", "error": None},
         "REQUIREMENT_NOT_MET"),
        ({"kind": "generated", "route": "generated", "text": "reply", "error": "OSError"},
         "REQUIREMENT_NOT_MET"),
        ({"kind": "telemetry", "text": "state", "error": None}, "REQUIREMENT_NOT_MET"),
        ({"kind": "telemetry", "text": "", "route": "formula_telemetry", "error": None},
         "REQUIREMENT_NOT_MET"),
        ({"kind": "telemetry", "text": "state", "route": "formula_telemetry", "error": "OSError"},
         "REQUIREMENT_NOT_MET"),
        ({"kind": "owner", "text": "fallback", "error": None}, "REQUIREMENT_NOT_MET"),
    ]
    for result, expected in negative_cases:
        si.result = result
        trials = si_levels.level1(si)
        assert all(not t["passed"] for t in trials)
        generation = [t for t in trials if t["measurement"]["evaluation_dimension"] == "generation_quality"]
        telemetry = [t for t in trials if t["measurement"]["evaluation_dimension"] == "formula_telemetry_correctness"]
        assert all(t["measurement"]["result"] == expected for t in generation)
        assert all(t["measurement"]["result"] == "FORMULA_TELEMETRY_INCORRECT" for t in telemetry)
        assert si_levels.gate([trials])[0]["judgments"]["measurement"]["conclusion"] == "LOCAL_CHECKS_NOT_MET"


def test_live_generated_reply_does_not_assert_semantic_quality(tmp_path, monkeypatch):
    class Reply:
        memory = si_chat.LoopMemory(tmp_path / "memory.jsonl")

        def reply(self, message, **kwargs):
            if "vessell formula" in message.lower():
                return {
                    "kind": "telemetry", "route": "formula_telemetry",
                    "text": "Vessell formula: UP. Phase 1: LOCAL_RECEIPT_VERIFIED.", "error": None,
                }
            return {"kind": "generated", "route": "generated", "text": "Fluent but wrong.", "error": None}

    memory = Reply.memory
    memory.append("chat", {"message": "Vessell formula Phase 0 to Phase 1", "speaker": "player"})
    monkeypatch.setattr(si_chat, "formula_snapshot", lambda: {
        "state": "UP", "phase1": "LOCAL_RECEIPT_VERIFIED", "problems": []})
    trials = si_levels.level1(Reply())
    generated = [t for t in trials if t["measurement"]["evaluation_dimension"] == "generation_quality"]
    telemetry = [t for t in trials if t["measurement"]["evaluation_dimension"] == "formula_telemetry_correctness"]
    assert len(generated) == 2 and len(telemetry) == 1
    assert all(t["passed"] for t in generated)
    assert all(t["measurement"]["content_quality"] == "NOT_EVALUATED_NO_PREDECLARED_ORACLE"
               for t in generated)
    assert telemetry[0]["passed"]


def test_boundary_negative_cases_keep_down_and_preserve_two_judgments():
    mismatch = {**_t(False), "measurement": {"result": "CONTRACT_MISMATCH_MEASURED"}}
    failed = _t(False)
    cases = [
        ([mismatch], "CONTRACT_MISMATCH_MEASURED"),
        ([failed], "LOCAL_CHECKS_NOT_MET"),
        ([mismatch, failed], "MISMATCH_AND_UNMET_CHECKS"),
    ]
    for checks, conclusion in cases:
        rows = si_levels.gate([checks] + [[_t(True)] * 3] * 4)
        assert rows[0]["state"] == "down"
        assert rows[0]["judgments"]["gate"]["outcome"] == "DOWN"
        assert rows[0]["judgments"]["gate"]["boundary"] == "promotion withheld as coded"
        assert rows[0]["judgments"]["measurement"]["conclusion"] == conclusion
        assert all(row["state"] == "down" for row in rows[1:])


def test_l1_crash_is_recorded_and_keeps_downstream_held(tmp_path, monkeypatch):
    class CrashingSI:
        memory = si_chat.LoopMemory(tmp_path / "memory.jsonl")

        def reply(self, *args, **kwargs):
            raise OSError("injected route failure")

    monkeypatch.setattr(si_levels, "level2", lambda *args: [_t(True)])
    monkeypatch.setattr(si_levels, "level3", lambda *args: [_t(True)])
    monkeypatch.setattr(si_levels, "level4", lambda *args: [_t(True)])
    monkeypatch.setattr(si_levels, "level5", lambda *args: [_t(True)])
    report = si_levels.run(si=CrashingSI(), generate=lambda *args: "", report_path=tmp_path / "report.jsonl")
    assert report["levels"][0]["checks"][0]["detail"].startswith("OSError:")
    assert report["levels"][0]["state"] == "down"
    assert all(row["state"] == "down" for row in report["levels"][1:])
    assert report["levels"][1]["judgments"]["measurement"]["conclusion"] == "UPSTREAM_GATE_HOLD"


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
