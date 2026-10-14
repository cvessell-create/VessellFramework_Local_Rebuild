"""Bounded offline fixtures for blockchain onboarding, not a network adapter."""
from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Any

from vessell.formula import evaluate
from vessell.receipts import KEY_PATH, ROOT, file_leaves, load_key, sign, verify

OUT_DIR = ROOT / "outputs" / "blockchain_simulation"
SCHEMA = "vessell-blockchain-simulation/v1"


def simulate(inputs: dict[str, Any], seen_payments: set[str]) -> dict[str, Any]:
    """Evaluate supplied fixture observations; no signer, wallet or network transport."""
    if inputs["chain_id"] != 84532:
        return {"state": "BLOCKED_WRONG_NETWORK", "deliveries": 0}
    if inputs["owner_approval"] is not True:
        return {"state": "BLOCKED_OWNER_DECISION", "deliveries": 0}
    if inputs["privacy_review"] is not True:
        return {"state": "BLOCKED_PRIVACY_REVIEW", "deliveries": 0}
    if inputs["receipt_intact"] is not True:
        return {"state": "BLOCKED_RECEIPT", "deliveries": 0}
    if inputs["anchor"] == "failed":
        return {"state": "FAILED_ANCHOR", "deliveries": 0}
    if inputs["anchor"] != "confirmed":
        return {"state": "PENDING_ANCHOR", "deliveries": 0}
    if inputs["payment_verified"] is not True:
        return {"state": "BLOCKED_PAYMENT", "deliveries": 0}
    payment_id = inputs["payment_id"]
    if payment_id in seen_payments:
        return {"state": "BLOCKED_REPLAY", "deliveries": 0}
    if inputs["settlement"] == "failed":
        return {"state": "FAILED_SETTLEMENT", "deliveries": 0}
    if inputs["settlement"] != "confirmed":
        return {"state": "PENDING_SETTLEMENT", "deliveries": 0}
    if inputs["human_release"] is not True:
        return {"state": "BLOCKED_HUMAN_RELEASE", "deliveries": 0}
    seen_payments.add(payment_id)
    return {"state": "SIMULATED_DELIVERY", "deliveries": 1}


def scenarios() -> list[tuple[str, dict[str, Any], str]]:
    return [
        ("happy_path", {}, "SIMULATED_DELIVERY"),
        ("wrong_network", {"chain_id": 8453}, "BLOCKED_WRONG_NETWORK"),
        ("no_approval", {"owner_approval": False}, "BLOCKED_OWNER_DECISION"),
        ("no_privacy_review", {"privacy_review": False}, "BLOCKED_PRIVACY_REVIEW"),
        ("tampered_receipt", {"receipt_intact": False}, "BLOCKED_RECEIPT"),
        ("pending_anchor", {"anchor": "pending"}, "PENDING_ANCHOR"),
        ("failed_anchor", {"anchor": "failed"}, "FAILED_ANCHOR"),
        ("bad_payment", {"payment_verified": False}, "BLOCKED_PAYMENT"),
        ("replayed_payment", {}, "BLOCKED_REPLAY"),
        ("pending_settlement", {"settlement": "pending"}, "PENDING_SETTLEMENT"),
        ("failed_settlement", {"settlement": "failed"}, "FAILED_SETTLEMENT"),
        ("no_human_release", {"human_release": False}, "BLOCKED_HUMAN_RELEASE"),
    ]


def run(rounds: int = 2, out_dir: Path = OUT_DIR, key_path: Path = KEY_PATH) -> dict[str, Any]:
    if not 1 <= rounds <= 20:
        raise ValueError("rounds must be between 1 and 20")
    run_id = uuid.uuid4().hex
    cases: list[dict[str, Any]] = []
    for round_index in range(rounds):
        baseline: dict[str, Any] = {"chain_id": 84532, "owner_approval": True, "privacy_review": True,
                    "receipt_intact": True, "anchor": "confirmed", "payment_verified": True,
                    "payment_id": "synthetic-payment", "settlement": "confirmed", "human_release": True}
        for name, changes, expected in scenarios():
            seen: set[str] = {"synthetic-payment"} if name == "replayed_payment" else set()
            inputs: dict[str, Any] = {**baseline, **changes}
            result = simulate(inputs, seen)
            replay = simulate(inputs, seen) if name == "happy_path" else None
            passed = result["state"] == expected and result["deliveries"] == (1 if name == "happy_path" else 0)
            if replay is not None:
                passed = passed and replay["state"] == "BLOCKED_REPLAY" and replay["deliveries"] == 0
            cases.append({"id": f"{round_index + 1}:{name}", "run_id": run_id, "passed": passed,
                          "inputs": inputs, "expected": expected, "observed": result, "replay": replay})
    checks = [{k: row[k] for k in ("id", "run_id", "passed")} for row in cases]
    record: dict[str, Any] = {
        "schema": SCHEMA, "run_id": run_id, "at": time.time(), "mode": "OFFLINE_SIMULATION",
        "rounds": rounds, "cases": cases, "formula": evaluate([row["id"] for row in cases], checks, run_id),
        "network_calls": 0, "wallets_created": 0, "transactions_submitted": 0,
        "real_onboarding": "NOT_PERFORMED", "phase_advance_authorized": False,
        "scope": "fixture behavior only; not x402 wire compatibility, chain finality or production safety",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot = out_dir / f"{run_id}.json"
    snapshot.write_text(json.dumps(record, indent=2) + "\n", "utf-8")
    key = load_key(key_path, create=True)
    receipt = sign(file_leaves([snapshot]), key, f"simulation:{run_id}", run_at=record["at"])
    receipt_path = out_dir / f"{run_id}.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", "utf-8")
    persisted = json.loads(receipt_path.read_text("utf-8"))
    problems = verify(persisted, key, check_files=True)
    if problems:
        raise ValueError("simulation receipt verification failed: " + "; ".join(problems))
    record["receipt"] = {"state": "LOCAL_RECEIPT_VERIFIED", "receipt_id": receipt["receipt_id"],
                         "snapshot_path": str(snapshot.resolve()), "receipt_path": str(receipt_path.resolve()),
                         "anchored": False}
    with (out_dir / "report.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    (out_dir / "latest.json").write_text(json.dumps(record, indent=2) + "\n", "utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=2)
    args = parser.parse_args(argv)
    record = run(args.rounds)
    print(f"OFFLINE SIMULATION: {len(record['cases'])} cases / {record['rounds']} rounds")
    for row in record["cases"]:
        print(f"{'PASS' if row['passed'] else 'FAIL'} {row['id']}: {row['observed']['state']}")
    print(f"VESSELL FORMULA: {record['formula']['state']} / {record['receipt']['state']}")
    print("Real onboarding NOT_PERFORMED; zero network calls, wallets or transactions.")
    return 0 if record["formula"]["state"] == "UP" else 1


if __name__ == "__main__":
    raise SystemExit(main())
