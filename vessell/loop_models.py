"""Loop models fitted on recorded autopilot episodes.

Pure-Python statistics shared by the game loop, the framework loop and the
repo-to-repo loop: a SQLite relational store with first-order integrity
predicates, probability tables (joint, chain rule, independence, total
probability, Bayes), robust outlier detection, an L2 logistic regression,
backward induction over mission levels, 2x2 zero-sum minimax for deception
games, a Big-M mixed-integer loadout model and a Beta-posterior gate that
spins the five SI layers up or down.

Deception-game payoffs are declared design values in game units, not
historical calibration.  Nothing here trains neural-network weights.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import statistics
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Any

FEATURES = ("mission", "kills", "intel", "hp", "stuck", "outlier")
LAYERS = (
    "L1 chatbot",
    "L2 tactical planner",
    "L3 strategic induction",
    "L4 cross-repo builder",
    "L5 self-revision",
)

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS repo (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS agent (
  id INTEGER PRIMARY KEY, repo_id INTEGER NOT NULL REFERENCES repo(id),
  name TEXT NOT NULL UNIQUE, role TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS loop (
  id INTEGER PRIMARY KEY, agent_id INTEGER NOT NULL REFERENCES agent(id),
  iteration INTEGER NOT NULL CHECK (iteration >= 0),
  UNIQUE (agent_id, iteration));
CREATE TABLE IF NOT EXISTS episode (
  id INTEGER PRIMARY KEY, loop_id INTEGER NOT NULL REFERENCES loop(id),
  generation INTEGER NOT NULL, mission INTEGER NOT NULL CHECK (mission BETWEEN 0 AND 4),
  outcome TEXT NOT NULL CHECK (outcome IN ('complete','dead','timeout','interrupted')),
  kills INTEGER NOT NULL CHECK (kills >= 0), intel INTEGER NOT NULL CHECK (intel >= 0),
  seconds REAL NOT NULL CHECK (seconds >= 0), hp INTEGER NOT NULL,
  stuck INTEGER NOT NULL CHECK (stuck >= 0), fitness REAL NOT NULL,
  levels_completed INTEGER NOT NULL CHECK (levels_completed >= 0),
  died INTEGER NOT NULL CHECK (died IN (0, 1)),
  fitness_calc REAL GENERATED ALWAYS AS (
    levels_completed * 1000 + kills * 50 + intel / 10.0 + hp * 2
    - seconds - died * 300 - stuck * 5) VIRTUAL,
  -- first-order predicates: died -> outcome = dead; complete -> levels >= 1
  CHECK (died = 0 OR outcome = 'dead'),
  CHECK (outcome <> 'complete' OR levels_completed >= 1));
CREATE TABLE IF NOT EXISTS attribute (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, discovered_by INTEGER REFERENCES agent(id));
CREATE TABLE IF NOT EXISTS episode_attribute (
  episode_id INTEGER NOT NULL REFERENCES episode(id),
  attribute_id INTEGER NOT NULL REFERENCES attribute(id),
  value REAL NOT NULL, PRIMARY KEY (episode_id, attribute_id));
CREATE TABLE IF NOT EXISTS message (
  id INTEGER PRIMARY KEY, loop_id INTEGER NOT NULL REFERENCES loop(id),
  sender INTEGER NOT NULL REFERENCES agent(id), receiver INTEGER NOT NULL REFERENCES agent(id),
  body TEXT NOT NULL, CHECK (sender <> receiver));
CREATE TABLE IF NOT EXISTS model_run (
  id INTEGER PRIMARY KEY, loop_id INTEGER NOT NULL UNIQUE REFERENCES loop(id),
  log_loss REAL NOT NULL, accuracy REAL NOT NULL CHECK (accuracy BETWEEN 0 AND 1));
CREATE VIEW IF NOT EXISTS v_episode_features AS
  SELECT e.id, e.mission, e.kills, e.intel, e.hp, e.stuck, e.seconds, e.fitness,
         e.outcome, (e.outcome = 'complete') AS cleared,
         COALESCE((SELECT ea.value FROM episode_attribute ea JOIN attribute a ON a.id = ea.attribute_id
                   WHERE ea.episode_id = e.id AND a.name = 'outlier'), 0) AS outlier
  FROM episode e;
CREATE VIEW IF NOT EXISTS v_integrity_violations AS
  SELECT 'fitness_mismatch' AS rule, id FROM episode WHERE abs(fitness - fitness_calc) > 0.05
  UNION ALL
  SELECT 'orphan_model_run', m.id FROM model_run m LEFT JOIN loop l ON l.id = m.loop_id WHERE l.id IS NULL
  UNION ALL
  SELECT 'cross_repo_message_without_loop', g.id FROM message g
    LEFT JOIN loop l ON l.id = g.loop_id WHERE l.id IS NULL;
"""

AGENTS = (
    ("hail-to-the-analyst", "autopilot", "player"),
    ("hail-to-the-analyst", "build-agent", "game improver"),
    ("VessellFramework_Local_Rebuild", "si-chat", "framework analyst"),
)


@dataclass(frozen=True)
class Episode:
    generation: int
    mission: int
    outcome: str
    kills: int
    intel: int
    seconds: float
    hp: int
    stuck: int
    fitness: float
    levels_completed: int
    died: bool


def load_episodes(path: Path) -> list[Episode]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            Episode(
                generation=int(row["generation"]),
                mission=int(row["mission"]),
                outcome=row["outcome"],
                kills=int(row["kills"]),
                intel=int(row["intel"]),
                seconds=float(row["seconds"]),
                hp=int(row["hp"]),
                stuck=int(row["stuck"]),
                fitness=float(row["fitness"]),
                levels_completed=int(row["levelsCompleted"]),
                died=row["died"].strip().lower() == "true",
            )
            for row in csv.DictReader(handle)
        ]


# --- Outliers ---------------------------------------------------------------


def robust_z(values: list[float]) -> list[float]:
    """Modified z-score (Iglewicz-Hoaglin): 0.6745 * (x - median) / MAD."""
    median = statistics.median(values)
    mad = statistics.median(abs(v - median) for v in values)
    if mad == 0:
        return [0.0 for _ in values]
    return [0.6745 * (v - median) / mad for v in values]


def outlier_flags(episodes: list[Episode], threshold: float = 3.5) -> list[int]:
    fit = robust_z([e.fitness for e in episodes])
    sec = robust_z([e.seconds for e in episodes])
    return [int(abs(a) > threshold or abs(b) > threshold) for a, b in zip(fit, sec, strict=True)]


# --- Relational store ---------------------------------------------------------


def build_store(
    episodes: list[Episode], flags: list[int], db: str = ":memory:"
) -> sqlite3.Connection:
    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    for repo in sorted({a[0] for a in AGENTS}):
        con.execute("INSERT OR IGNORE INTO repo(name) VALUES (?)", (repo,))
    for repo, name, role in AGENTS:
        con.execute(
            "INSERT OR IGNORE INTO agent(repo_id, name, role) SELECT id, ?, ? FROM repo WHERE name = ?",
            (name, role, repo),
        )
    ids = {n: i for i, n in con.execute("SELECT id, name FROM agent")}
    con.execute(
        "INSERT OR IGNORE INTO loop(agent_id, iteration) VALUES (?, 0)", (ids["autopilot"],)
    )
    (loop_id,) = con.execute(
        "SELECT id FROM loop WHERE agent_id = ? AND iteration = 0", (ids["autopilot"],)
    ).fetchone()
    con.execute(
        "INSERT OR IGNORE INTO attribute(name, discovered_by) VALUES ('outlier', ?)",
        (ids["si-chat"],),
    )
    (attr,) = con.execute("SELECT id FROM attribute WHERE name = 'outlier'").fetchone()
    for e, flag in zip(episodes, flags, strict=True):
        cur = con.execute(
            "INSERT INTO episode(loop_id, generation, mission, outcome, kills, intel, seconds, hp, stuck,"
            " fitness, levels_completed, died) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                loop_id,
                e.generation,
                e.mission,
                e.outcome,
                e.kills,
                e.intel,
                e.seconds,
                e.hp,
                e.stuck,
                e.fitness,
                e.levels_completed,
                int(e.died),
            ),
        )
        con.execute("INSERT INTO episode_attribute VALUES (?,?,?)", (cur.lastrowid, attr, flag))
    con.execute(
        "INSERT INTO message(loop_id, sender, receiver, body) VALUES (?,?,?,?)",
        (loop_id, ids["si-chat"], ids["build-agent"], "outlier attribute published"),
    )
    con.commit()
    return con


def relationship_summary(con: sqlite3.Connection) -> dict[str, Any]:
    def q(sql: str) -> int:
        return int(con.execute(sql).fetchone()[0])

    return {
        "one_to_one": {
            "loop->model_run": "model_run.loop_id UNIQUE",
            "rows": q("SELECT count(*) FROM model_run"),
        },
        "many_to_one": {
            "episode->loop": q("SELECT count(*) FROM episode"),
            "message->loop": q("SELECT count(*) FROM message"),
            "agent->repo": q("SELECT count(*) FROM agent"),
        },
        "many_to_many": {"episode<->attribute": q("SELECT count(*) FROM episode_attribute")},
        "integrity_violations": [
            list(r) for r in con.execute("SELECT * FROM v_integrity_violations")
        ],
    }


# --- Probability ------------------------------------------------------------


def _speed(e: Episode, median_seconds: float) -> str:
    return "fast" if e.seconds <= median_seconds else "slow"


def probability_report(episodes: list[Episode]) -> dict[str, Any]:
    n = len(episodes)
    med = statistics.median(e.seconds for e in episodes)
    rows = [(e.mission, e.outcome, _speed(e, med)) for e in episodes]
    missions = sorted({r[0] for r in rows})
    outcomes = sorted({r[1] for r in rows})
    c_mos = Counter(rows)
    c_mo = Counter(r[:2] for r in rows)
    c_m = Counter(r[0] for r in rows)
    c_o = Counter(r[1] for r in rows)

    # chain rule on empirical counts: P(M,O,S) = P(M) P(O|M) P(S|M,O)
    chain_ok = True
    for m, o, s in product(missions, outcomes, ("fast", "slow")):
        if c_mo[(m, o)]:
            joint = Fraction(c_mos[(m, o, s)], n)
            chain = (
                Fraction(c_m[m], n)
                * Fraction(c_mo[(m, o)], c_m[m])
                * Fraction(c_mos[(m, o, s)], c_mo[(m, o)])
            )
            chain_ok = chain_ok and chain == joint
    # independence of mission and outcome: Pearson chi-square
    chi2 = 0.0
    for m, o in product(missions, outcomes):
        expected = c_m[m] * c_o[o] / n
        chi2 += (c_mo[(m, o)] - expected) ** 2 / expected
    dof = (len(missions) - 1) * (len(outcomes) - 1)
    # total probability and Bayes with Laplace smoothing (alpha = 1)
    k = len(outcomes)
    cond = {m: {o: (c_mo[(m, o)] + 1) / (c_m[m] + k) for o in outcomes} for m in missions}
    prior = {m: c_m[m] / n for m in missions}
    total = {o: sum(cond[m][o] * prior[m] for m in missions) for o in outcomes}
    bayes = {o: {m: cond[m][o] * prior[m] / total[o] for m in missions} for o in outcomes}
    return {
        "n": n,
        "median_seconds": med,
        "joint_mission_outcome": {
            f"{m}|{o}": c_mo[(m, o)] / n for m, o in product(missions, outcomes)
        },
        "chain_rule_holds": chain_ok,
        "independence_mission_outcome": {
            "chi2": round(chi2, 4),
            "dof": dof,
            "chi2_crit_0.05": _chi2_crit(dof),
            "independent_at_0.05": chi2 <= _chi2_crit(dof),
        },
        "p_outcome_given_mission": cond,
        "total_probability": total,
        "bayes_mission_given_outcome": bayes,
    }


def _chi2_crit(dof: int) -> float:
    """Wilson-Hilferty approximation of the 95th chi-square percentile."""
    z = 1.6449
    return round(dof * (1 - 2 / (9 * dof) + z * math.sqrt(2 / (9 * dof))) ** 3, 4) if dof else 0.0


# --- Logistic regression --------------------------------------------------------


@dataclass
class Logistic:
    weights: list[float]
    bias: float
    means: list[float]
    scales: list[float]

    def prob(self, x: list[float]) -> float:
        z = self.bias + sum(
            w * (v - m) / s
            for w, v, m, s in zip(self.weights, x, self.means, self.scales, strict=True)
        )
        return 1 / (1 + math.exp(-max(-35.0, min(35.0, z))))


def fit_logistic(
    xs: list[list[float]], ys: list[int], l2: float = 0.1, lr: float = 0.3, epochs: int = 3000
) -> Logistic:
    d = len(xs[0])
    means = [statistics.fmean(r[j] for r in xs) for j in range(d)]
    scales = [statistics.pstdev([r[j] for r in xs]) or 1.0 for j in range(d)]
    z = [[(r[j] - means[j]) / scales[j] for j in range(d)] for r in xs]
    w, b, n = [0.0] * d, 0.0, len(xs)
    for _ in range(epochs):
        gw, gb = [0.0] * d, 0.0
        for row, y in zip(z, ys, strict=True):
            err = (
                1
                / (
                    1
                    + math.exp(
                        -max(-35.0, min(35.0, b + sum(a * c for a, c in zip(w, row, strict=True))))
                    )
                )
                - y
            )
            gb += err
            for j in range(d):
                gw[j] += err * row[j]
        w = [w[j] - lr * (gw[j] / n + l2 * w[j]) for j in range(d)]
        b -= lr * gb / n
    return Logistic(w, b, means, scales)


def logistic_report(episodes: list[Episode], flags: list[int]) -> dict[str, Any]:
    xs = [
        [float(e.mission), float(e.kills), float(e.intel), float(e.hp), float(e.stuck), float(f)]
        for e, f in zip(episodes, flags, strict=True)
    ]
    ys = [int(e.outcome == "complete") for e in episodes]
    model = fit_logistic(xs, ys)
    probs = [model.prob(x) for x in xs]
    eps = 1e-12
    loss = -statistics.fmean(
        y * math.log(p + eps) + (1 - y) * math.log(1 - p + eps)
        for y, p in zip(ys, probs, strict=True)
    )
    acc = statistics.fmean(int((p >= 0.5) == bool(y)) for y, p in zip(ys, probs, strict=True))
    return {
        "target": "outcome == complete",
        "features": list(FEATURES),
        "standardized_coefficients": dict(
            zip(FEATURES, (round(v, 4) for v in model.weights), strict=True)
        ),
        "intercept": round(model.bias, 4),
        "log_loss": round(loss, 4),
        "accuracy": round(acc, 4),
        "note": "Descriptive fit on post-episode features; not a causal or out-of-sample claim.",
    }


# --- Backward induction and dominance --------------------------------------------


def backward_induction(clear_rate: dict[int, float], reward: float = 1000.0) -> dict[str, Any]:
    """Solve missions 3 -> 2 (index 2 -> 1) choosing cautious or aggressive play.

    Design assumption: aggressive play trades 10% clear probability for a
    250-unit time bonus; cautious play keeps the observed clear rate.
    """
    styles = {"cautious": (1.0, 0.0), "aggressive": (0.9, 250.0)}
    value_next = 0.0
    plan: dict[str, Any] = {}
    for mission in (2, 1):
        base = clear_rate.get(mission, 0.5)
        values = {s: base * f * (reward + bonus + value_next) for s, (f, bonus) in styles.items()}
        best = max(values, key=lambda s: values[s])
        plan[f"mission_{mission + 1}"] = {
            "values": {k: round(v, 2) for k, v in values.items()},
            "choice": best,
        }
        value_next = values[best]
    choices = {v["choice"] for v in plan.values()}
    plan["dominant_strategy"] = choices.pop() if len(choices) == 1 else None
    plan["value_from_mission_2"] = round(value_next, 2)
    return plan


def dominant_strategies(matrix: list[list[float]]) -> int | None:
    """Row index that weakly dominates every other row (row player maximises)."""
    for i, row in enumerate(matrix):
        if all(
            all(a >= b for a, b in zip(row, other, strict=True))
            for j, other in enumerate(matrix)
            if j != i
        ):
            return i
    return None


# --- Minimax deception games -------------------------------------------------------


def minimax_2x2(matrix: list[list[float]]) -> dict[str, Any]:
    """Zero-sum 2x2: row maximises, column minimises."""
    (a, b), (c, d) = matrix
    lower = max(min(a, b), min(c, d))
    upper = min(max(a, c), max(b, d))
    if lower == upper:
        row = 0 if min(a, b) == lower else 1
        col = 0 if max(a, c) == upper else 1
        return {
            "saddle": True,
            "value": lower,
            "row_mix": [1 - row, row],
            "col_mix": [1 - col, col],
        }
    denom = a - b - c + d
    p = (d - c) / denom
    q = (d - b) / denom
    return {
        "saddle": False,
        "value": round((a * d - b * c) / denom, 4),
        "row_mix": [round(p, 4), round(1 - p, 4)],
        "col_mix": [round(q, 4), round(1 - q, 4)],
    }


DECEPTION_GAMES: dict[str, dict[str, Any]] = {
    "fortitude_south": {
        "actors": ["deceiver", "defender"],
        "rows": ["land at Normandy", "land at Calais"],
        "cols": ["reinforce Normandy", "reinforce Calais"],
        "payoff": [[2.0, 8.0], [6.0, 1.0]],
    },
    "norway_feint": {
        "actors": ["deceiver", "defender"],
        "rows": ["threaten Norway", "commit main front"],
        "cols": ["garrison Norway", "release reserves"],
        "payoff": [[3.0, 1.0], [7.0, 2.0]],
    },
    "maskirovka_air": {
        "actors": ["jet squadron", "air defense"],
        "rows": ["decoy emitters", "direct strike"],
        "cols": ["engage decoys", "hold fire"],
        "payoff": [[6.0, 2.0], [3.0, 5.0]],
    },
}


def deception_report() -> dict[str, Any]:
    out = {}
    for name, game in DECEPTION_GAMES.items():
        result = minimax_2x2(game["payoff"])
        dom = dominant_strategies(game["payoff"])
        out[name] = dict(
            game,
            solution=result,
            dominant_row=None if dom is None else game["rows"][dom],
            evidence="design values in game units; not historical calibration",
        )
    return out


# --- Big-M loadout ---------------------------------------------------------------


def big_m_loadout(capacity: int = 10, big_m: int = 6) -> dict[str, Any]:
    """max sum v_i x_i + 40 f  s.t.  sum w_i x_i + f <= C,  f <= M * x_jet,  x binary, f integer >= 0."""
    items = {"jetpack": (60, 3), "shotgun": (80, 4), "armor": (70, 4), "scanner": (50, 2)}
    names = list(items)
    best: tuple[float, dict[str, int], int] = (-1.0, {}, 0)
    for xs in product((0, 1), repeat=len(names)):
        chosen = dict(zip(names, xs, strict=True))
        used = sum(items[n][1] * x for n, x in chosen.items())
        for fuel in range(big_m + 1):
            if fuel > big_m * chosen["jetpack"] or used + fuel > capacity:
                continue
            value = float(sum(items[n][0] * x for n, x in chosen.items()) + 40 * fuel)
            if value > best[0]:
                best = (value, chosen, fuel)
    value, chosen, fuel = best
    return {
        "objective": value,
        "x": chosen,
        "fuel": fuel,
        "big_m": big_m,
        "big_m_binding": fuel == big_m * chosen.get("jetpack", 0),
        "capacity": capacity,
    }


# --- Five-layer Bayes gate ---------------------------------------------------------


def layer_gate(
    episodes: list[Episode], threshold: float = 0.6, prior: tuple[float, float] = (1.0, 1.0)
) -> list[dict[str, Any]]:
    """Beta-Binomial posterior per layer; layer k is evidenced by mission index k-1 clears."""
    out, upstream = [], True
    for k, name in enumerate(LAYERS):
        trials = [e for e in episodes if e.mission == k]
        wins = sum(1 for e in trials if e.outcome == "complete")
        a, b = prior[0] + wins, prior[1] + len(trials) - wins
        mean = a / (a + b)
        sd = math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1)))
        up = upstream and mean >= threshold
        out.append(
            {
                "layer": name,
                "trials": len(trials),
                "clears": wins,
                "posterior_mean": round(mean, 4),
                "posterior_sd": round(sd, 4),
                "state": "up" if up else "down",
            }
        )
        upstream = up
    return out


def run(csv_path: Path, out_path: Path | None = None) -> dict[str, Any]:
    episodes = load_episodes(csv_path)
    flags = outlier_flags(episodes)
    con = build_store(episodes, flags)
    logistic = logistic_report(episodes, flags)
    (loop_id,) = con.execute("SELECT id FROM loop LIMIT 1").fetchone()
    con.execute(
        "INSERT INTO model_run(loop_id, log_loss, accuracy) VALUES (?,?,?)",
        (loop_id, logistic["log_loss"], logistic["accuracy"]),
    )
    probs = probability_report(episodes)
    clear_rate = {
        int(m): v.get("complete", 0.0) for m, v in probs["p_outcome_given_mission"].items()
    }
    report = {
        "source": str(csv_path),
        "outliers": {
            "count": sum(flags),
            "generations": [e.generation for e, f in zip(episodes, flags, strict=True) if f],
        },
        "relational": relationship_summary(con),
        "probability": probs,
        "logistic": logistic,
        "backward_induction": backward_induction(clear_rate),
        "deception_games": deception_report(),
        "big_m": big_m_loadout(),
        "layers": layer_gate(episodes),
        "trained_weights": False,
    }
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/loop_models/latest.json"))
    args = parser.parse_args(argv)
    report = run(args.csv, args.out)
    print(json.dumps({k: report[k] for k in ("outliers", "logistic", "layers")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
