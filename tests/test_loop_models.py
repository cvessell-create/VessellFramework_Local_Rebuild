from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

from vessell import loop_models as lm

FIELDS = (
    "generation,mission,outcome,kills,intel,seconds,hp,stuck,fitness,improved,levelsCompleted,died"
)


def _row(
    g: int, mission: int, outcome: str, kills: int, hp: int, seconds: float
) -> dict[str, object]:
    levels = 1 if outcome == "complete" else 0
    died = outcome == "dead"
    intel, stuck = 500, 1
    fitness = levels * 1000 + kills * 50 + intel / 10 + hp * 2 - seconds - died * 300 - stuck * 5
    return dict(
        zip(
            FIELDS.split(","),
            [
                g,
                mission,
                outcome,
                kills,
                intel,
                seconds,
                hp,
                stuck,
                round(fitness, 2),
                True,
                levels,
                died,
            ],
            strict=True,
        )
    )


@pytest.fixture()
def csv_path(tmp_path: Path) -> Path:
    rows = []
    for g in range(30):
        mission = g % 5
        outcome = "complete" if g % 3 else ("dead" if g % 2 else "timeout")
        hp = 0 if outcome == "dead" else 60 + g
        rows.append(_row(g, mission, outcome, 3 + g % 4, hp, 80.0 + g))
    rows.append(_row(30, 2, "complete", 9, 90, 900.0))  # deliberate outlier
    path = tmp_path / "episodes.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS.split(","))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_outlier_flags_mark_extreme_episode(csv_path: Path) -> None:
    episodes = lm.load_episodes(csv_path)
    flags = lm.outlier_flags(episodes)
    assert flags[-1] == 1
    assert sum(flags) < len(flags) // 2


def test_relational_store_enforces_predicates(csv_path: Path) -> None:
    episodes = lm.load_episodes(csv_path)
    con = lm.build_store(episodes, lm.outlier_flags(episodes))
    summary = lm.relationship_summary(con)
    assert summary["integrity_violations"] == []
    assert summary["many_to_many"]["episode<->attribute"] == len(episodes)
    (loop_id,) = con.execute("SELECT id FROM loop").fetchone()
    with pytest.raises(sqlite3.IntegrityError):  # died -> outcome = dead
        con.execute(
            "INSERT INTO episode(loop_id, generation, mission, outcome, kills, intel, seconds, hp, stuck,"
            " fitness, levels_completed, died) VALUES (?,0,0,'timeout',0,0,1,0,0,0,0,1)",
            (loop_id,),
        )
    con.execute(
        "INSERT INTO model_run(loop_id, log_loss, accuracy) VALUES (?, 0.1, 0.9)", (loop_id,)
    )
    with pytest.raises(sqlite3.IntegrityError):  # one-to-one loop -> model_run
        con.execute(
            "INSERT INTO model_run(loop_id, log_loss, accuracy) VALUES (?, 0.2, 0.8)", (loop_id,)
        )


def test_probability_identities(csv_path: Path) -> None:
    report = lm.probability_report(lm.load_episodes(csv_path))
    assert report["chain_rule_holds"] is True
    assert sum(report["joint_mission_outcome"].values()) == pytest.approx(1.0)
    assert sum(report["total_probability"].values()) == pytest.approx(1.0)
    for posterior in report["bayes_mission_given_outcome"].values():
        assert sum(posterior.values()) == pytest.approx(1.0)


def test_logistic_regression_learns_separable_signal() -> None:
    xs = [[float(i)] for i in range(20)]
    ys = [int(i >= 10) for i in range(20)]
    model = lm.fit_logistic(xs, ys, l2=0.01)
    assert model.weights[0] > 0
    assert model.prob([2.0]) < 0.2
    assert model.prob([17.0]) > 0.8


def test_minimax_and_dominance() -> None:
    mixed = lm.minimax_2x2([[2.0, 8.0], [6.0, 1.0]])
    assert mixed["saddle"] is False
    assert sum(mixed["row_mix"]) == pytest.approx(1.0)
    assert mixed["value"] == pytest.approx(46 / 11, abs=1e-3)
    saddle = lm.minimax_2x2([[3.0, 1.0], [7.0, 2.0]])
    assert saddle == {"saddle": True, "value": 2.0, "row_mix": [0, 1], "col_mix": [0, 1]}
    assert lm.dominant_strategies([[3.0, 1.0], [7.0, 2.0]]) == 1
    assert lm.dominant_strategies([[2.0, 8.0], [6.0, 1.0]]) is None


def test_backward_induction_and_big_m() -> None:
    plan = lm.backward_induction({1: 0.9, 2: 0.6})
    assert plan["mission_3"]["choice"] in {"cautious", "aggressive"}
    assert plan["value_from_mission_2"] > 0
    loadout = lm.big_m_loadout(capacity=10, big_m=6)
    assert loadout["fuel"] <= loadout["big_m"] * loadout["x"]["jetpack"]
    assert lm.big_m_loadout(capacity=4, big_m=6)["fuel"] <= 4


def test_layer_gate_is_sequential(csv_path: Path) -> None:
    layers = lm.layer_gate(lm.load_episodes(csv_path), threshold=0.5)
    assert len(layers) == 5
    states = [layer["state"] for layer in layers]
    assert states == sorted(states, key=lambda s: s != "up")  # no layer up above a down layer


def test_run_writes_report(csv_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "latest.json"
    report = lm.run(csv_path, out)
    assert out.exists()
    assert report["trained_weights"] is False
    assert report["relational"]["one_to_one"]["rows"] == 1
    assert "fortitude_south" in report["deception_games"]
