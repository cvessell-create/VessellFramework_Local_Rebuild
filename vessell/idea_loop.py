# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""SI <-> framework-agent game-idea loop on a local Ollama model.

SI (the in-game voice) pitches game ideas from the autopilot loop log; the
framework agent critiques each pitch with declared assumptions, the episodes it
rests on and a playtest that could disconfirm it. Everything stays on
127.0.0.1. Output is generated derivative text: NOT_VERIFIED and pending
human review, never an approved design or a claim about the owner's intent.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from vessell.si_chat import MEMORY_PATH, OLLAMA_URL, PERSONA, ROOT, LoopMemory

SCHEMA = "vessell-game-idea/v1"
IDEAS_PATH = ROOT / "outputs" / "game_ideas" / "ideas.jsonl"
DEFAULT_MODEL = "llama3.1"
STATUS = "NOT_VERIFIED / PENDING_HUMAN_REVIEW"

GAME_BRIEF = (
    "Game: 'Hail to the Analyst', a mature (17+) retro shooter. Isometric 3D city layer "
    "(Vessell City: Downtown/Safehouse hub, The Archive, Skyline District, Fabrication Plant; "
    "later Frost Yard, Starlight Boulevard, Glacier Dock, Shadow Dossier) plus a first-person "
    "raycaster for missions (V toggles). Existing systems: walls block fire, catwalks/rooftops "
    "give height, grenades (T), hacking (H), roll, jetpack, RED/BLUE clearance doors, metro "
    "fast travel, hex minimap (M), skills/augments (K), loadout, XP and in-game credits only. "
    "An autopilot learner plays missions and the SI radio comments on each run."
)

AGENT_ROLE = (
    "You are the VessellFramework analyst agent reviewing a game-design pitch. Be concrete and "
    "brief. Reply in exactly these labelled lines:\n"
    "IDEA: one-sentence refined version of the pitch\n"
    "EVIDENCE: which loop episodes or SI lines it rests on (cite E# / S# ids), or NOT_SUPPLIED\n"
    "ASSUMPTIONS: what must be true for it to work\n"
    "DISCONFIRMER: an autopilot or playtest result that would show it is a bad idea\n"
    "SLICE: smallest buildable first step using existing systems\n"
    "RISK: scope, fairness or rule conflicts (no real money, telemetry opt-in and local)\n"
    "Do not claim it has been tested or approved."
)

Generate = Callable[[str, list[dict[str, str]], int], str]


def ollama_generate(url: str = OLLAMA_URL, timeout: float = 180) -> Generate:
    def gen(model: str, messages: list[dict[str, str]], max_tokens: int) -> str:
        body = {"model": model, "messages": messages, "stream": False,
                "options": {"temperature": 0.8, "num_predict": max_tokens}}
        req = urllib.request.Request(url.rstrip("/") + "/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return str(json.loads(resp.read()).get("message", {}).get("content", "")).strip()
    return gen


def digest(rows: list[dict[str, Any]], n: int = 12) -> tuple[str, dict[str, Any]]:
    """Summarise the loop log with stable ids the agent can cite."""
    episodes = [r for r in rows if r.get("kind") == "episode"]
    si = [r for r in rows if r.get("kind") == "chat" and r.get("reply_kind") == "generated" and r.get("text")]
    outcomes = Counter((e.get("mission"), e.get("outcome")) for e in episodes)
    lines = [f"Totals: {len(episodes)} runs, " + ", ".join(
        f"mission {m}: {c} {o}" for (m, o), c in sorted(outcomes.items(), key=lambda x: str(x[0])))]
    refs: dict[str, Any] = {}
    for i, e in enumerate(episodes[-n:], 1):
        refs[f"E{i}"] = {k: e.get(k) for k in ("generation", "mission", "outcome", "kills", "fitness", "seconds", "at")}
        lines.append(f"E{i}: mission {e.get('mission')} {e.get('outcome')}, kills {e.get('kills')}, "
                     f"fitness {e.get('fitness')}, {e.get('seconds')}s")
    for i, c in enumerate(si[-6:], 1):
        refs[f"S{i}"] = {"text": c["text"], "at": c.get("at")}
        lines.append(f"S{i}: SI said \"{c['text'][:220]}\"")
    return "\n".join(lines), refs


def parse_review(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    key = None
    for raw in text.splitlines():
        line = raw.strip().lstrip("*-# ").replace("**", "")
        head, sep, rest = line.partition(":")
        if sep and head.strip().upper() in {"IDEA", "EVIDENCE", "ASSUMPTIONS", "DISCONFIRMER", "SLICE", "RISK"}:
            key = head.strip().lower()
            out[key] = rest.strip()
        elif key and line:
            out[key] += " " + line
    return out


def run(rounds: int = 3, model: str = DEFAULT_MODEL, generate: Generate | None = None,
        memory: LoopMemory | None = None, out_path: Path = IDEAS_PATH, focus: str = "") -> list[dict[str, Any]]:
    gen = generate or ollama_generate()
    log_text, refs = digest((memory or LoopMemory(MEMORY_PATH)).load())
    si_system = (f"{PERSONA}\n\nRight now you are off the radio, pitching game ideas to the design "
                 f"team. {GAME_BRIEF}\nLoop log:\n{log_text}")
    agent_system = f"{AGENT_ROLE}\n\n{GAME_BRIEF}\nLoop log:\n{log_text}"
    results, previous = [], []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for r in range(1, rounds + 1):
        ask = ("Pitch ONE new game idea (mechanic, enemy, district beat, gadget or mission) grounded in "
               "what the loop log shows. Two or three sentences." + (f" Focus: {focus}." if focus else ""))
        if previous:
            ask += " Do not repeat these: " + " | ".join(previous)
        pitch = gen(model, [{"role": "system", "content": si_system}, {"role": "user", "content": ask}], 160)
        review_text = gen(model, [{"role": "system", "content": agent_system},
                                  {"role": "user", "content": f"SI pitch:\n{pitch}"}], 360)
        review = parse_review(review_text)
        record = {"schema": SCHEMA, "round": r, "at": time.time(), "model": f"ollama:{model}",
                  "status": STATUS, "label": "generated derivative of loop telemetry; not owner text",
                  "si_pitch": pitch, "agent_review": review, "agent_raw": review_text,
                  "evidence_refs": {k: v for k, v in refs.items() if k in review.get("evidence", "")}}
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        results.append(record)
        previous.append(review.get("idea") or pitch[:120])
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vessell-ideas", description=__doc__.splitlines()[0])
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--model", default=DEFAULT_MODEL, help="local Ollama model name")
    ap.add_argument("--focus", default="", help="optional theme, e.g. 'Skyline District'")
    ap.add_argument("--forever", action="store_true", help="repeat until stopped (overnight)")
    ap.add_argument("--pause", type=float, default=60, help="seconds between batches with --forever")
    args = ap.parse_args(argv)
    while True:
        try:
            for rec in run(args.rounds, args.model, focus=args.focus):
                rv = rec["agent_review"]
                print(f"\n[{rec['round']}] SI: {rec['si_pitch']}\n    IDEA: {rv.get('idea', '?')}\n"
                      f"    SLICE: {rv.get('slice', '?')}\n    DISCONFIRMER: {rv.get('disconfirmer', '?')}", flush=True)
        except (urllib.error.URLError, OSError) as exc:
            print(f"Ollama unreachable ({exc}); start it with `ollama serve`.", flush=True)
            if not args.forever:
                return 1
        if not args.forever:
            print(f"\nSaved to {IDEAS_PATH} ({STATUS}).")
            return 0
        time.sleep(args.pause)


if __name__ == "__main__":
    raise SystemExit(main())
