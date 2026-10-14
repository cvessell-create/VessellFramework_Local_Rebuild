import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from vessell import si_chat, story_corpus


class SIBackend:
    """Scripted SI stand-in for tests; the real SI is what we are striving toward."""
    name = "si:test"

    def __init__(self, ready=True, text="Push for the red door, Analyst."):
        self.ready, self.text, self.seen = ready, text, []

    def available(self):
        return self.ready

    def generate(self, messages):
        self.seen.append(messages)
        text = self.text if isinstance(self.text, str) else self.text[(len(self.seen) - 1) % len(self.text)]
        return text


@pytest.fixture
def chat(tmp_path):
    return si_chat.SIChat(backend=SIBackend(), memory=si_chat.LoopMemory(tmp_path / "m.jsonl"), myth=[])


def test_generated_reply_is_labelled_derivative_and_keeps_hidden_sources(chat):
    r = chat.reply("how do I pass the gate?", view="game")
    assert r["kind"] == "generated" and "derivative" in r["label"]
    assert r["sources_hidden"] is True and r["sources"]
    ids = {line["id"]: line for line in chat.corpus["lines"]}
    for s in r["sources"]:
        assert story_corpus.sha256(ids[s["id"]]["text"]) == s["sha256"]
    system = chat.backend.seen[0][0]["content"]
    assert "Hidden briefing notes" in system and "Loop telemetry" in system


def test_loop_memory_feeds_later_prompts(chat):
    chat.backend.text = ["Gen 3 is down, Analyst.", "Hold the gate."]
    chat.reply("", event={"generation": 3, "mission": 1, "outcome": "dead", "kills": 2,
                          "fitness": -120, "stage": "gate"})
    summary = chat.memory.summary()
    assert summary["episodes"] == 1 and summary["deaths"] == 1 and summary["stage"] == "gate"
    chat.reply("what now?")
    last = chat.backend.seen[-1]
    assert '"deaths": 1' in last[0]["content"]
    assert not any(m["role"] == "assistant" for m in last), "generated replies are not replayed"


def test_offline_backend_falls_back_to_one_verbatim_owner_line(tmp_path):
    c = si_chat.SIChat(backend=SIBackend(ready=False), memory=si_chat.LoopMemory(tmp_path / "m.jsonl"), myth=[])
    r = c.reply("correction dependents", view="framework")
    assert r["kind"] == "owner" and r["model"] is None and len(r["sources"]) == 1
    line = next(ln for ln in c.corpus["lines"] if ln["id"] == r["sources"][0]["id"])
    assert r["text"] == story_corpus.collapse(line["text"])


def test_http_server_serves_chatbox_and_rejects_foreign_origins(chat):
    server = ThreadingHTTPServer(("127.0.0.1", 0), si_chat.make_handler(chat))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert b"SI CHAT" in urllib.request.urlopen(base + "/").read()

        def post(origin):
            req = urllib.request.Request(base + "/chat", data=json.dumps({"message": "status"}).encode(),
                                         headers={"Content-Type": "application/json", "Origin": origin})
            return urllib.request.urlopen(req)

        resp = post("http://127.0.0.1:8787")
        assert resp.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:8787"
        assert json.loads(resp.read())["kind"] == "generated"
        with pytest.raises(urllib.error.HTTPError) as err:
            post("https://evil.example")
        assert err.value.code == 403
    finally:
        server.shutdown()


def test_loops_page_shows_feed_levels_and_ideas(chat, tmp_path):
    chat.reply("where is the exit?", speaker="player")
    chat.memory.append("lesson", {"lesson": "Answer the question asked."})
    levels, ideas = tmp_path / "r.jsonl", tmp_path / "i.jsonl"
    levels.write_text(json.dumps({"at": 1, "model": "si:test", "levels": [{"level": "L1 Chatbot", "state": "up"}]}) + "\n")
    ideas.write_text(json.dumps({"si_pitch": "From E3: recon run"}) + "\n")
    snap = si_chat.loops_snapshot(chat.memory, levels, ideas)
    assert snap["status"] == "RECORDED LOOP ACTIVITY"
    assert snap["levels"]["levels"][0]["state"] == "up"
    assert snap["ideas"][0]["si_pitch"].startswith("From E3")
    assert [r["kind"] for r in snap["feed"]] == ["chat", "lesson"] and snap["feed"][0]["speaker"] == "player"
    server = ThreadingHTTPServer(("127.0.0.1", 0), si_chat.make_handler(chat))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert b"SI LOOPS" in urllib.request.urlopen(base + "/loops").read()
        assert "feed" in json.loads(urllib.request.urlopen(base + "/loops.json").read())
    finally:
        server.shutdown()


def test_loops_keeps_offline_simulation_separate_and_sanitised(chat, tmp_path):
    from vessell.blockchain_simulation import run
    output = tmp_path / "simulation"
    run(1, out_dir=output, key_path=tmp_path / "key")
    snap = si_chat.loops_snapshot(chat.memory, phase0_path=tmp_path / "missing",
                                  simulation_path=output / "latest.json")
    sim = snap["simulation"]
    assert sim["mode"] == "OFFLINE_SIMULATION"
    assert sim["state"] == "UP" and sim["real_onboarding"] == "NOT_PERFORMED"
    assert snap["formula"]["state"] == "DOWN"
    assert len(sim["cases"]) == 12
    assert str(tmp_path) not in json.dumps(sim)
    (output / "latest.json").write_text("{")
    bad = si_chat.loops_snapshot(chat.memory, phase0_path=tmp_path / "missing",
                                 simulation_path=output / "latest.json")
    assert bad["simulation"]["state"] == "DOWN"
    assert "error" in bad["simulation"]


def test_game_facts_are_sanitised_into_the_prompt(chat):
    chat.reply("ammo?", game={"hp": 40, "bullets": 7, "red_clearance": True, "autopilot_goal": "nav:ammo",
                              "Bad Key": 1, "nested": {"x": 1}, "nan": float("nan")})
    system = chat.backend.seen[-1][0]["content"]
    assert '"game_now": {"hp": 40, "bullets": 7, "red_clearance": true, "autopilot_goal": "nav:ammo"}' in system


def test_situation_and_grounding_guard_reject_invented_clearance(chat):
    facts = {"mission": 2, "hp": 76, "red_clearance": False, "blue_clearance": True, "autopilot_goal": "nav:exit"}
    text = si_chat.SIChat.situation(facts)
    assert "Current objective: exit." in text and "Red clearance NOT held." in text
    r = chat.reply("next objective?", game=facts)  # SI test backend keeps saying "red door"
    assert r["kind"] == "telemetry" and r["error"] == "ungrounded" and len(chat.backend.seen) == 2
    assert r["text"] == text and r["sources"] == [] and "no model" in r["label"]
    chat.backend.text, chat.backend.seen = ["Exit is close, Analyst.", "Exit is close, Analyst.", "Blue is yours. Move."], []
    assert chat.reply("go?", game=facts)["text"] == "Exit is close, Analyst."
    again = chat.reply("go?", game=facts)
    assert again["text"] == "Blue is yours. Move.", "verbatim repeat of the last reply is regenerated"


def test_grounding_guard_rejects_numbers_not_in_facts(chat):
    facts = {"bullets": 34, "red_clearance": True}
    assert chat.grounded("34 bullets left, Analyst.", facts)
    assert not chat.grounded("34 bullets, below the recommended 50.", facts)
    assert chat.grounded("Gen 9 is done.", facts, known='{"generation": 9}')


def test_degenerate_and_long_output_is_trimmed_or_rejected(chat):
    assert si_chat.two_sentences('"One. Two!  Three?"') == "One. Two!"
    assert si_chat.degenerate("Episode 1.0.0.0.0.0.0.0.0.0.0.0.")
    assert not chat.grounded("Episode 1.0.0.0.0.0.0.0.0.0.0.0.", {"mission": 1}, known="0")
    assert not si_chat.degenerate("Exit is close, Analyst.")


def test_myth_layer_is_hidden_public_domain_flavour_matched_to_mission(tmp_path):
    from vessell import myth_corpus

    frost = myth_corpus.MythSource("t", 1, "T", "X", 1900, "japanese", "pd")
    items = myth_corpus.passages(
        "*** START OF THE PROJECT GUTENBERG EBOOK T ***\n\n"
        + "The woman of the snow breathed frost across the sleeping ferryman in the cold winter hut. " * 3
        + "\n\n"
        + "A smith worked gold at the forge while the dragon slept upon the hoard of the barrow. " * 3,
        frost,
    )
    assert {tuple(i["tags"]) for i in items} == {("cold", "frost", "snow", "winter"), ("dragon", "forge", "gold", "smith")}
    c = si_chat.SIChat(backend=SIBackend(text="Hold steady, Analyst."), memory=si_chat.LoopMemory(tmp_path / "m.jsonl"),
                       myth=items)
    r = c.reply("what now?", view="game", game={"mission": 3, "hp": 80})
    system = c.backend.seen[0][0]["content"]
    assert "Hidden folklore" in system and "snow" in system and "forge" not in system
    assert r["sources_hidden"] is True
    assert [s for s in r["sources"] if s.get("layer") == "myth"] == [
        {"id": "myth:t", "cite": "public-domain:t", "layer": "myth"}
    ]


def test_replies_that_mention_hidden_layers_are_rejected(chat):
    assert not chat.grounded("The hidden briefing notes say little.", {})
    assert not chat.grounded("My sources are quiet.", {})
    assert chat.grounded("Hold the line, Analyst.", {})


def test_grounded_rejects_unsourced_causal_backstory(chat):
    invented = "The manual correction was a result of our reliance on old systems that were not updated."
    assert not chat.grounded(invented, {}, "manual correction went down hard")
    assert chat.grounded("Restock because the corridor is hot.", {}, "restock before you trust that corridor hot")
    assert chat.grounded("Hold the line, Analyst.", {}, "")


def _web(calls):
    def fetch(q):
        calls.append(q)
        return {"Heading": "Cyberpunk", "AbstractText": "Cyberpunk is a subgenre of science fiction.",
                "AbstractURL": "https://en.wikipedia.org/wiki/Cyberpunk", "AbstractSource": "Wikipedia",
                "RelatedTopics": [{"Topics": [{"Text": "Neuromancer - 1984 novel", "FirstURL": "https://duckduckgo.com/Neuromancer"}]},
                                  {"Text": "bad", "FirstURL": "http://insecure.example"}]}
    return si_chat.WebSearch(fetch=fetch)


def test_web_search_only_when_requested_and_cited(tmp_path):
    calls = []
    c = si_chat.SIChat(backend=SIBackend(text=["Hold steady, Analyst.", "Cyberpunk is a subgenre of science fiction."]),
                       memory=si_chat.LoopMemory(tmp_path / "m.jsonl"), myth=[], web=_web(calls))
    c.reply("what is cyberpunk", view="game")
    assert calls == []
    r = c.reply("what is cyberpunk", view="framework", search=True)
    assert calls == ["what is cyberpunk"]
    web = [s for s in r["sources"] if s.get("layer") == "web"]
    assert [s["cite"] for s in web] == ["https://en.wikipedia.org/wiki/Cyberpunk", "https://duckduckgo.com/Neuromancer"]
    assert all(s["status"] == "NOT_VERIFIED" for s in web)
    assert "Hidden web results" in c.backend.seen[-1][0]["content"]


def test_web_search_failure_is_silent():
    def boom(q):
        raise OSError("offline")
    assert si_chat.WebSearch(fetch=boom).search("x") == []


def test_grounded_rejects_spelled_out_invented_counts(chat):
    assert not chat.grounded("The next floor is guarded by four guards.", {}, "")
    assert chat.grounded("Four exits remain.", {}, "four exits remain")
def test_formula_question_is_answered_from_observed_status(tmp_path, monkeypatch):
    from vessell import si_chat
    monkeypatch.setattr(si_chat, "formula_snapshot", lambda: {
        "state": "UP", "phase1": "LOCAL_RECEIPT_VERIFIED", "problems": []})
    si = si_chat.SIChat(backend=SIBackend(text=["must not generate"]), memory=si_chat.LoopMemory(tmp_path / "m.jsonl"))
    reply = si.reply("How does the Vessell formula move Phase 0 into Phase 1?")
    assert reply["kind"] == "telemetry"
    assert reply["route"] == "formula_telemetry"
    assert "LOCAL_RECEIPT_VERIFIED" in reply["text"]
    assert reply["sources"] == []
    assert si.memory.load()[-1]["reply_route"] == "formula_telemetry"
