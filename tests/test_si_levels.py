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
    assert report["status"].startswith("NOT_VERIFIED")
    assert json.loads((tmp_path / "r.jsonl").read_text())["levels"][4]["level"] == "L5 Organization"
    # Probe traffic is not treated as playtester questions.
    from vessell import chat_duel
    assert chat_duel.player_questions(mem) == ["where is the exit?"]
