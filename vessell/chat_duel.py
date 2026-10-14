"""Sparring loop: a second local chatbot (Rook) talks to the SI and coaches it.

Rook runs on a local Ollama model (default llama3.1). Conversations open with
real player questions from the SI loop memory. The SI answers through the
normal ``SIChat.reply`` pipeline (grounding checks and fallbacks intact). After
each exchange Rook writes one style rule; the SI retrieves the latest rules
into its prompt. This is prompt retrieval, not model training. Everything is
generated and local; coaching suggestions await human review.
"""

from __future__ import annotations

import argparse
import re
import time
import urllib.error
from typing import Any

from vessell.idea_loop import DEFAULT_MODEL, Generate, ollama_generate
from vessell.si_chat import LoopMemory, SIChat

STATUS = "GENERATED COACHING / PENDING_HUMAN_REVIEW"
ROOK = (
    "You are Rook, a veteran fixer who spars with a younger AI radio operator called the SI in a "
    "cyberpunk shooter. You talk like a player: blunt, curious, a little cynical. Ask one short "
    "follow-up question or challenge per turn, under 25 words. Never invent game numbers."
)
COACH = (
    "Judge the SI's last radio reply to the player. Write exactly one line starting with "
    "'LESSON:' giving a short general style rule (under 20 words) that would make its next reply "
    "more useful to a player. No numbers, names or game facts in the rule."
)
OPENERS = ["What should I do first?", "Who are you, really?", "How do I survive the next fight?"]


def player_questions(memory: LoopMemory, n: int = 20) -> list[str]:
    """Real questions playtesters typed into the in-game chat."""
    out = [str(r.get("message", "")) for r in memory.load()
           if r.get("kind") == "chat" and r.get("speaker", "player") == "player"]
    out = [q for q in out if q and not q.startswith("[")]
    return list(dict.fromkeys(reversed(out)))[:n] or OPENERS


def clean_lesson(text: str) -> str | None:
    m = re.search(r"LESSON:\s*(.+)", text or "")
    if not m:
        return None
    lesson = m.group(1).strip().strip('"').splitlines()[0][:160]
    # Rules are style advice only; anything carrying digits could smuggle in invented facts.
    if re.search(r"\d", lesson) or len(lesson.split()) < 3:
        return None
    return lesson


def converse(opener: str, si: SIChat, generate: Generate, model: str = DEFAULT_MODEL,
             turns: int = 3, web: bool = True) -> dict[str, Any]:
    transcript: list[dict[str, str]] = []
    question = opener
    lessons: list[str] = []
    for turn in range(turns):
        # Turn 0 is a playtester's verbatim question, so it is never sent to web search.
        answer = si.reply(question, view="game", speaker="rival", search=web and turn > 0)
        transcript += [{"who": "rook", "text": question}, {"who": "si", "text": answer["text"],
                                                             "kind": answer["kind"]}]
        log = "\n".join(f"{t['who'].upper()}: {t['text']}" for t in transcript)
        lesson = clean_lesson(generate(model, [{"role": "system", "content": COACH},
                                               {"role": "user", "content": log}], 60))
        if lesson:
            lessons.append(lesson)
            si.memory.append("lesson", {"lesson": lesson, "opener": opener, "status": STATUS})
        if turn + 1 < turns:
            question = generate(model, [{"role": "system", "content": ROOK},
                                        {"role": "user", "content": log + "\nROOK:"}], 50)
            question = question.replace("ROOK:", "").strip().splitlines()[0][:300] if question.strip() else opener
    record = {"opener": opener, "model": model, "transcript": transcript, "lessons": lessons, "status": STATUS}
    si.memory.append("dialogue", record)
    return record


def run(rounds: int = 2, model: str = DEFAULT_MODEL, generate: Generate | None = None,
        si: SIChat | None = None, turns: int = 3, web: bool = True) -> list[dict[str, Any]]:
    si = si or SIChat()
    generate = generate or ollama_generate()
    questions = player_questions(si.memory)
    return [converse(questions[i % len(questions)], si, generate, model, turns, web) for i in range(rounds)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vessell-spar", description=__doc__.splitlines()[0])
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--turns", type=int, default=3)
    ap.add_argument("--model", default=DEFAULT_MODEL, help="local Ollama model for Rook")
    ap.add_argument("--forever", action="store_true")
    ap.add_argument("--no-web", action="store_true", help="keep Rook's follow-ups offline")
    ap.add_argument("--pause", type=float, default=120)
    args = ap.parse_args(argv)
    while True:
        try:
            for rec in run(args.rounds, args.model, turns=args.turns, web=not args.no_web):
                print("\n--- opener: " + rec["opener"], flush=True)
                for t in rec["transcript"]:
                    print(f"  {t['who'].upper()}: {t['text']}", flush=True)
                for lesson in rec["lessons"]:
                    print(f"  LESSON: {lesson}", flush=True)
        except (urllib.error.URLError, OSError) as exc:
            print(f"Ollama unreachable ({exc}).", flush=True)
            if not args.forever:
                return 1
        if not args.forever:
            print(f"\nLogged to loop memory ({STATUS}).")
            return 0
        time.sleep(args.pause)


if __name__ == "__main__":
    raise SystemExit(main())
