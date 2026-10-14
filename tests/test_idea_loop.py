# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
import json

from vessell import idea_loop
from vessell.si_chat import LoopMemory


def _memory(tmp_path):
    m = LoopMemory(tmp_path / "m.jsonl")
    m.append("episode", {"generation": 5, "mission": 0, "outcome": "dead", "kills": 3, "fitness": 400, "seconds": 40})
    m.append("chat", {"message": "[episode]", "text": "Catwalk snipers chewed you up, Analyst.", "reply_kind": "generated"})
    m.append("chat", {"message": "[episode]", "text": "Owner line.", "reply_kind": "owner"})
    return m


def test_digest_cites_episodes_and_only_generated_si_lines(tmp_path):
    text, refs = idea_loop.digest(_memory(tmp_path).load())
    assert "E1: mission 0 dead" in text and "S1:" in text and "Owner line" not in text
    assert set(refs) == {"E1", "S1"}


def test_parse_review_reads_labelled_lines_and_continuations():
    r = idea_loop.parse_review("**IDEA:** Sniper nests\nEVIDENCE: E1, S1\nSLICE: one catwalk\n  with a turret\nnoise")
    assert r["idea"] == "Sniper nests" and r["evidence"] == "E1, S1"
    assert r["slice"] == "one catwalk with a turret noise"


def test_run_alternates_si_and_agent_and_marks_output_unverified(tmp_path):
    calls = []

    def fake(model, messages, max_tokens):
        calls.append(messages[-1]["content"])
        if "pitching game ideas" in messages[0]["content"]:
            return "Drop sniper drones on the Plant catwalks."
        return "IDEA: Catwalk sniper drones\nEVIDENCE: E1\nDISCONFIRMER: autopilot deaths double\nSLICE: one drone"

    out = tmp_path / "ideas.jsonl"
    recs = idea_loop.run(2, "test", generate=fake, memory=_memory(tmp_path), out_path=out)
    assert len(calls) == 4 and "Do not repeat these: Catwalk sniper drones" in calls[2]
    rows = [json.loads(x) for x in out.read_text().splitlines()]
    assert len(rows) == 2 and all(r["status"] == idea_loop.STATUS for r in rows)
    assert rows[0]["agent_review"]["idea"] == "Catwalk sniper drones"
    assert set(rows[0]["evidence_refs"]) == {"E1"}
