"""Phase 1: local signed receipts and an offline verifier.

Receipts commit to loop output files with a domain-separated Merkle tree and
an HMAC-SHA256 tag. Everything is local: no chain, wallet, timestamp calendar
or network call. The key lives in the git-ignored ``private/`` directory and
is never committed. HMAC means only a holder of the same key can verify; a
receipt is an integrity record, not proof of truth, time, payment or credit.

    python -m vessell.receipts sign [--loop phase0] [paths...]
    python -m vessell.receipts verify RECEIPT.json [--check-files]
    python -m vessell.receipts prove RECEIPT.json PATH
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KEY_PATH = ROOT / "private" / "receipt_hmac.key"
RECEIPT_DIR = ROOT / "outputs" / "receipts"
SCHEMA = "vessell-receipt/v1"
ALG = "HMAC-SHA256"
STATUS = "LOCAL INTEGRITY RECORD - NOT ANCHORED - PENDING HUMAN REVIEW"
DEFAULT_PATHS = ["outputs/si_chat/memory.jsonl", "outputs/si_levels/report.jsonl",
                 "outputs/si_levels/ideas.jsonl", "outputs/game_ideas/ideas.jsonl",
                 "outputs/phase0/latest.json"]


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def load_key(path: Path = KEY_PATH, create: bool = False) -> bytes:
    if not path.exists():
        if not create:
            raise FileNotFoundError(f"no receipt key at {path}; run 'sign' once to create it")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(secrets.token_bytes(32))
        os.chmod(path, 0o600)
    key = path.read_bytes()
    if len(key) < 32:
        raise ValueError("receipt key shorter than 32 bytes")
    return key


def key_id(key: bytes) -> str:
    return hashlib.sha256(b"vessell-receipt-key-id\x00" + key).hexdigest()[:16]


def leaf_hash(leaf: dict[str, str]) -> bytes:
    return hashlib.sha256(b"\x00" + canonical({"path": leaf["path"], "sha256": leaf["sha256"]})).digest()


def _node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _levels(leaves: list[dict[str, str]]) -> list[list[bytes]]:
    level = [leaf_hash(x) for x in leaves]
    if not level:
        raise ValueError("a receipt needs at least one leaf")
    levels = [level]
    while len(level) > 1:
        # An odd last node is promoted unchanged, so no leaf is ever duplicated.
        level = [_node(level[i], level[i + 1]) if i + 1 < len(level) else level[i]
                 for i in range(0, len(level), 2)]
        levels.append(level)
    return levels


def merkle_root(leaves: list[dict[str, str]]) -> str:
    return _levels(leaves)[-1][0].hex()


def membership_proof(leaves: list[dict[str, str]], index: int) -> list[dict[str, str]]:
    proof = []
    for level in _levels(leaves)[:-1]:
        sibling = index ^ 1
        if sibling < len(level):
            proof.append({"side": "left" if sibling < index else "right", "hash": level[sibling].hex()})
        index //= 2
    return proof


def verify_membership(leaf: dict[str, str], proof: list[dict[str, str]], root: str) -> bool:
    acc = leaf_hash(leaf)
    for step in proof:
        sib = bytes.fromhex(step["hash"])
        acc = _node(sib, acc) if step["side"] == "left" else _node(acc, sib)
    return hmac.compare_digest(acc.hex(), root)


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def file_leaves(paths: list[Path]) -> list[dict[str, str]]:
    leaves = {}
    for p in paths:
        if p.exists():
            leaves[_rel(p)] = {"path": _rel(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    return [leaves[k] for k in sorted(leaves)]


def _tag(body: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical(body), hashlib.sha256).hexdigest()


def sign(leaves: list[dict[str, str]], key: bytes, loop_id: str,
         supersedes: str | None = None, run_at: float | None = None) -> dict[str, Any]:
    paths = [x["path"] for x in leaves]
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate leaf path")
    body = {"schema": SCHEMA, "alg": ALG, "key_id": key_id(key), "loop_id": loop_id,
            "run_at": time.time() if run_at is None else run_at, "leaves": leaves,
            "merkle_root": merkle_root(leaves), "supersedes": supersedes,
            "anchored": False, "status": STATUS}
    body["receipt_id"] = hashlib.sha256(canonical(body)).hexdigest()
    return {**body, "tag": _tag(body, key)}


def verify(receipt: dict[str, Any], key: bytes, check_files: bool = False,
           root_dir: Path = ROOT) -> list[str]:
    """Return problems; an empty list means the receipt verifies."""
    problems = []
    body = {k: v for k, v in receipt.items() if k != "tag"}
    if receipt.get("schema") != SCHEMA or receipt.get("alg") != ALG:
        problems.append("unknown schema or algorithm")
    if receipt.get("key_id") != key_id(key):
        problems.append("key_id does not match this key (rotated or wrong key)")
    if not hmac.compare_digest(str(receipt.get("tag", "")), _tag(body, key)):
        problems.append("tag mismatch: receipt altered or signed with another key")
    leaves = receipt.get("leaves") or []
    paths = [x.get("path") for x in leaves]
    if len(set(paths)) != len(paths):
        problems.append("duplicate leaf path")
    if not leaves:
        problems.append("no leaves")
    elif receipt.get("merkle_root") != merkle_root(leaves):
        problems.append("merkle root does not match leaves")
    id_body = {k: v for k, v in body.items() if k != "receipt_id"}
    if receipt.get("receipt_id") != hashlib.sha256(canonical(id_body)).hexdigest():
        problems.append("receipt_id does not match body")
    if check_files:
        for leaf in leaves:
            p = root_dir / leaf["path"]
            if not p.exists():
                problems.append(f"missing file: {leaf['path']}")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != leaf["sha256"]:
                problems.append(f"file changed since receipt: {leaf['path']}")
    return problems


def gate(problems: list[str]) -> str:
    """UP = NOT DOWN: one problem anywhere makes the receipt DOWN."""
    return "UP" if not problems else "DOWN"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vessell.receipts", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sign")
    s.add_argument("paths", nargs="*")
    s.add_argument("--loop", default="phase0")
    s.add_argument("--supersedes")
    v = sub.add_parser("verify")
    v.add_argument("receipt")
    v.add_argument("--check-files", action="store_true")
    p = sub.add_parser("prove")
    p.add_argument("receipt")
    p.add_argument("path")
    a = ap.parse_args(argv)

    if a.cmd == "sign":
        key = load_key(create=True)
        paths = [Path(x) if Path(x).is_absolute() else ROOT / x for x in (a.paths or DEFAULT_PATHS)]
        rec = sign(file_leaves(paths), key, a.loop, a.supersedes)
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        out = RECEIPT_DIR / f"{int(rec['run_at'])}-{rec['receipt_id'][:12]}.json"
        out.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"signed {len(rec['leaves'])} leaves · root {rec['merkle_root'][:16]}… · {_rel(out)}")
        return 0

    rec = json.loads(Path(a.receipt).read_text())
    if a.cmd == "verify":
        problems = verify(rec, load_key(), check_files=a.check_files)
        for x in problems:
            print("DOWN:", x)
        print(f"GATE: {gate(problems)} · {STATUS}")
        return 0 if not problems else 1

    target = _rel(Path(a.path) if Path(a.path).is_absolute() else ROOT / a.path)
    idx = next((i for i, x in enumerate(rec["leaves"]) if x["path"] == target), None)
    if idx is None:
        print(f"DOWN: {target} not in receipt")
        return 1
    proof = membership_proof(rec["leaves"], idx)
    ok = verify_membership(rec["leaves"][idx], proof, rec["merkle_root"])
    print(json.dumps({"leaf": rec["leaves"][idx], "proof": proof, "gate": "UP" if ok else "DOWN"}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
