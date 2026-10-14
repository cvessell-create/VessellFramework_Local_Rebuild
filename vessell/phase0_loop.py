# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Phase 0 restart loop: re-scrape blockchain sources, read-only chain touch, re-report every SI loop.

Phase 0 is research plus *read-only* contact with public networks. The loop:

1. Re-scrapes declared primary sources and records a SEARCH RECORD for each.
2. Touches public chains read-only (JSON-RPC ``eth_chainId``/``eth_blockNumber``,
   Bitcoin tip height from two explorers, OpenTimestamps calendar reachability).
   No wallet, key, signature, payment, stamp submission or transaction exists here.
3. Re-reports the other loops (five levels, ideas, sparring lessons, autopilot
   episodes) straight from their raw files, flagging stalls and gaps.
4. Builds an unsigned, unanchored local Merkle preview of loop outputs: the seed
   for Phase 1 local receipts.
5. Optionally asks a local model for Phase 1 steps; steps citing no real R#/L#
   evidence id are dropped.

Output records source access and probe observations, not evidence truth.
All output is PENDING_HUMAN_REVIEW. Passing the Phase 0 gate never
authorizes Phase 1; that remains an owner decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from vessell.si_chat import MEMORY_PATH, OLLAMA_URL, ROOT
from vessell.formula import evaluate

SCHEMA = "vessell-phase0/v1"
STATUS = "RESEARCH OBSERVATIONS / PENDING_HUMAN_REVIEW"
OUT_DIR = ROOT / "outputs" / "phase0"
LEVELS_PATH = ROOT / "outputs" / "si_levels" / "report.jsonl"
IDEA_PATHS = (ROOT / "outputs" / "si_levels" / "ideas.jsonl", ROOT / "outputs" / "game_ideas" / "ideas.jsonl")
DEFAULT_MODEL = "llama3.1"
UA = {"User-Agent": "vessell-phase0/1 (read-only research)"}

SOURCES: list[dict[str, str]] = [
    {"id": "R1", "topic": "OpenTimestamps", "expect": "timestamp", "url": "https://opentimestamps.org/"},
    {"id": "R2", "topic": "OpenTimestamps client", "expect": "ots verify",
     "url": "https://raw.githubusercontent.com/opentimestamps/opentimestamps-client/master/README.md"},
    {"id": "R3", "topic": "x402 standard", "expect": "402", "url": "https://www.x402.org/"},
    {"id": "R4", "topic": "x402 reference repo", "expect": "facilitator",
     "url": "https://raw.githubusercontent.com/coinbase/x402/main/README.md"},
    {"id": "R5", "topic": "Base network connection", "expect": "sepolia",
     "url": "https://docs.base.org/base-chain/quickstart/connecting-to-base"},
    {"id": "R6", "topic": "Base testnet faucets", "expect": "faucet",
     "url": "https://docs.base.org/base-chain/network-information/network-faucets"},
    {"id": "R7", "topic": "Ethereum Attestation Service", "expect": "attestation",
     "url": "https://docs.attest.org/docs/welcome"},
    {"id": "R8", "topic": "Ethereum JSON-RPC", "expect": "eth_blocknumber",
     "url": "https://ethereum.org/en/developers/docs/apis/json-rpc/"},
    {"id": "R9", "topic": "Olas agent services", "expect": "olas", "url": "https://docs.olas.network/"},
    {"id": "R10", "topic": "Virtuals ACP", "expect": "virtuals", "url": "https://whitepaper.virtuals.io/"},
    {"id": "R11", "topic": "Bittensor", "expect": "bittensor", "url": "https://docs.bittensor.com/"},
]

READ_ONLY_RPC = frozenset({"eth_chainId", "eth_blockNumber"})
BASE_SEPOLIA_RPC = "https://sepolia.base.org"
BASE_SEPOLIA_CHAIN_ID = 84532
BTC_TIPS = ("https://blockstream.info/api/blocks/tip/height", "https://mempool.space/api/blocks/tip/height")
OTS_CALENDAR = "https://alice.btc.calendar.opentimestamps.org/"

Fetch = Callable[[str, bytes | None], tuple[int, bytes]]
Generate = Callable[[str, list[dict[str, str]], int], str]


def http_fetch(url: str, body: bytes | None = None, timeout: float = 12) -> tuple[int, bytes]:
    headers = dict(UA)
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(600_000)
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except (urllib.error.URLError, OSError):
        return 0, b""


def _title(raw: bytes) -> str:
    text = raw.decode("utf-8", "replace")
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S) or re.search(r"^#\s+(.+)$", text, re.M)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:120] if m else ""


def rescrape(fetch: Fetch, previous: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Fetch each declared primary source; one SEARCH RECORD per source."""
    previous = previous or {}
    records = []
    for src in SOURCES:
        code, raw = fetch(src["url"], None)
        digest = hashlib.sha256(raw).hexdigest() if raw else ""
        found = bool(raw) and src["expect"].lower() in raw.decode("utf-8", "replace").lower()
        records.append({
            **src, "tool": "urllib GET", "scope": "single primary URL", "http": code, "bytes": len(raw),
            "sha256": digest, "title": _title(raw) if raw else "", "primary_opened": code == 200,
            "content_matches": found, "changed_since_last": bool(previous.get(src["id"])) and previous[src["id"]] != digest,
            "status": "SOURCE OPENED" if code == 200 and found else ("OPENED, EXPECTED TERM MISSING" if code == 200 else "NOT REACHED"),
            "not_checked": "claims inside the page are not independently verified",
        })
    return records


def rpc(fetch: Fetch, url: str, method: str) -> Any:
    if method not in READ_ONLY_RPC:
        raise PermissionError(f"{method} is not a read-only method allowed in Phase 0")
    code, raw = fetch(url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": []}).encode())
    if code != 200 or not raw:
        return None
    try:
        return json.loads(raw).get("result")
    except ValueError:
        return None


def touch(fetch: Fetch) -> list[dict[str, Any]]:
    """Read-only contact with public networks. Nothing is signed, sent, stamped or paid."""
    probes = []
    chain = rpc(fetch, BASE_SEPOLIA_RPC, "eth_chainId")
    chain_id = int(chain, 16) if isinstance(chain, str) and chain.startswith("0x") else None
    probes.append({"id": "T1", "probe": "Base Sepolia eth_chainId", "ok": chain_id == BASE_SEPOLIA_CHAIN_ID,
                   "value": chain_id, "expected": BASE_SEPOLIA_CHAIN_ID})
    block = rpc(fetch, BASE_SEPOLIA_RPC, "eth_blockNumber")
    probes.append({"id": "T2", "probe": "Base Sepolia eth_blockNumber",
                   "ok": isinstance(block, str) and block.startswith("0x"),
                   "value": int(block, 16) if isinstance(block, str) and block.startswith("0x") else None})
    tips = []
    for url in BTC_TIPS:
        code, raw = fetch(url, None)
        tips.append(int(raw) if code == 200 and raw.strip().isdigit() else None)
    agree = all(tips) and abs(tips[0] - tips[1]) <= 2
    probes.append({"id": "T3", "probe": "Bitcoin tip height (blockstream vs mempool.space)", "ok": bool(agree),
                   "value": tips, "note": "two explorers of one chain; agreement is consistency, not independent corroboration"})
    code, _ = fetch(OTS_CALENDAR, None)
    probes.append({"id": "T4", "probe": "OpenTimestamps calendar reachable (GET only, nothing submitted)",
                   "ok": code == 200, "value": code})
    return probes


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text("utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _words(text: str) -> frozenset[str]:
    return frozenset(w for w in re.findall(r"[a-z]{4,}", text.lower()))


def distinct_lessons(lessons: list[str], threshold: float = 0.5) -> list[str]:
    """Greedy near-duplicate filter by word-set Jaccard similarity."""
    kept: list[tuple[frozenset[str], str]] = []
    for text in lessons:
        w = _words(text)
        if w and all(len(w & k) / len(w | k) < threshold for k, _ in kept):
            kept.append((w, text))
    return [t for _, t in kept]


def longest_streak(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    best = {"length": 0}
    run, key = 0, None
    for e in episodes:
        k = (e.get("mission"), e.get("outcome"), e.get("kills"))
        run = run + 1 if k == key else 1
        key = k
        if run > best["length"]:
            best = {"length": run, "mission": k[0], "outcome": k[1], "kills": k[2],
                    "last_generation": e.get("generation")}
    return best


def rereport(memory_path: Path = MEMORY_PATH, levels_path: Path = LEVELS_PATH,
             idea_paths: tuple[Path, ...] = IDEA_PATHS) -> dict[str, Any]:
    """Re-derive every loop's state from raw files; each finding gets an L# id."""
    levels = _jsonl(levels_path)
    mem = _jsonl(memory_path)
    ideas = [r for p in idea_paths for r in _jsonl(p)]
    lv: dict[str, Counter] = {}
    fails: Counter = Counter()
    for run in levels:
        for L in run.get("levels", []):
            lv.setdefault(L["level"], Counter())[L.get("state", "?")] += 1
            for c in L.get("checks", []):
                if not c.get("passed"):
                    fails[f"{L['level']}: {c.get('check', '')[:50]}"] += 1
    kinds = Counter(r.get("kind") for r in mem)
    lessons = [r.get("lesson", "") for r in mem if r.get("kind") == "lesson"]
    uniq = distinct_lessons(lessons)
    episodes = [r for r in mem if r.get("kind") == "episode"]
    outcomes = Counter(f"m{e.get('mission')}:{e.get('outcome')}" for e in episodes)
    streak = longest_streak(episodes)
    themed = sum(bool(re.search(r"st\.? ?louis|municipal|stalker|mobile cit|odni", r.get("si_pitch", ""), re.I)) for r in ideas)
    cited = sum(bool(r.get("evidence_refs")) for r in ideas)
    findings = [
        f"Five-level loop: {len(levels)} runs; " + "; ".join(f"{k} {dict(v)}" for k, v in sorted(lv.items())),
        "Five-level failures: " + (", ".join(f"{k} x{n}" for k, n in fails.most_common(5)) or "none"),
        "L1/L2 checks test presence (a reply, a citation), not correctness or relevance.",
        f"Sparring lessons: {len(lessons)} recorded, about {len(uniq)} distinct after near-duplicate filtering.",
        f"Ideas: {len(ideas)} generated, {cited} with resolvable evidence ids, {themed} mention the St. Louis campaign.",
        f"Autopilot episodes synced: {len(episodes)}; outcomes " + ", ".join(f"{k} x{n}" for k, n in outcomes.most_common(6)),
        (f"STALL: {streak['length']} identical episodes in a row (mission {streak['mission']}, {streak['outcome']}, "
         f"kills {streak['kills']}) up to generation {streak.get('last_generation')}"
         if streak["length"] >= 10 else f"No stall: longest identical streak {streak['length']}"),
        "Phase 0 records read-only contact; optional Phase 1 records local receipts, never chain anchors.",
    ]
    return {"findings": [{"id": f"L{i}", "text": t} for i, t in enumerate(findings, 1)],
            "counts": {"level_runs": len(levels), "memory": dict(kinds), "lessons": len(lessons),
                       "distinct_lessons": len(uniq), "ideas": len(ideas), "ideas_cited": cited,
                       "ideas_on_theme": themed, "episodes": len(episodes)},
            "stall": streak if streak["length"] >= 10 else None,
            "sample_lessons": uniq[:8]}


def merkle_root(digests: list[str]) -> str:
    level = [bytes.fromhex(d) for d in sorted(digests)] or [hashlib.sha256(b"").digest()]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def receipt_preview(paths: list[Path]) -> dict[str, Any]:
    """Unsigned, unanchored local commitment over loop outputs (Phase 1 seed)."""
    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            return p.name

    leaves = [{"path": rel(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
              for p in paths if p.exists()]
    return {"leaves": leaves, "merkle_root": merkle_root([x["sha256"] for x in leaves]),
            "signed": False, "anchored": False,
            "note": "local integrity preview only; not a signature, timestamp proof, payment or credit"}


ROADMAP_ROLE = (
    "You are the VessellFramework research agent planning Phase 1 (local signed receipts and an offline "
    "verifier, no blockchain writes). Use ONLY the evidence lines given. Write 3 to 5 lines, each exactly:\n"
    "STEP: <one concrete engineering step> [ids]\n"
    "where [ids] lists R#/T#/L# ids, e.g. [R2,L7]. Every step MUST combine at least one research id (R# or T#) "
    "with at least one loop finding (L#): say how that research fixes or receipts that loop problem. "
    "Do not restate evidence lines. No wallets, tokens, payments, "
    "mainnet, profit claims or steps needing the owner's money. Do not claim anything was tested."
)

STEP_RE = re.compile(r"STEP:\s*(.+?)\s*\[([A-Z0-9,\s]+)\]\s*$")


def roadmap_steps(text: str, known: set[str], evidence: dict[str, str] | None = None,
                  limit: int = 5) -> list[dict[str, Any]]:
    """Keep steps that cite real ids, mix research (R/T) with loop findings (L), and add new words."""
    evidence = evidence or {}
    steps = []
    for raw in text.splitlines():
        m = STEP_RE.search(raw.strip().replace("**", ""))
        if not m:
            continue
        ids = [i.strip() for i in m.group(2).split(",") if i.strip()]
        valid = [i for i in ids if i in known]
        if not valid or not any(i[0] == "L" for i in valid) or not any(i[0] in "RT" for i in valid):
            continue
        w = _words(m.group(1))
        cited = frozenset().union(*(_words(evidence.get(i, "")) for i in valid))
        if not w or len(w - cited) < 2:
            continue
        steps.append({"step": m.group(1), "evidence": valid, "dropped_ids": [i for i in ids if i not in known]})
    return steps[:limit]


def ollama_generate(url: str = OLLAMA_URL, timeout: float = 240) -> Generate:
    def gen(model: str, messages: list[dict[str, str]], max_tokens: int) -> str:
        body = {"model": model, "messages": messages, "stream": False,
                "options": {"temperature": 0.4, "num_predict": max_tokens}}
        req = urllib.request.Request(url.rstrip("/") + "/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return str(json.loads(resp.read()).get("message", {}).get("content", "")).strip()
    return gen


def gate(sources: list[dict[str, Any]], probes: list[dict[str, Any]], report: dict[str, Any],
         steps: list[dict[str, Any]] | None) -> dict[str, Any]:
    checks = [
        ("primary sources re-opened (>= 80%)", sum(s["status"] == "SOURCE OPENED" for s in sources) >= 0.8 * len(sources)),
        ("read-only chain touch succeeded", all(p["ok"] for p in probes)),
        ("every loop re-reported from raw files", bool(report["findings"])),
        ("Phase 1 steps cite real evidence", steps is None or bool(steps)),
        ("no wallet, key, payment, stamp or transaction", True),
    ]
    done = all(ok for _, ok in checks)
    return {"checks": [{"check": c, "passed": ok} for c, ok in checks],
            "state": "PHASE 0 COMPLETE - PENDING HUMAN REVIEW" if done else "PHASE 0 IN PROGRESS",
            "phase1_authorized": False}


def run(fetch: Fetch = http_fetch, generate: Generate | None = None, model: str = DEFAULT_MODEL,
        out_dir: Path = OUT_DIR, memory_path: Path = MEMORY_PATH, levels_path: Path = LEVELS_PATH,
        idea_paths: tuple[Path, ...] = IDEA_PATHS, phase1: bool = False,
        receipt_key_path: Path | None = None) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = out_dir / "latest.json"
    prev = {}
    if latest.exists():
        try:
            prev = {s["id"]: s["sha256"] for s in json.loads(latest.read_text("utf-8"))["sources"]}
        except (ValueError, KeyError):
            prev = {}
    sources = rescrape(fetch, prev)
    probes = touch(fetch)
    report = rereport(memory_path, levels_path, idea_paths)
    receipts = receipt_preview([memory_path, levels_path, *idea_paths])
    steps = None
    if generate:
        evidence = [f"{s['id']}: {s['topic']} - {s['status']} ({s['url']})" for s in sources]
        evidence += [f"{p['id']}: {p['probe']} -> {'ok' if p['ok'] else 'FAILED'} {p['value']}" for p in probes]
        evidence += [f"{f['id']}: {f['text']}" for f in report["findings"]]
        text = generate(model, [{"role": "system", "content": ROADMAP_ROLE},
                                {"role": "user", "content": "Evidence:\n" + "\n".join(evidence)}], 420)
        lookup = {line.split(":", 1)[0]: line for line in evidence}
        steps = roadmap_steps(text, set(lookup), lookup)
    run_id = uuid.uuid4().hex
    observations: list[dict[str, Any]] = [{"id": s["id"], "run_id": run_id, "passed": s["status"] == "SOURCE OPENED"}
                    for s in sources]
    observations += [{"id": p["id"], "run_id": run_id, "passed": p["ok"]} for p in probes]
    formula = evaluate([s["id"] for s in SOURCES] + ["T1", "T2", "T3", "T4"], observations, run_id)
    record: dict[str, Any] = {"schema": SCHEMA, "run_id": run_id, "at": time.time(), "status": STATUS, "model": f"ollama:{model}" if generate else None,
              "sources": sources, "touch": probes, "rereport": report, "receipt_preview": receipts,
              "phase1_steps": steps, "gate": gate(sources, probes, report, steps),
              "formula": formula, "phase1": {"state": "NOT_REQUESTED", "anchored": False}}
    if phase1:
        if formula["state"] != "UP" or not record["gate"]["state"].startswith("PHASE 0 COMPLETE"):
            record["phase1"] = {"state": "BLOCKED", "anchored": False,
                                "reason": "strict formula and Phase 0 policy must both pass"}
        else:
            from vessell import receipts as local_receipts

            key = local_receipts.load_key(receipt_key_path or local_receipts.KEY_PATH, create=True)
            runs = out_dir / "runs"
            runs.mkdir(exist_ok=True)
            snapshot_path = runs / f"{run_id}.json"
            snapshot_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", "utf-8")
            receipt = local_receipts.sign(local_receipts.file_leaves([snapshot_path]), key,
                                          f"phase0:{run_id}", run_at=record["at"])
            receipt_path = runs / f"{run_id}.receipt.json"
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", "utf-8")
            persisted = json.loads(receipt_path.read_text("utf-8"))
            problems = local_receipts.verify(persisted, key, check_files=True)
            if problems:
                raise ValueError("Phase 1 receipt verification failed: " + "; ".join(problems))
            record["phase1"] = {"state": "LOCAL_RECEIPT_VERIFIED", "anchored": False,
                                "receipt_id": receipt["receipt_id"], "run_id": run_id,
                                "receipt_path": str(receipt_path.resolve()),
                                "snapshot_path": str(snapshot_path.resolve()),
                                "scope": "HMAC and immutable snapshot digest; not evidence truth"}
    with (out_dir / "report.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    latest.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vessell-phase0", description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--no-llm", action="store_true", help="skip generated Phase 1 steps")
    ap.add_argument("--phase1", action="store_true", help="owner-requested local receipt after strict checks pass")
    ap.add_argument("--forever", action="store_true")
    ap.add_argument("--pause", type=float, default=1800)
    args = ap.parse_args(argv)
    while True:
        try:
            rec = run(generate=None if args.no_llm else ollama_generate(), model=args.model, phase1=args.phase1)
        except (urllib.error.URLError, OSError) as exc:
            print(f"Ollama unreachable ({exc}); retry with --no-llm.", flush=True)
            if not args.forever:
                return 1
        else:
            for s in rec["sources"]:
                print(f"{s['id']:4} {s['status']:30} {s['topic']}" + ("  [CHANGED]" if s["changed_since_last"] else ""))
            for p in rec["touch"]:
                print(f"{p['id']:4} {'OK  ' if p['ok'] else 'FAIL'} {p['probe']}: {p['value']}")
            for f in rec["rereport"]["findings"]:
                print(f"{f['id']:4} {f['text']}")
            for s in rec["phase1_steps"] or []:
                print(f"STEP {s['step']}  {s['evidence']}")
            print(f"GATE: {rec['gate']['state']} · Phase 1 authorized: no · {STATUS}", flush=True)
            print(f"VESSELL FORMULA: {rec['formula']['state']} · PHASE 1: {rec['phase1']['state']}", flush=True)
        if not args.forever:
            return 0
        time.sleep(args.pause)


if __name__ == "__main__":
    raise SystemExit(main())
