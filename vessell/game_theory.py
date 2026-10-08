"""Exact bounded strategic models; computed consequences are not observed motives."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from vessell.validation import validate_record


@dataclass(frozen=True)
class GameTheoryResult:
    status: str
    model: dict[str, Any] | None
    calculations: dict[str, Any]
    limitations: tuple[str, ...]
    grants_authority: bool = False
    validates_motives: bool = False


def _keys(value: Any, required: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("Model fields must be exactly: " + ", ".join(sorted(required)))


def _integer(value: Any, *, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= 1_000_000:
        raise ValueError("Expected bounded integer, not a Boolean, float or inferred coefficient")
    return value


def _fraction(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _matrix(model: dict[str, Any], players: list[str]) -> dict[str, Any]:
    _keys(model, {"actions", "payoffs"})
    actions, payoffs = model["actions"], model["payoffs"]
    if len(players) != 2 or not isinstance(actions, list) or len(actions) != 2:
        raise ValueError("Matrix requires two players and two action lists")
    for choices in actions:
        if (not isinstance(choices, list) or not 1 <= len(choices) <= 8
                or any(not isinstance(x, str) or not x.strip() or len(x) > 100 for x in choices)
                or len(set(choices)) != len(choices)):
            raise ValueError("Each player needs 1-8 unique named actions")
    rows, columns = len(actions[0]), len(actions[1])
    if not isinstance(payoffs, list) or len(payoffs) != rows:
        raise ValueError("Payoff row count does not match actions")
    for row in payoffs:
        if not isinstance(row, list) or len(row) != columns:
            raise ValueError("Payoff column count does not match actions")
        for cell in row:
            if not isinstance(cell, list) or len(cell) != 2:
                raise ValueError("Every outcome requires both player utilities")
            for number in cell:
                _integer(number, minimum=-1_000_000)
    pure = [
        [actions[0][i], actions[1][j]] for i in range(rows) for j in range(columns)
        if all(payoffs[i][j][0] >= payoffs[k][j][0] for k in range(rows))
        and all(payoffs[i][j][1] >= payoffs[i][k][1] for k in range(columns))
    ]
    dominance = []
    for player, count, responses in ((0, rows, columns), (1, columns, rows)):
        for better in range(count):
            for worse in range(count):
                if better == worse:
                    continue
                diffs = [
                    (payoffs[better][r][0] - payoffs[worse][r][0]) if player == 0
                    else (payoffs[r][better][1] - payoffs[r][worse][1])
                    for r in range(responses)
                ]
                if min(diffs) >= 0 and max(diffs) > 0:
                    dominance.append({"player": players[player], "better": actions[player][better],
                                      "worse": actions[player][worse],
                                      "kind": "strict" if min(diffs) > 0 else "weak"})
    sums = {sum(cell) for row in payoffs for cell in row}
    mixed = None
    if rows == columns == 2:
        a, b, c, d = (payoffs[0][0][0], payoffs[0][1][0],
                       payoffs[1][0][0], payoffs[1][1][0])
        e, f, g, h = (payoffs[0][0][1], payoffs[0][1][1],
                       payoffs[1][0][1], payoffs[1][1][1])
        if a - b - c + d and e - f - g + h:
            q = Fraction(d - b, a - b - c + d)
            p = Fraction(h - g, e - f - g + h)
            if 0 < p < 1 and 0 < q < 1:
                probabilities = [p * q, p * (1-q), (1-p) * q, (1-p) * (1-q)]
                utilities = [
                    sum((probabilities[k] * payoffs[k//2][k % 2][i] for k in range(4)), Fraction())
                    for i in range(2)
                ]
                mixed = {"first_action_probabilities": [_fraction(p), _fraction(q)],
                         "expected_utilities": [_fraction(x) for x in utilities]}
    return {"pure_nash": pure, "dominance": dominance, "constant_sum": len(sums) == 1,
            "constant": next(iter(sums)) if len(sums) == 1 else None, "interior_mixed": mixed,
            "mixed_scope": "Nondegenerate interior 2x2 only; boundary/degenerate equilibria not enumerated"}


def _coalition(model: dict[str, Any], players: list[str]) -> dict[str, Any]:
    _keys(model, {"weights", "quota", "veto", "cap"})
    weights = model["weights"]
    if not isinstance(weights, list) or len(weights) != len(players):
        raise ValueError("Weights must match declared players")
    weights = [_integer(x) for x in weights]
    quota, cap = _integer(model["quota"], minimum=1), _integer(model["cap"], minimum=1)
    veto = model["veto"]
    if (not isinstance(veto, list) or any(x not in players for x in veto)
            or len(set(veto)) != len(veto) or quota > sum(weights)):
        raise ValueError("Attainable quota and unique known veto holders required")
    n = len(players)
    veto_mask = sum(1 << players.index(x) for x in veto)
    winning = [
        sum(weights[i] for i in range(n) if mask & (1 << i)) >= quota
        and mask & veto_mask == veto_mask for mask in range(1 << n)
    ]
    swings, pivots = [0] * n, [0] * n
    for i in range(n):
        for mask in range(1 << n):
            if not mask & (1 << i) and not winning[mask] and winning[mask | (1 << i)]:
                swings[i] += 1
                size = mask.bit_count()
                pivots[i] += math.factorial(size) * math.factorial(n-size-1)
    total = sum(swings)
    shares = []
    for i in range(n):
        banzhaf, shapley = Fraction(swings[i], total), Fraction(pivots[i], math.factorial(n))
        shares.append({"player": players[i], "swings": swings[i],
                       "banzhaf_absolute": _fraction(Fraction(swings[i], 1 << (n-1))),
                       "banzhaf_normalized": _fraction(banzhaf),
                       "shapley_shubik": _fraction(shapley),
                       "base_reserve": _fraction(cap * (banzhaf + shapley) / 2)})
    return {"players": shares, "reserve_total": _fraction(Fraction(cap)),
            "invariant": "Fixed weights, quota, roster, veto and cap imply fixed base reserves",
            "payout_scope": "Reserve excludes survival, flooring, critical bonus and payout caps"}


def _savings(model: dict[str, Any]) -> dict[str, Any]:
    _keys(model, {"bank", "available", "earned", "yield_remaining", "award", "reserve", "requested"})
    values = {key: _integer(value) for key, value in model.items() if key != "reserve"}
    bank, available, earned, budget = (values[k] for k in (
        "bank", "available", "earned", "yield_remaining"))
    if bank + available != earned or budget != bank:
        raise ValueError("Savings input must conserve bank + available = earned and yield = bank")
    reserve = model["reserve"]
    if type(reserve) not in (int, float) or not math.isfinite(reserve) or not 0 <= reserve <= 1_000_000:
        raise ValueError("Reserve must be a finite nonnegative bounded number")
    award, requested = values["award"], values["requested"]
    deposit, floor = award // 4, math.floor(Fraction(str(reserve)) / 2)
    harvest = min(requested, budget + deposit, max(0, bank + deposit - floor))
    next_state = {"bank": bank+deposit-harvest, "available": available+award-deposit+harvest,
                  "yield_remaining": budget+deposit-harvest, "earned": earned+award}
    return {"deposit": deposit, "protected_target": floor, "harvested": harvest,
            "next": next_state, "conserved": next_state["bank"]+next_state["available"] == next_state["earned"],
            "reverse_award": next_state["earned"]-earned, "reverse_harvest": bank+deposit-next_state["bank"]}


def _tree(model: dict[str, Any], players: list[str]) -> dict[str, Any]:
    _keys(model, {"root"})
    visited = 0

    def solve(node: Any, depth: int) -> tuple[list[Fraction], list[str]]:
        nonlocal visited
        visited += 1
        if depth > 16 or visited > 512:
            raise ValueError("Decision tree exceeds depth 16 or 512 nodes")
        if isinstance(node, dict) and set(node) == {"payoff"}:
            if not isinstance(node["payoff"], list) or len(node["payoff"]) != len(players):
                raise ValueError("Terminal payoffs must match players")
            return [Fraction(_integer(x, minimum=-1_000_000)) for x in node["payoff"]], []
        _keys(node, {"actor", "choices"})
        if node["actor"] not in players:
            raise ValueError("Unknown tree actor; chance and hidden-information nodes not supported")
        choices = node["choices"]
        if not isinstance(choices, list) or not 1 <= len(choices) <= 8:
            raise ValueError("Tree needs 1-8 choices per nonterminal")
        results = []
        labels = set()
        for choice in choices:
            _keys(choice, {"action", "next"})
            action = choice["action"]
            if not isinstance(action, str) or not action.strip() or action in labels or len(action) > 100:
                raise ValueError("Unique named tree actions required")
            labels.add(action)
            payoff, path = solve(choice["next"], depth+1)
            results.append((payoff, [action, *path]))
        return max(results, key=lambda result: result[0][players.index(node["actor"])])

    payoff, path = solve(model["root"], 0)
    return {"payoff": [_fraction(x) for x in payoff], "path": path, "visited_nodes": visited,
            "tie_break": "first supplied action", "scope": "Finite deterministic perfect-information tree"}


def assess_game_theory(raw: Any, evidence_ids: set[str]) -> GameTheoryResult:
    if raw is None:
        return GameTheoryResult("NOT_SUPPLIED", None, {}, (
            "No strategic model supplied; no incentives, utilities or policies inferred.",))
    try:
        text = json.dumps(raw, allow_nan=False)
    except (ValueError, TypeError, RecursionError) as error:
        raise ValueError("Strategic model must be finite acyclic JSON") from error
    if len(text.encode()) > 32768:
        raise ValueError("Strategic model exceeds 32 KiB")
    validate_record(raw, "game-theory.schema.json")
    unknown = set(raw["evidence_ids"]) - evidence_ids
    if unknown:
        raise ValueError("Strategic model references unknown evidence: " + ", ".join(sorted(unknown)))
    model = copy.deepcopy(raw)
    kind, body, players = model["kind"], model["model"], model["players"]
    if kind == "matrix":
        output = _matrix(body, players)
    elif kind == "coalition":
        output = _coalition(body, players)
    elif kind == "tree":
        output = _tree(body, players)
    else:
        if len(players) != 1:
            raise ValueError("Savings trace requires exactly one ledger owner")
        output = _savings(body)
    return GameTheoryResult("COMPUTED_CONDITIONAL", model, output, (
        *model["limitations"], "Utilities and weights are declared inputs, not measured motives or merit.",
        "Reproducibility and conditional invariants do not establish empirical efficacy or authority.",
        "Backward provenance requires original inputs; rounded results do not have a unique inverse.",
    ))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="JSON case with evidence and game_theory")
    args = parser.parse_args()
    try:
        case = json.loads(args.case.read_text())
        result = assess_game_theory(case.get("game_theory"), {x["source_id"] for x in case["evidence"]})
        print(json.dumps(asdict(result), indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"GAME THEORY FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
