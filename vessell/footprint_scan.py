"""Self-scan for one's own usernames with WhatsMyName rules, matched to JustDeleteMe fixes.

Data sources (fetched into the git-ignored ``private/sources`` folder, never committed):
- WhatsMyName ``wmn-data.json`` by Micah Hoffman, CC BY-SA 4.0
  (https://github.com/WebBreacher/WhatsMyName)
- JustDeleteMe ``_data/sites.json``, MIT (https://github.com/jdm-contrib/jdm)

Only public profile URLs are requested. A hit means a profile with that username exists;
it does not prove the profile belongs to the owner. Every finding is UNCONFIRMED until the
owner confirms it, and fixes are drafts: this module never signs in, deletes or submits.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable

from vessell import footprint

PRIVATE = footprint.ROOT / "private"
SOURCES = PRIVATE / "sources"
WMN_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
JDM_URL = "https://raw.githubusercontent.com/jdm-contrib/jdm/master/_data/sites.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
SEVERITY_BY_CAT = {"xx NSFW xx": "high", "dating": "high", "finance": "high", "political": "high",
                   "social": "medium", "shopping": "medium", "health": "medium", "business": "medium"}
JDM_SEVERITY_BUMP = {"impossible": "high", "hard": "medium"}

Fetch = Callable[[str, str, bytes | None, dict[str, str]], tuple[int, str]]


def variants(full_name: str) -> list[str]:
    """Common username forms of a full name (first, middle, last)."""
    parts = [p for p in re.findall(r"[a-z]+", full_name.lower())]
    if len(parts) < 2:
        return parts
    first, last, mids = parts[0], parts[-1], parts[1:-1]
    short = {"christopher": "chris", "william": "will", "robert": "rob", "michael": "mike"}.get(first)
    out = [first + last, f"{first}.{last}", f"{first}_{last}", first[0] + last, f"{first}-{last}"]
    if mids:
        out += ["".join(parts), first[0] + mids[0][0] + last, first + mids[0][0] + last]
    if short:
        out += [short + last, f"{short}.{last}", f"{short}_{last}"]
    return list(dict.fromkeys(out))


def http_fetch(url: str, method: str = "GET", body: bytes | None = None,
               headers: dict[str, str] | None = None, timeout: float = 12) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body, method=method, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(400_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(200_000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""


def check(site: dict[str, Any], user: str, fetch: Fetch) -> str:
    """Return 'hit', 'miss' or 'unclear' using the site's WhatsMyName rules."""
    url = site["uri_check"].replace("{account}", user)
    body = site.get("post_body")
    data = body.replace("{account}", user).encode() if body else None
    try:
        code, text = fetch(url, "POST" if data else "GET", data, site.get("headers") or {})
    except Exception:
        return "unclear"
    if code == site.get("e_code") and site.get("e_string", "") in text:
        return "hit"
    if code == site.get("m_code") and site.get("m_string", "") in text:
        return "miss"
    return "unclear"


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def jdm_index(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {_key(r["name"]): r for r in rows if r.get("name")}


def finding(site: dict[str, Any], user: str, jdm: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fix = jdm.get(_key(site["name"]))
    sev = SEVERITY_BY_CAT.get(site.get("cat", ""), "low")
    if fix and footprint.SEVERITIES.index(JDM_SEVERITY_BUMP.get(fix.get("difficulty"), "low")) < footprint.SEVERITIES.index(sev):
        sev = JDM_SEVERITY_BUMP[fix["difficulty"]]
    pretty = site.get("uri_pretty") or site["uri_check"]
    row = {"name": site["name"], "category": "account", "severity": sev, "source": "WhatsMyName self-scan",
           "username": user, "url": pretty.replace("{account}", user), "site_category": site.get("cat"),
           "ownership": "UNCONFIRMED — owner must confirm this profile is theirs"}
    if fix:
        row["fix"] = {"how": "JustDeleteMe", "url": fix.get("url"), "difficulty": fix.get("difficulty"),
                      "notes": fix.get("notes")}
    return row


def load_sources(refresh: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    SOURCES.mkdir(parents=True, exist_ok=True)
    for url, name in ((WMN_URL, "wmn-data.json"), (JDM_URL, "jdm-sites.json")):
        path = SOURCES / name
        if refresh or not path.exists():
            code, text = http_fetch(url, timeout=30)
            if code != 200:
                raise SystemExit(f"could not fetch {url}: HTTP {code}")
            path.write_text(text, "utf-8")
    wmn = json.loads((SOURCES / "wmn-data.json").read_text("utf-8"))["sites"]
    jdm = json.loads((SOURCES / "jdm-sites.json").read_text("utf-8"))
    return [s for s in wmn if s.get("valid", True)], jdm


def scan(users: list[str], sites: list[dict[str, Any]], jdm: list[dict[str, Any]],
         fetch: Fetch = http_fetch, workers: int = 16,
         progress: Callable[[int, int], None] | None = None) -> dict[str, Any]:
    index = jdm_index(jdm)
    jobs = [(s, u) for u in users for s in sites]
    counts = {"hit": 0, "miss": 0, "unclear": 0}
    findings: list[dict[str, Any]] = []

    def run(job: tuple[dict[str, Any], str]) -> tuple[dict[str, Any], str, str]:
        return job[0], job[1], check(job[0], job[1], fetch)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (site, user, result) in enumerate(pool.map(run, jobs), 1):
            counts[result] += 1
            if result == "hit":
                findings.append(finding(site, user, index))
            if progress and i % 200 == 0:
                progress(i, len(jobs))
    findings.sort(key=lambda r: (footprint.SEVERITIES.index(r["severity"]), r["name"].lower(), r["username"]))
    return {"schema": "vessell-footprint-scan/v1", "at": time.time(), "usernames": users, "sites": len(sites),
            "counts": counts, "findings": findings, "status": "UNCONFIRMED / NOT_VERIFIED",
            "attribution": ["WhatsMyName data by Micah Hoffman, CC BY-SA 4.0",
                            "JustDeleteMe data, MIT licence"]}


def save(result: dict[str, Any], scan_path: Path = footprint.PRIVATE_SCAN) -> int:
    """Write the full scan and merge new findings into the private exposures file."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (scan_path.parent / f"wmn-scan-{stamp}.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    seen = set()
    if scan_path.exists():
        for line in scan_path.read_text("utf-8").splitlines():
            try:
                r = json.loads(line)
                seen.add((r.get("name"), r.get("username")))
            except json.JSONDecodeError:
                continue
    added = 0
    with scan_path.open("a", encoding="utf-8") as fh:
        for r in result["findings"]:
            if (r["name"], r["username"]) not in seen:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                added += 1
    return added


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vessell-footprint-scan", description=__doc__.splitlines()[0])
    ap.add_argument("full_name", help="your own name; usernames are derived from it")
    ap.add_argument("--username", action="append", default=[], help="extra username to check (repeatable)")
    ap.add_argument("--only", help="check only these comma-separated derived/extra usernames")
    ap.add_argument("--refresh", action="store_true", help="re-download the WhatsMyName/JustDeleteMe data")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args(argv)
    users = list(dict.fromkeys(variants(args.full_name) + args.username))
    if args.only:
        users = [u for u in args.only.split(",") if u]
    sites, jdm = load_sources(args.refresh)
    print(f"checking {len(users)} usernames x {len(sites)} sites: {', '.join(users)}", flush=True)
    result = scan(users, sites, jdm, workers=args.workers,
                  progress=lambda i, n: print(f"  {i}/{n}", flush=True))
    added = save(result)
    print(f"hits {result['counts']['hit']} · misses {result['counts']['miss']} · unclear {result['counts']['unclear']}"
          f" · {added} new rows in private/exposures.jsonl (git-ignored)")
    for r in result["findings"][:40]:
        fix = r.get("fix", {})
        print(f"  [{r['severity'].upper()}] {r['name']} · {r['username']} · {r['url']}"
              + (f" · delete: {fix.get('difficulty')} {fix.get('url')}" if fix else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
