"""Delete documentation lines that only restate an implemented, tested constant.

A Markdown line is *provable* when every number it states equals the value of a
module-level numeric constant, each such constant shares a name keyword with
the line, and a test imports the constant's module. The code constant plus its
test then carries the claim, so the prose restatement is removed. Every removal
is written to ``docs/traceability/provable-lines-ledger.json`` with the original
text, its SHA-256 and the proving constant/test, so the deletion is auditable.

Owner sources, the author's paper material, source logs and history records are
excluded. Run without ``--apply`` for a dry run.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "traceability" / "provable-lines-ledger.json"

EXCLUDED = (
    re.compile(r"^docs/paper-source-reconciliation"),
    re.compile(r"^docs/owner-fourth-person-perspective\.md$"),
    re.compile(r"^docs/civilian-authorship-and-model-interference\.md$"),
    re.compile(r"^docs/grad-school-prospectus\.md$"),
    re.compile(r"^docs/game-theory/source-log/"),
    re.compile(r"^docs/traceability/"),
    re.compile(r"^case_studies/"),
    re.compile(r"^memory_payloads/"),
    re.compile(r"Path_Sync_Log"),
    re.compile(r"Stale_State_Correction"),
    re.compile(r"(^|/)CHANGELOG"),
)
NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
STOP = {
    "MIN",
    "MAX",
    "THRESHOLD",
    "SCORE",
    "SECONDS",
    "MINUTES",
    "DAYS",
    "BYTES",
    "BASE",
    "VERSION",
}


@dataclass(frozen=True)
class Constant:
    name: str
    value: float
    path: str
    line: int
    module: str
    keywords: frozenset[str]
    anchors: frozenset[str]


def tracked(suffix: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [f for f in out.split() if f.endswith(suffix)]


def keywords(name: str) -> frozenset[str]:
    parts = [p for p in name.split("_") if p and p not in STOP and len(p) > 2]
    return frozenset(p.lower() for p in parts)


def constants() -> list[Constant]:
    found: list[Constant] = []
    for path in tracked(".py"):
        if path.startswith("tests/"):
            continue
        try:
            tree = ast.parse((ROOT / path).read_text())
        except (SyntaxError, UnicodeDecodeError):
            continue
        module = path[:-3].replace("/", ".")
        functions = {
            n.name
            for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and len(n.name) > 6
        }
        anchors = frozenset(functions | {Path(path).stem})
        for node in tree.body:
            target, value = None, None
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                target, value = node.targets[0].id, node.value
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.value is not None
            ):
                target, value = node.target.id, node.value
            if target is None or value is None or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", target):
                continue
            try:
                literal = ast.literal_eval(value)
            except ValueError:
                continue
            if isinstance(literal, bool) or not isinstance(literal, (int, float)):
                continue
            words = keywords(target)
            if words:
                found.append(
                    Constant(target, float(literal), path, node.lineno, module, words, anchors)
                )
    return found


def tested_modules() -> dict[str, str]:
    covered: dict[str, str] = {}
    for path in tracked(".py"):
        if not path.startswith("tests/"):
            continue
        for match in re.finditer(
            r"^\s*(?:from|import)\s+([\w.]+)", (ROOT / path).read_text(), re.MULTILINE
        ):
            covered.setdefault(match.group(1), path)
    return covered


NEGATION = re.compile(r"\b(no|not|never|without)\b", re.IGNORECASE)


def proof(
    line: str, pool: list[Constant], covered: dict[str, str]
) -> list[dict[str, object]] | None:
    if line.lstrip().startswith(("#", "|---", "| ---")) or NEGATION.search(line):
        return None
    numbers = {float(n) for n in NUMBER.findall(line)}
    if not numbers:
        return None
    words = set(re.findall(r"[a-z]+", line.lower()))
    proofs: list[dict[str, object]] = []
    for number in numbers:
        match = next(
            (c for c in pool if c.value == number and c.keywords & words and c.module in covered),
            None,
        )
        if match is None:
            return None
        proofs.append(
            {
                "value": number,
                "constant": match.name,
                "code": f"{match.path}:{match.line}",
                "test": covered[match.module],
            }
        )
    return proofs


def run(apply: bool) -> list[dict[str, object]]:
    pool, covered = constants(), tested_modules()
    entries: list[dict[str, object]] = []
    for path in tracked(".md"):
        if any(rule.search(path) for rule in EXCLUDED):
            continue
        document = (ROOT / path).read_text()
        local = [c for c in pool if any(a in document for a in c.anchors)]
        lines = document.splitlines(keepends=True)
        keep: list[str] = []
        fenced = False
        for number, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
            following = lines[number] if number < len(lines) else ""
            wrapped = (
                following.startswith("  ")
                and following.strip()
                and not following.lstrip().startswith(("-", "*", "|"))
            )
            found = (
                None
                if fenced or wrapped or line.lstrip().startswith("```")
                else proof(line, local, covered)
            )
            if found is None:
                keep.append(line)
                continue
            text = line.rstrip("\n")
            entries.append(
                {
                    "file": path,
                    "line": number,
                    "text": text,
                    "sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "proven_by": found,
                }
            )
        if apply and len(keep) != len(lines):
            (ROOT / path).write_text("".join(keep))
    if apply and entries:
        prior = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
        LEDGER.write_text(json.dumps(prior + entries, indent=2, ensure_ascii=False) + "\n")
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="delete matched lines and append the ledger"
    )
    args = parser.parse_args()
    entries = run(args.apply)
    for entry in entries:
        print(f"{entry['file']}:{entry['line']}: {str(entry['text'])[:100]}")
    print(f"{'removed' if args.apply else 'would remove'} {len(entries)} line(s)")


if __name__ == "__main__":
    main()
