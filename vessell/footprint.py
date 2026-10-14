"""Digital-footprint triage learned from the FOOTPRINT PURGE game mission.

The game scrubs fictional exposures; its episodes teach a triage order. That order is
applied to the owner's real scan, which lives only in the git-ignored ``private/``
folder. Output is a draft checklist: nothing is sent, deleted or submitted here, and
every step is NOT_VERIFIED / PENDING_OWNER_ACTION until the owner acts on it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from vessell.si_chat import LoopMemory

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_SCAN = ROOT / "private" / "exposures.jsonl"
PLAN_PATH = ROOT / "outputs" / "footprint" / "plan.json"
STATUS = "NOT_VERIFIED / PENDING_OWNER_ACTION"

SEVERITIES = ("critical", "high", "medium", "low")
CATEGORIES = ("data_broker", "dark_web", "account", "leaked_domain", "web_mention")
DIFFICULTIES = ("easy", "medium", "hard", "impossible")
CATEGORY_ALIASES = {"data broker": "data_broker", "dark web": "dark_web", "account": "account",
                    "leaked domain": "leaked_domain", "domain": "leaked_domain", "website": "leaked_domain"}

# Generic owner checklists. They name no specific site or URL; the owner confirms each step.
PLAYBOOK = {
    "data_broker": ["Find the broker's own opt-out or privacy-request page (or use your removal service).",
                    "Submit the removal request; keep the confirmation.",
                    "Re-check the listing after the broker's stated processing time."],
    "dark_web": ["Identify which account or password the leak involves.",
                 "Change that password everywhere it was reused; turn on two-factor sign-in.",
                 "If identity numbers or financial data leaked, consider a credit freeze or fraud alert."],
    "account": ["Sign in and decide: keep, lock down, or delete the account.",
                "Download anything you want to keep, then delete or tighten privacy settings.",
                "Remove saved payment details from accounts you no longer use."],
    "leaked_domain": ["Do not visit the site directly; review what the scan says it exposes.",
                      "Request removal through your removal service or the host's abuse channel.",
                      "Rotate any credential the listing shows."],
    "web_mention": ["Confirm the page is about you and decide whether it is a problem.",
                    "Ask the site owner to remove or edit it; use the search engine's own removal-request tools "
                    "for outdated or personal-information results.",
                    "Once the page changes, request a refresh of the cached result."],
}


def clean_footprints(raw: Any, limit: int = 40) -> list[dict[str, Any]]:
    """Keep only the structured fields the game is allowed to send."""
    out = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        cat, sev = item.get("category"), item.get("severity")
        if cat not in CATEGORIES or sev not in SEVERITIES:
            continue
        fid = str(item.get("id", ""))
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,12}", fid):
            continue
        try:
            t = round(max(0.0, float(item.get("t", 0))), 1)
        except (TypeError, ValueError):
            t = 0.0
        row = {"id": fid, "category": cat, "severity": sev, "t": t}
        if item.get("difficulty") in DIFFICULTIES:
            row["difficulty"] = item["difficulty"]
        out.append(row)
        if len(out) >= limit:
            break
    return out


def learn_policy(memory: LoopMemory) -> dict[str, Any]:
    """Average scrub rank per category from completed purge runs; severity always comes first."""
    runs = [r for r in memory.load(2000) if r.get("kind") == "episode" and r.get("footprints")]
    good = [r for r in runs if r.get("outcome") == "complete"]
    ranks: dict[str, list[float]] = {c: [] for c in CATEGORIES}
    for run in good:
        seq = run["footprints"]
        for i, f in enumerate(seq):
            ranks[f["category"]].append(i / max(1, len(seq) - 1))
    mean = {c: round(sum(v) / len(v), 3) if v else None for c, v in ranks.items()}
    order = sorted(CATEGORIES, key=lambda c: (mean[c] is None, mean[c] if mean[c] is not None else 0, CATEGORIES.index(c)))
    return {"runs": len(runs), "completed": len(good), "category_order": order, "category_mean_rank": mean,
            "severity_order": list(SEVERITIES), "status": "NOT_VERIFIED",
            "note": "Learned from fictional training runs; a heuristic, not a risk assessment."}


def normalise(row: dict[str, Any]) -> dict[str, Any] | None:
    sev = str(row.get("severity", "")).strip().lower()
    cat = str(row.get("category", "")).strip().lower()
    cat = CATEGORY_ALIASES.get(cat, cat.replace(" ", "_"))
    name = str(row.get("name", "")).strip()[:120]
    if sev not in SEVERITIES or cat not in CATEGORIES or not name:
        return None
    out = {"name": name, "category": cat, "severity": sev, "source": str(row.get("source", "owner scan"))[:60]}
    for key in ("url", "username", "ownership", "snippet"):
        if isinstance(row.get(key), str):
            out[key] = row[key][:300]
    if isinstance(row.get("fix"), dict):
        out["fix"] = {k: str(v)[:400] for k, v in row["fix"].items() if v is not None}
    return out


def load_scan(path: Path = PRIVATE_SCAN) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text("utf-8").splitlines():
        try:
            item = normalise(json.loads(line))
        except (json.JSONDecodeError, AttributeError):
            continue
        if item:
            rows.append(item)
    return rows


def parse_scan_text(text: str, source: str = "Serus scan") -> list[dict[str, Any]]:
    """Parse pasted 'Severity / Name / Category' triplets from a scan summary."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = []
    for i, ln in enumerate(lines[:-2]):
        if ln.lower() in SEVERITIES:
            name = re.sub(r"\]\(.*\)$", "", lines[i + 1]).lstrip("[")
            item = normalise({"severity": ln, "name": name, "category": lines[i + 2], "source": source})
            if item:
                out.append(item)
    return out


def _steps(row: dict[str, Any]) -> list[str]:
    steps = []
    if row.get("ownership", "").startswith("UNCONFIRMED"):
        steps.append("Open the link and confirm this profile is actually yours; skip it if not.")
    fix = row.get("fix") or {}
    if fix.get("url"):
        steps.append(f"Deletion ({fix.get('difficulty', 'unknown')}): {fix['url']}"
                     + (f" — {fix['notes']}" if fix.get("notes") else ""))
    return steps + PLAYBOOK[row["category"]]


def build_plan(scan: Iterable[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    cat_rank = {c: i for i, c in enumerate(policy["category_order"])}
    ordered = sorted(scan, key=lambda r: (SEVERITIES.index(r["severity"]), cat_rank[r["category"]], r["name"].lower()))
    items = [{"rank": i + 1, **r, "steps": _steps(r), "status": STATUS}
             for i, r in enumerate(ordered)]
    return {"schema": "vessell-footprint-plan/v1", "at": time.time(), "status": STATUS, "policy": policy,
            "items": items, "limits": ["Drafts only: nothing was sent, deleted or submitted.",
                                       "Scan findings are the scanner's claims and are not independently verified."]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vessell-footprint", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("policy", help="show the triage order learned from game runs")
    sub.add_parser("plan", help="rank the private scan and write a draft checklist to outputs/")
    imp = sub.add_parser("import", help="append pasted scan text (stdin) to the private scan file")
    imp.add_argument("--source", default="Serus scan")
    args = ap.parse_args(argv)
    policy = learn_policy(LoopMemory())
    if args.cmd == "policy":
        print(json.dumps(policy, indent=2))
    elif args.cmd == "import":
        rows = parse_scan_text(sys.stdin.read(), args.source)
        PRIVATE_SCAN.parent.mkdir(parents=True, exist_ok=True)
        with PRIVATE_SCAN.open("a", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"imported {len(rows)} exposures into {PRIVATE_SCAN.relative_to(ROOT)} (git-ignored)")
    else:
        plan = build_plan(load_scan(), policy)
        PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        PLAN_PATH.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", "utf-8")
        for it in plan["items"][:20]:
            print(f"{it['rank']:>3}. [{it['severity'].upper()}] {it['name']} ({it['category']}) -> {it['steps'][0]}")
        print(f"{len(plan['items'])} items · draft written to {PLAN_PATH.relative_to(ROOT)} · {STATUS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
