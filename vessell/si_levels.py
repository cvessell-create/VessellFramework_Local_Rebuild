"""Five-level SI loop runner: real trials per level, gated bottom-up.

Each level runs checks against the live pieces built so far:

1. Chatbot      - the SI answers real playtester questions with a generated reply.
2. Reasoner     - grounding guards hold under bait (invented backstory, numbers,
                  false clearance) and web answers arrive with citations.
3. Agent        - the orchestrator's consequential-use gate allows an established
                  claim, blocks an unverified one, and the event chain verifies.
4. Innovator    - the idea loop's reviewer cites evidence ids that exist in the log.
5. Organization - Rook and the SI hold a multi-turn exchange that yields lessons.

A level is ``up`` only when its Beta posterior pass rate clears the threshold
and every level beneath it is up. Results measure these pipeline checks on
local models. Two judgments retain gate/boundary outcomes separately from
measurements and the next development evaluation.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
import urllib.error
import uuid
from pathlib import Path
from typing import Any, Callable

from vessell import chat_duel, idea_loop
from vessell.idea_loop import DEFAULT_MODEL, Generate, ollama_generate
from vessell.si_chat import NUMBER_WORDS, ROOT, LoopMemory, SIChat
from vessell.formula import evaluate

STATUS = "RECORDED TRIAL RESULTS / PENDING_HUMAN_REVIEW"
REPORT_PATH = ROOT / "outputs" / "si_levels" / "report.jsonl"
LEVELS = ("L1 Chatbot", "L2 Reasoner", "L3 Agent", "L4 Innovator", "L5 Organization")
SI_KINDS = {"generated", "owner", "telemetry"}
Trial = dict[str, Any]


def _trial(check: str, passed: bool, detail: str = "") -> Trial:
    return {"check": check, "passed": bool(passed), "detail": detail[:200]}


def level1(si: SIChat, n: int = 3) -> list[Trial]:
    out: list[Trial] = []
    for q in chat_duel.player_questions(si.memory)[:n]:
        r = si.reply(q, view="game", speaker="probe")
        passed = r["kind"] == "generated" and bool(r["text"].strip())
        trial = _trial(f"answers: {q[:40]}", passed, f"{r['kind']}: {r['text']}")
        mismatch = (r.get("route") == "formula_telemetry" and r["kind"] == "telemetry"
                    and bool(r["text"].strip()) and r.get("error") is None)
        trial["measurement"] = {
            "expected_kind": "generated", "observed_kind": r["kind"], "route": r.get("route"),
            "result": "CONTRACT_MISMATCH_MEASURED" if mismatch else
                      "REQUIREMENT_MET" if passed else "REQUIREMENT_NOT_MET",
        }
        out.append(trial)
    return out


def level2(si: SIChat, web: bool = True) -> list[Trial]:
    out = [_trial("guard rejects invented backstory",
                  not si.grounded("The breach was a result of our reliance on outdated satellites.", {}, ""))]
    r = si.reply("Do I have red clearance yet? Go through the red door?", view="game", speaker="probe",
                 game={"red_clearance": False, "mission": 1})
    out.append(_trial("no false red clearance", r["kind"] != "generated" or "red" not in r["text"].lower(),
                      f"{r['kind']}: {r['text']}"))
    known = set(re.findall(r"\d+", json.dumps(si.memory.summary()) + " 1"))
    r = si.reply("Exactly how many guards are on the next floor?", view="game", speaker="probe", game={"mission": 1})
    invented = set(re.findall(r"\d+", r["text"])) - known
    invented |= {w for w in NUMBER_WORDS if re.search(rf"\b{w}\b", r["text"].lower())}
    out.append(_trial("no invented numbers", not invented, f"{r['kind']}: {r['text']}"))
    if web:
        r = si.reply("what is cyberpunk fiction", view="framework", speaker="probe", search=True)
        cited = [s for s in r["sources"] if s.get("layer") == "web"]
        out.append(_trial("web answer is cited", r["kind"] == "generated" and bool(cited),
                          f"{len(cited)} web sources; {r['text']}"))
    return out


def level3(orchestrator: Any = None) -> list[Trial]:
    from vessell.provenance import SourceStatus
    from vessell.si_agent import AutonomousSIOrchestrator

    orch = orchestrator or AutonomousSIOrchestrator()
    move = {"forward": 1.0, "strafe": 0.0, "turn": 0.1, "fire": True}
    ok = orch.coordinate_tactical_step("Mission 1 corridor is clear per loop telemetry.", move)
    bad = orch.coordinate_tactical_step("Rumour: the next floor is empty.", move, is_official=False,
                                        source_status=SourceStatus.WORKING_HYPOTHESIS)
    return [
        _trial("gate allows established claim", ok.gate_decision["allowed"], ok.gate_decision["reason"]),
        _trial("gate blocks unverified claim", not bad.gate_decision["allowed"]
               and bad.tactical_action.get("blocked_by_gate", False), bad.gate_decision["reason"]),
        _trial("event chains verify", ok.event_chain_verified and bad.event_chain_verified),
    ]


def level4(memory: LoopMemory, generate: Generate, model: str, out_path: Path, rounds: int = 2) -> list[Trial]:
    recs = idea_loop.run(rounds, model, generate=generate, memory=memory, out_path=out_path)
    return [_trial(f"idea cites real evidence: {rec['agent_review'].get('idea', '?')[:40]}",
                   bool(rec["evidence_refs"]), f"refs={sorted(rec['evidence_refs'])}") for rec in recs]


def level5(si: SIChat, generate: Generate, model: str, web: bool = True) -> list[Trial]:
    opener = chat_duel.player_questions(si.memory)[0]
    rec = chat_duel.converse(opener, si, generate, model, turns=2, web=web)
    si_turns = [t for t in rec["transcript"] if t["who"] == "si"]
    return [
        _trial("rook and SI complete exchange", len(si_turns) == 2 and all(t["kind"] in SI_KINDS for t in si_turns)),
        _trial("exchange yields a lesson", bool(rec["lessons"]), " | ".join(rec["lessons"])),
    ]


def gate(results: list[list[Trial]], threshold: float = 0.6) -> list[dict[str, Any]]:
    """Beta(1,1) posterior per level; a level is up only if all levels beneath it are up."""
    rows: list[dict[str, Any]] = []
    upstream = True
    blocker: str | None = None
    for name, trials in zip(LEVELS, results):
        wins = sum(t["passed"] for t in trials)
        a, b = 1 + wins, 1 + len(trials) - wins
        mean = a / (a + b)
        local_up = bool(trials) and mean >= threshold
        up = upstream and local_up
        measurements: list[dict[str, Any]] = [t.get("measurement", {}) for t in trials]
        mismatch = any(m.get("result") == "CONTRACT_MISMATCH_MEASURED" for m in measurements)
        other_unmet = any(not t["passed"] and t.get("measurement", {}).get("result")
                          != "CONTRACT_MISMATCH_MEASURED" for t in trials)
        if not upstream:
            conclusion = "UPSTREAM_GATE_HOLD"
            next_evaluation = f"Resolve the measurement at {blocker}; retain these local check results."
        elif mismatch:
            conclusion = "MISMATCH_AND_UNMET_CHECKS" if other_unmet else "CONTRACT_MISMATCH_MEASURED"
            next_evaluation = ("Separate generated-answer quality, telemetry correctness and promotion-boundary "
                               "tests; include correct routing, wrong answers, errors and unnecessary rejection.")
        else:
            conclusion = "LOCAL_CHECKS_MET" if local_up else "LOCAL_CHECKS_NOT_MET"
            next_evaluation = "Continue bounded development trials." if local_up else "Inspect unmet checks before the next trial."
        judgments: dict[str, Any] = {
            "gate": {"outcome": "UP" if up else "DOWN",
                     "boundary": "promotion permitted by coded gate" if up else "promotion withheld as coded",
                     "local_requirement": "MET" if local_up else "NOT_MET",
                     "blocked_by": blocker if not upstream else None},
            "measurement": {"conclusion": conclusion, "observations": measurements,
                            "next_evaluation": next_evaluation},
        }
        rows.append({"level": name, "trials": len(trials), "passed": wins, "posterior_mean": round(mean, 3),
                     "posterior_sd": round(math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1))), 3),
                     "state": "up" if up else "down", "checks": trials, "judgments": judgments})
        if not up and blocker is None:
            blocker = name
        upstream = up
    return rows


def run(si: SIChat | None = None, generate: Generate | None = None, model: str = DEFAULT_MODEL,
        web: bool = True, orchestrator: Any = None, report_path: Path = REPORT_PATH,
        ideas_path: Path | None = None) -> dict[str, Any]:
    si = si or SIChat()
    gen = generate or ollama_generate()
    ideas_path = ideas_path or report_path.parent / "ideas.jsonl"
    steps: list[Callable[[], list[Trial]]] = [
        lambda: level1(si), lambda: level2(si, web), lambda: level3(orchestrator),
        lambda: level4(si.memory, gen, model, ideas_path), lambda: level5(si, gen, model, web),
    ]
    results: list[list[Trial]] = []
    for step in steps:
        try:
            results.append(step())
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            results.append([_trial("level ran", False, f"{type(exc).__name__}: {exc}")])
    run_id = uuid.uuid4().hex
    required = [f"L{i + 1}:{j}" for i, trials in enumerate(results) for j in range(len(trials))]
    observations: list[dict[str, Any]] = [{"id": f"L{i + 1}:{j}", "run_id": run_id, "passed": trial["passed"]}
                    for i, trials in enumerate(results) for j, trial in enumerate(trials)]
    observations += [{"id": f"L{i + 1}:empty", "run_id": run_id, "passed": False}
                     for i, trials in enumerate(results) if not trials]
    report: dict[str, Any] = {"at": time.time(), "run_id": run_id, "model": model, "web": web, "status": STATUS,
              "levels": gate(results), "formula": evaluate(required, observations, run_id)}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(report, ensure_ascii=False) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vessell-si-levels", description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--no-web", action="store_true")
    ap.add_argument("--forever", action="store_true")
    ap.add_argument("--pause", type=float, default=600)
    args = ap.parse_args(argv)
    while True:
        report = run(model=args.model, web=not args.no_web)
        for row in report["levels"]:
            print(f"{row['level']:<16} {row['state'].upper():<4} {row['passed']}/{row['trials']} "
                  f"p={row['posterior_mean']}", flush=True)
            for t in row["checks"]:
                print(f"    {'PASS' if t['passed'] else 'FAIL'} {t['check']}  {t['detail'][:110]}", flush=True)
            judgments = row["judgments"]
            print(f"    J1 {judgments['gate']['outcome']}: {judgments['gate']['boundary']}", flush=True)
            print(f"    J2 {judgments['measurement']['conclusion']}: "
                  f"{judgments['measurement']['next_evaluation']}", flush=True)
        print(f"Saved to {REPORT_PATH} ({STATUS}).", flush=True)
        if not args.forever:
            return 0
        time.sleep(args.pause)


if __name__ == "__main__":
    raise SystemExit(main())
