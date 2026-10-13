"""Public-domain folklore layer for the SI chat (hidden in game view).

Sources are pre-1929 English translations verified on Project Gutenberg. Texts
are cached locally (git-ignored) and pinned by SHA-256 in ``LOCK``. Passages are
background lore only: they are kept apart from owner text, never presented as
owner writing, and inspire *original* characters rather than any modern
franchise character (for example, no Sub-Zero / Mortal Kombat likeness).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "myth_corpus" / "cache"
LOCK = ROOT / "data" / "myth_corpus" / "lock.json"
GUTENBERG = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"


@dataclass(frozen=True)
class MythSource:
    id: str
    gutenberg: int
    title: str
    translator: str
    year: int
    tradition: str
    pd_basis: str


SOURCES = (
    MythSource("kwaidan", 1210, "Kwaidan", "Lafcadio Hearn", 1904, "japanese", "US: published before 1929"),
    MythSource("poetic-edda", 73533, "The Poetic Edda", "Henry Adams Bellows", 1923, "norse", "US: published 1923"),
    MythSource("younger-edda", 18947, "The Younger Edda", "Rasmus B. Anderson", 1880, "norse", "US: pre-1929"),
    MythSource("beowulf", 16328, "Beowulf", "J. Lesslie Hall", 1892, "anglo-saxon", "US: published before 1929"),
    MythSource("mabinogion", 5160, "The Mabinogion", "Lady Charlotte Guest", 1877, "welsh", "US: pre-1929"),
    MythSource("volsungs", 1152, "The Story of the Volsungs", "Magnusson & Morris", 1888, "norse", "US: pre-1929"),
)

# Mission (1-based) -> folklore themes matching the level's setting.
MISSION_THEMES = {
    1: ("record", "chronicle", "rune", "wisdom", "mimir"),
    2: ("forge", "smith", "fire", "dragon", "gold"),
    3: ("snow", "frost", "ice", "winter", "cold"),
    4: ("star", "dragon", "night", "moon", "shining"),
    5: ("frost", "giant", "ice", "sea", "ymir"),
}
THEMES = frozenset(word for words in MISSION_THEMES.values() for word in words)
_WORD = re.compile(r"[a-z]+")


def strip_gutenberg(text: str) -> str:
    start = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG[^\n]*\n", text)
    end = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG", text)
    return text[start.end() if start else 0 : end.start() if end else len(text)]


def fetch(sources: tuple[MythSource, ...] = SOURCES) -> dict[str, str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    lock: dict[str, str] = {}
    for source in sources:
        path = CACHE / f"{source.id}.txt"
        if not path.exists():
            with urllib.request.urlopen(GUTENBERG.format(id=source.gutenberg), timeout=60) as response:
                path.write_bytes(response.read())
        lock[source.id] = hashlib.sha256(path.read_bytes()).hexdigest()
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock, indent=2) + "\n")
    return lock


def passages(text: str, source: MythSource) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", strip_gutenberg(text)):
        flat = " ".join(block.split())
        if not 160 <= len(flat) <= 700 or flat.isupper() or "gutenberg" in flat.lower():
            continue
        words = set(_WORD.findall(flat.lower()))
        tags = sorted(words & THEMES)
        if tags:
            out.append({"source": source.id, "tradition": source.tradition, "tags": tags, "text": flat})
    return out


def load(cache: Path = CACHE) -> list[dict[str, Any]]:
    """Return tagged passages from cached texts whose hashes match ``LOCK``."""
    if not LOCK.exists():
        return []
    lock = json.loads(LOCK.read_text())
    found: list[dict[str, Any]] = []
    for source in SOURCES:
        path = cache / f"{source.id}.txt"
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != lock.get(source.id):
            continue
        found.extend(passages(path.read_text(encoding="utf-8", errors="replace"), source))
    return found


class MythRetriever:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items

    def search(self, query: str, mission: int | None = None, limit: int = 1) -> list[dict[str, Any]]:
        wanted = set(_WORD.findall(query.lower())) | set(MISSION_THEMES.get(mission or 0, ()))
        scored = [(len(wanted & set(item["tags"])), -len(item["text"]), i) for i, item in enumerate(self.items)]
        best = sorted((s for s in scored if s[0] > 0), reverse=True)[:limit]
        return [self.items[i] for _score, _length, i in best]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch and summarise the public-domain folklore layer.")
    parser.add_argument("--fetch", action="store_true", help="download missing texts and rewrite the hash lock")
    args = parser.parse_args(argv)
    if args.fetch:
        fetch()
    items = load()
    counts: dict[str, int] = {}
    for item in items:
        counts[item["source"]] = counts.get(item["source"], 0) + 1
    print(json.dumps({"passages": len(items), "by_source": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
