"""Owner-authored story corpus for the game's SI Level 1 (chatbot) learning loop.

Extracts sentences from owner-designated writing and exports them, with
line numbers and SHA-256 hashes, to the game repository. The game may select
and display these lines but cannot rewrite them; any edit breaks the hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "vessell-si-story-corpus/v1"


@dataclass(frozen=True)
class Source:
    path: str
    role: str
    # Heading prefixes whose sections are not exported.
    exclude: tuple[str, ...] = ()


SOURCES: tuple[Source, ...] = (
    # Section 1 is the owner's personal incident account; it stays out of a public game.
    Source("docs/claim-correction-case-study.md", "author-paper",
           ("# How", "## 1.", "## References")),
    Source("SKILL.md", "skill"),
    Source("VesselFramework_Knowing_Field_SKILL_v0.1.md", "skill"),
    Source("Knowing_Field_Theory_SKILL_v0.1.md", "skill"),
    Source("VesselFramework_Game_Theory_SKILL_v0.1.md", "skill"),
    Source("Game_Theory_Theory_SKILL_v0.1.md", "skill"),
)

# SI Level 1 stages follow the paper's six mechanisms, in order.
STAGES: tuple[dict, ...] = (
    {"id": "intake", "name": "Intake", "milestone": "first episode recorded",
     "keywords": ["intake", "source", "tagged", "provenance", "record"]},
    {"id": "corroboration", "name": "Corroboration", "milestone": "two episodes with kills",
     "keywords": ["corroborat", "independent", "evidence", "root"]},
    {"id": "gate", "name": "Gate", "milestone": "first mission exit passed",
     "keywords": ["gate", "waiver", "consequential", "release", "authori"]},
    {"id": "status", "name": "Status", "milestone": "three champion improvements",
     "keywords": ["status", "uncertain", "confidence", "label", "assumption"]},
    {"id": "dependents", "name": "Dependents", "milestone": "exits passed in two missions",
     "keywords": ["dependen", "cascade", "downstream", "propagat"]},
    {"id": "correction", "name": "Correction", "milestone": "improvement after a death",
     "keywords": ["correct", "retract", "disavow", "revis", "supersed"]},
)

_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z*\"(])")
_LIST = re.compile(r"^(\s*)([-*+]|\d+\.)\s+")


def sha256(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def collapse(text: str) -> str:
    return " ".join(text.split())


def paragraphs(text: str, exclude: tuple[str, ...]):
    """Yield (heading, first_line, last_line, joined_text) for prose blocks."""
    lines = text.splitlines()
    i, heading, skipping, fence = 0, "", False, False
    if lines and lines[0].strip() == "---":
        i = next((n for n in range(1, len(lines)) if lines[n].strip() == "---"), 0) + 1
    block: list[tuple[int, str]] = []

    def flush():
        if block and not skipping:
            yield heading, block[0][0], block[-1][0], collapse(" ".join(t for _, t in block))
        block.clear()

    for n in range(i, len(lines)):
        raw = lines[n]
        s = raw.strip()
        if s.startswith("```"):
            yield from flush()
            fence = not fence
            continue
        if fence:
            continue
        if s.startswith("#"):
            yield from flush()
            heading = s
            skipping = any(s.startswith(p) for p in exclude)
            continue
        if not s or s.startswith(("|", "<", ">", "---")):
            yield from flush()
            continue
        m = _LIST.match(raw)
        if m:
            yield from flush()
            block.append((n + 1, raw[m.end():]))
            continue
        block.append((n + 1, s))
    yield from flush()


def stage_of(text: str) -> str:
    low = text.lower()
    scores = [(sum(low.count(k) for k in st["keywords"]), -idx, st["id"]) for idx, st in enumerate(STAGES)]
    best = max(scores)
    return best[2] if best[0] > 0 else "general"


def extract(root: Path = ROOT) -> dict:
    lines_out, sources_out = [], []
    for src in SOURCES:
        data = (root / src.path).read_bytes()
        sources_out.append({"path": src.path, "role": src.role, "sha256": sha256(data)})
        for heading, first, last, para in paragraphs(data.decode("utf-8"), src.exclude):
            for sentence in _SENTENCE.split(para):
                sentence = sentence.strip()
                if (not 40 <= len(sentence) <= 240 or "](" in sentence or "http" in sentence
                        or not sentence[0].isupper() or len(sentence.split()) < 7):
                    continue
                lines_out.append({
                    "id": f"{Path(src.path).stem}:{first}:{sha256(sentence)[:8]}",
                    "source": src.path, "role": src.role, "section": heading.lstrip("# "),
                    "line_start": first, "line_end": last, "stage": stage_of(sentence),
                    "text": sentence, "sha256": sha256(sentence),
                })
    return {
        "schema": SCHEMA,
        "authority": "Owner-designated writing; selection only, text is never rewritten.",
        "verbatim_rule": "text equals a whitespace-collapsed substring of lines line_start..line_end",
        "si_level": {"number": 1, "label": "Chatbots (OpenAI five-level ladder)"},
        "stages": [{k: v for k, v in st.items()} for st in STAGES],
        "sources": sources_out,
        "lines": lines_out,
    }


def verify(corpus: dict, root: Path = ROOT) -> list[str]:
    """Return problems; empty list means every line is verbatim and unmodified."""
    problems, cache = [], {}
    for line in corpus["lines"]:
        if sha256(line["text"]) != line["sha256"]:
            problems.append(f"hash mismatch: {line['id']}")
            continue
        src = cache.setdefault(line["source"], (root / line["source"]).read_text("utf-8").splitlines())
        window = collapse(" ".join(src[line["line_start"] - 1:line["line_end"]]))
        if line["text"] not in window:
            problems.append(f"not verbatim: {line['id']}")
    return problems


def to_js(corpus: dict) -> str:
    body = json.dumps(corpus, ensure_ascii=False, indent=1)
    return ("// Generated by VessellFramework vessell/story_corpus.py. Do not edit; regenerate.\n"
            "(function (root) {\n  'use strict';\n  const corpus = " + body + ";\n"
            "  if (typeof module === 'object' && module.exports) module.exports = corpus;\n"
            "  else root.HailStoryCorpus = corpus;\n"
            "})(typeof globalThis === 'object' ? globalThis : this);\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vessell-story", description=__doc__.splitlines()[0])
    ap.add_argument("--game-dir", default=str(ROOT.parent / "hail-to-the-analyst"))
    ap.add_argument("--check", action="store_true", help="verify only, do not write")
    args = ap.parse_args(argv)
    corpus = extract()
    problems = verify(corpus)
    if problems:
        print("\n".join(problems))
        return 1
    counts = {st["id"]: 0 for st in STAGES} | {"general": 0}
    for line in corpus["lines"]:
        counts[line["stage"]] += 1
    print(f"{len(corpus['lines'])} verbatim lines from {len(SOURCES)} sources; by stage: {counts}")
    if not args.check:
        out = Path(args.game_dir) / "engine" / "si-story-corpus.js"
        out.write_text(to_js(corpus), "utf-8")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
