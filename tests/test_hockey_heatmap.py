"""Tests for vessell.hockey_heatmap (synthetic play-by-play in the api-web.nhle.com schema)."""

from __future__ import annotations

import io
import json
import random
from pathlib import Path
from typing import Any, Self

import pytest

from vessell import hockey_heatmap as hh

TEAM_IDS = {"STL": 19, "COL": 21, "DAL": 25, "CHI": 16}


def _play(
    kind: str, owner: int, x: float, y: float, side: str | None = "left", **extra: Any
) -> dict[str, Any]:
    play: dict[str, Any] = {
        "typeDescKey": kind,
        "periodDescriptor": {"number": 1, "periodType": extra.pop("period_type", "REG")},
        "situationCode": extra.pop("situation", "1551"),
        "details": {"xCoord": x, "yCoord": y, "eventOwnerTeamId": owner},
    }
    if side is not None:
        play["homeTeamDefendingSide"] = side
    return play


def _game(
    game_id: int, home: str, away: str, plays: list[dict[str, Any]], date: str = "2026-04-01"
) -> dict[str, Any]:
    return {
        "id": game_id,
        "gameDate": date,
        "homeTeam": {"id": TEAM_IDS[home], "abbrev": home},
        "awayTeam": {"id": TEAM_IDS[away], "abbrev": away},
        "plays": plays,
    }


def _synthetic_game(
    game_id: int, home: str, away: str, seed: int, date: str = "2026-04-01"
) -> dict[str, Any]:
    rng = random.Random(seed)
    plays = []
    for team in (home, away):
        # home defends left => home attacks +x, away attacks -x
        sign = 1 if team == home else -1
        for _ in range(25):
            x = rng.uniform(30, 88)
            y = rng.uniform(-35, 35)
            dist = ((89 - x) ** 2 + y**2) ** 0.5
            kind = "goal" if rng.random() < max(0.01, 0.25 - dist / 250) else "shot-on-goal"
            plays.append(_play(kind, TEAM_IDS[team], sign * x, sign * y))
    return _game(game_id, home, away, plays, date)


def test_parse_normalises_direction_and_filters() -> None:
    plays = [
        _play("shot-on-goal", 19, 80, 5),  # home STL attacks right: kept as-is
        _play("goal", 21, -80, 5),  # away COL attacks left: flipped
        _play("blocked-shot", 19, 70, 0),  # excluded
        _play("faceoff", 19, 0, 0),  # excluded
        _play("goal", 19, 80, 0, period_type="SO"),  # shootout excluded
        _play("goal", 19, 10, 0, situation="0651"),  # empty net (away goalie pulled) excluded
        _play("missed-shot", 19, -70, 3, side=None),  # fallback: x<0 flipped
        _play("shot-on-goal", 99, 80, 0),  # unknown team skipped
    ]
    game = hh.parse_play_by_play(_game(2026020032, "STL", "COL", plays))
    assert [(s.shooter, s.x, s.y, s.goal) for s in game.shots] == [
        ("STL", 80.0, 5.0, False),
        ("COL", 80.0, -5.0, True),
        ("STL", 70.0, -3.0, False),
    ]


def test_right_defending_side_flips_home() -> None:
    game = hh.parse_play_by_play(
        _game(1, "STL", "COL", [_play("shot-on-goal", 19, -75, 4, side="right")])
    )
    assert (game.shots[0].x, game.shots[0].y) == (75.0, -4.0)


@pytest.mark.parametrize(
    "doc",
    [
        [],
        {"id": "x"},
        {"id": 1, "homeTeam": {}, "awayTeam": {}, "plays": []},
        {"id": 1, "homeTeam": {"id": 1, "abbrev": "A"}, "awayTeam": {"id": 2, "abbrev": "B"}},
    ],
)
def test_parse_rejects_malformed(doc: Any) -> None:
    with pytest.raises(TypeError):
        hh.parse_play_by_play(doc)


def test_grid_cells_and_bounds() -> None:
    grid = hh.Grid(10, 10)
    assert grid.cell(89, 0) == (5, 8)
    assert grid.cell(150, 99) == (0, 9)
    assert grid.cell(-20, -99) == (9, 0)
    with pytest.raises(ValueError):
        hh.Grid(1, 10)


def _games() -> list[hh.Game]:
    docs = [
        _synthetic_game(1, "STL", "DAL", 1),
        _synthetic_game(2, "CHI", "STL", 2),
        _synthetic_game(3, "COL", "DAL", 3),
        _synthetic_game(4, "CHI", "COL", 4),
    ]
    return [hh.parse_play_by_play(d) for d in docs]


def test_xg_model_closer_is_more_dangerous() -> None:
    model = hh.fit_xg_model(_games(), hh.Grid())
    assert model.slope < 0
    assert model.prior(10) > model.prior(50)
    assert 0 < model.goals_fitted < model.shots_fitted == 200


def test_projection_totals_and_matchup() -> None:
    games = _games()
    grid = hh.Grid()
    model = hh.fit_xg_model(games, grid)
    stl = hh.project(games, "STL", "COL", grid, model)
    assert stl.games_for == 2 and stl.games_against == 2
    assert 15 < stl.total_attempts < 40
    assert 0 < stl.total_xg < stl.total_attempts
    with pytest.raises(ValueError):
        hh.project(games, "NYR", "COL", grid, model)
    lone = hh.project(games, "STL", "NYR", grid, model)
    assert lone.notes and lone.total_xg > 0


def test_fit_rejects_empty() -> None:
    with pytest.raises(ValueError):
        hh.fit_xg_model([], hh.Grid())


def test_renderers_escape_and_shape() -> None:
    games = _games()
    grid = hh.Grid(8, 6)
    model = hh.fit_xg_model(games, grid)
    maps = [hh.project(games, "STL", "COL", grid, model)]
    page = hh.render_html(maps, grid, "<script>x</script>", ["src<1>"])
    assert "<script>x" not in page and "&lt;script&gt;" in page and "<svg" in page
    assert "src&lt;1&gt;" in page
    rows = hh.render_csv(maps, grid).strip().splitlines()
    assert len(rows) == 1 + 8 * 6
    text = hh.render_text(maps, grid, color=True)
    assert "\x1b[48;2;" in text and "STL attacking vs COL" in text
    data = json.loads(hh.to_json(maps, grid, model))
    assert data["maps"][0]["team"] == "STL" and len(data["maps"][0]["xg"]) == 6


def test_color_scale() -> None:
    assert hh.color_for_share(0) == hh.EMPTY_COLOR
    assert hh.color_for_share(1.0) == hh.SEQUENTIAL_PALETTE[-1]
    assert hh.color_for_share(5.0) == hh.SEQUENTIAL_PALETTE[-1]


def test_cli_with_files_and_observed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for i, (home, away) in enumerate(
        [("STL", "DAL"), ("CHI", "STL"), ("COL", "DAL"), ("CHI", "COL")], 1
    ):
        (tmp_path / f"{i}.json").write_text(
            json.dumps(_synthetic_game(i, home, away, i)), encoding="utf-8"
        )
    played = tmp_path / "played.json"
    played.write_text(
        json.dumps(_synthetic_game(9, "COL", "STL", 9, date="2026-10-03")), encoding="utf-8"
    )
    (tmp_path / "later.json").write_text(
        json.dumps(_synthetic_game(10, "STL", "COL", 10, date="2026-10-05"))
    )
    out = tmp_path / "out" / "map.json"
    rc = hh.main(
        [
            str(tmp_path),
            "--team",
            "stl",
            "--opponent",
            "COL",
            "--date",
            "2026-10-03",
            "--observed",
            str(played),
            "--format",
            "json",
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [m["team"] for m in data["maps"]] == ["STL", "COL", "STL", "COL"]
    assert data["model"]["shots_fitted"] == 200  # played + later games excluded by --date
    assert "observed game 9" in data["maps"][2]["notes"][0]
    assert (
        hh.main([str(tmp_path / "1.json"), "--team", "STL", "--opponent", "DAL", "--no-color"]) == 0
    )
    assert "STL attacking vs DAL" in capsys.readouterr().out


def test_cli_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert hh.main([str(tmp_path / "missing.json"), "--team", "STL", "--opponent", "COL"]) == 1
    assert hh.main(["--team", "STL", "--opponent", "COL", "--fetch"]) == 1
    assert "requires --date" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        hh.main(["--team", "ST1", "--opponent", "COL"])


def test_season_for() -> None:
    assert hh.season_for("2026-10-03") == "20262027"
    assert hh.season_for("2027-03-01") == "20262027"


class _Resp(io.BytesIO):
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def test_fetch_uses_nhl_api_and_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    schedule = {
        "games": [
            {"id": 2025020001, "gameDate": "2026-04-10", "gameType": 2, "gameState": "OFF"},
            {"id": 2025010001, "gameDate": "2025-09-20", "gameType": 1, "gameState": "OFF"},
            {"id": 2026020032, "gameDate": "2026-10-03", "gameType": 2, "gameState": "FUT"},
        ]
    }
    pbp = _synthetic_game(2025020001, "STL", "COL", 5)

    def fake_urlopen(request: Any, timeout: float) -> _Resp:
        url = request.full_url
        calls.append(url)
        return _Resp(json.dumps(pbp if "gamecenter" in url else schedule).encode())

    monkeypatch.setattr(hh.urllib.request, "urlopen", fake_urlopen)
    assert hh.recent_game_ids("STL", "2026-10-03", 5) == [2025020001]
    path = hh.fetch_play_by_play(2025020001, tmp_path)
    hh.fetch_play_by_play(2025020001, tmp_path)  # cached
    assert path.exists() and sum("gamecenter" in c for c in calls) == 1
    assert all(c.startswith(hh.NHL_API_ROOT + "/") for c in calls)
    with pytest.raises(ValueError):
        hh.fetch_play_by_play(123, tmp_path)
    with pytest.raises(ValueError):
        hh._get_json("https://evil.example/v1/x", 1)
