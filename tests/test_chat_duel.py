# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
from vessell import chat_duel, si_chat
from tests.test_si_chat import SIBackend


def _si(tmp_path):
    mem = si_chat.LoopMemory(tmp_path / "m.jsonl")
    mem.append("chat", {"message": "where is the exit?", "text": "x", "reply_kind": "generated"})
    mem.append("chat", {"message": "[episode]", "text": "y", "reply_kind": "owner"})
    calls = []
    web = si_chat.WebSearch(fetch=lambda q: calls.append(q) or {})
    si = si_chat.SIChat(backend=SIBackend(), memory=mem, myth=[], web=web)
    si.web_calls = calls
    return si


def test_clean_lesson_rejects_digits_and_missing_label():
    assert chat_duel.clean_lesson("LESSON: Name one concrete next move.") == "Name one concrete next move."
    assert chat_duel.clean_lesson("LESSON: Say you have 3 lives left.") is None
    assert chat_duel.clean_lesson("just be nicer") is None


def test_converse_uses_real_player_question_and_feeds_lessons_back(tmp_path):
    si = _si(tmp_path)

    def si_model(model, messages, max_tokens):
        return "LESSON: Name one concrete next move." if "LESSON" in messages[0]["content"] else "Why trust you?"

    recs = chat_duel.run(1, "test", generate=si_model, si=si, turns=2)
    rec = recs[0]
    assert rec["opener"] == "where is the exit?"
    assert [t["who"] for t in rec["transcript"]] == ["rook", "si", "rook", "si"]
    assert rec["transcript"][2]["text"] == "Why trust you?" and rec["status"].startswith("NOT_VERIFIED")
    rows = si.memory.load()
    assert sum(r["kind"] == "lesson" for r in rows) == 2 and rows[-1]["kind"] == "dialogue"
    # Rival turns are not replayed as player questions, and the lesson reaches the SI prompt.
    assert chat_duel.player_questions(si.memory) == ["where is the exit?"]
    si.reply("hi")
    system = si.backend.seen[-1][0]["content"]
    assert "Coaching from sparring" in system and "Name one concrete next move." in system
    assert "Why trust you?" not in system
    # The playtester's opener never goes to web search; Rook's own follow-up does.
    assert si.web_calls == ["Why trust you?"]
