"""Quoted-name search-engine sweep of one's own name (owner self-audit, read-only).

Queries public search result pages (Bing, Brave) for an exact-phrase name, keeps
result URL, title and snippet, and classifies each hit with simple heuristics. Results
are written only to the git-ignored ``private/`` folder. Classifications are
UNCONFIRMED: a page may be about someone else with the same name.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from vessell import footprint
from vessell.footprint_scan import http_fetch

# Well-known US people-search / background-check sites (heuristic list; extend as needed).
BROKERS = {
    "spokeo.com", "whitepages.com", "beenverified.com", "truepeoplesearch.com", "fastpeoplesearch.com",
    "radaris.com", "mylife.com", "intelius.com", "peoplefinders.com", "thatsthem.com", "instantcheckmate.com",
    "truthfinder.com", "clustrmaps.com", "nuwber.com", "peekyou.com", "usphonebook.com", "familytreenow.com",
    "zabasearch.com", "addresses.com", "searchpeoplefree.com", "peoplesearchnow.com", "cyberbackgroundchecks.com",
    "neighbor.report", "officialusa.com", "advancedbackgroundchecks.com", "voterrecords.com", "rocketreach.co",
    "zoominfo.com", "contactout.com", "signalhire.com", "lead411.com", "idcrawl.com", "ussearch.com",
    "publicrecordsnow.com", "arounddeal.com", "datanyze.com", "prospeo.io", "smartbackgroundchecks.com", "peoplelooker.com", "spyfly.com", "veripages.com",
}
SOCIAL = {"facebook.com", "linkedin.com", "instagram.com", "x.com", "twitter.com", "tiktok.com", "youtube.com",
          "reddit.com", "github.com", "pinterest.com", "researchgate.net", "medium.com", "threads.net"}
PII_TERMS = re.compile(r"\b(age \d+|address|phone|relatives|lives in|born|current residence|email)\b", re.I)

Fetch = Callable[..., tuple[int, str]]


def _host(url: str) -> str:
    h = urlparse(url).hostname or ""
    return h[4:] if h.startswith("www.") else h


def _strip(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _bing_target(href: str) -> str:
    href = html.unescape(href)
    m = re.search(r"[?&]u=a1([^&]+)", href)
    if not m:
        return href
    raw = m.group(1)
    try:
        return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "replace")
    except ValueError:
        return href


def parse_bing(page: str) -> list[dict[str, str]]:
    out = []
    for block in re.split(r'<li class="b_algo"', page)[1:]:
        a = re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not a:
            continue
        snip = re.search(r'<p[^>]*>(.*?)</p>', block, re.S)
        out.append({"url": _bing_target(a.group(1)), "title": _strip(a.group(2)),
                    "snippet": _strip(snip.group(1)) if snip else "", "engine": "bing"})
    return out


def parse_brave(page: str) -> list[dict[str, str]]:
    out = []
    for m in re.finditer(r'<a href="(https://[^"]+)" target="_self" class="[^"]*\bl1\b[^"]*"[^>]*>(.*?)</a>', page, re.S):
        title = re.search(r'class="title[^"]*"[^>]*>(.*?)</div>', m.group(2), re.S)
        out.append({"url": html.unescape(m.group(1)), "title": _strip(title.group(1) if title else m.group(2)),
                    "snippet": "", "engine": "brave"})
    return out


def search(phrase: str, fetch: Fetch = http_fetch, pages: int = 2, pause: float = 2.0) -> list[dict[str, str]]:
    """Brave honours exact-phrase quotes; Bing's scraped page often ignores them, so its hits must
    still contain the surname to be kept."""
    q = urllib.parse.quote_plus(f'"{phrase}"')
    surname = re.findall(r"[a-z]+", phrase.lower())[-1]
    results: list[dict[str, str]] = []
    for p in range(pages):
        for wait in (0, 15, 40):
            time.sleep(wait if fetch is http_fetch else 0)
            code, page = fetch(f"https://search.brave.com/search?q={q}&offset={p}")
            if code != 429:
                break
        if code == 200:
            results += parse_brave(page)
        time.sleep(pause)
    code, page = fetch(f"https://www.bing.com/search?q={q}&count=10")
    if code == 200:
        results += parse_bing(page)
    seen, unique = set(), []
    for r in results:
        key = r["url"].split("#")[0].rstrip("/")
        if surname not in f"{key} {r['title']} {r['snippet']}".lower():
            continue
        if key.startswith("http") and key not in seen and "bing.com" not in _host(key):
            seen.add(key)
            unique.append(r)
    return unique


def classify(result: dict[str, str], phrase: str) -> dict[str, Any]:
    host = _host(result["url"])
    text = f"{result['title']} {result['snippet']}"
    exact = phrase.lower() in text.lower()
    if any(host == b or host.endswith("." + b) for b in BROKERS) or re.search(r"background check|people search", text, re.I):
        cat, sev = "data_broker", "critical" if PII_TERMS.search(text) else "high"
    elif any(host == s or host.endswith("." + s) for s in SOCIAL):
        cat, sev = "account", "medium"
    else:
        cat, sev = "web_mention", "medium" if PII_TERMS.search(text) else "low"
    return {"name": host, "category": cat, "severity": sev, "source": f"search engine ({result['engine']})",
            "url": result["url"], "snippet": (result["title"] + " — " + result["snippet"]).strip(" —")[:300],
            "ownership": "UNCONFIRMED — check this page is about you" + ("" if exact else " (exact phrase not in snippet)")}


def save(rows: list[dict[str, Any]], scan_path: Path = footprint.PRIVATE_SCAN) -> int:
    seen = set()
    if scan_path.exists():
        for line in scan_path.read_text("utf-8").splitlines():
            try:
                seen.add(json.loads(line).get("url"))
            except json.JSONDecodeError:
                continue
    scan_path.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    with scan_path.open("a", encoding="utf-8") as fh:
        for r in rows:
            if r["url"] not in seen:
                seen.add(r["url"])
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                added += 1
    return added


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vessell-name-search", description=__doc__.splitlines()[0])
    ap.add_argument("phrase", nargs="+", help="exact phrase(s) to search, e.g. your full name")
    ap.add_argument("--pages", type=int, default=3)
    args = ap.parse_args(argv)
    rows = []
    for phrase in args.phrase:
        hits = search(phrase, pages=args.pages)
        rows += [classify(r, phrase) for r in hits]
        print(f'"{phrase}": {len(hits)} results', flush=True)
    rows.sort(key=lambda r: (footprint.SEVERITIES.index(r["severity"]), r["name"]))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (footprint.PRIVATE_SCAN.parent / f"name-search-{stamp}.json").write_text(json.dumps(rows, indent=2) + "\n", "utf-8")
    added = save(rows)
    for r in rows:
        print(f"  [{r['severity'].upper()}] {r['category']} · {r['url']}")
    print(f"{added} new rows in private/exposures.jsonl (git-ignored) · UNCONFIRMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
