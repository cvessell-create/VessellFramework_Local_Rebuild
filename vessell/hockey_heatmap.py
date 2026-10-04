# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Hockey scoring-chance heat map: projected expected goals by rink zone.

Builds a projected scoring-chance heat map for one team against one
opponent from **public NHL play-by-play** (``api-web.nhle.com``, the feed
behind NHL.com Gamecenter). Nothing is invented: every number traces back
to shot events in the play-by-play files you supply or fetch.

Pipeline
--------
1. **Ingest** unblocked shot attempts (goals, shots on goal, missed shots —
   "Fenwick"). Blocked shots are excluded because the feed records them at
   the block location under the blocking team. Shootouts and empty-net
   attempts are excluded.
2. **Normalise** coordinates so every attempt attacks the net at
   ``(89, 0)`` using ``homeTeamDefendingSide`` (fallback: sign of ``x``).
3. **Shot-quality prior**: a ridge-regularised logistic regression of goal
   on distance-to-net, fitted on every attempt in the sample (the same
   distance-based xG idea used by public models such as MoneyPuck,
   Evolving-Hockey and Natural Stat Trick).
4. **Zone conversion**: per grid cell, empirical-Bayes shrinkage of the
   observed goal rate toward that prior, so sparse cells do not swing.
5. **Matchup projection** (log5 / odds-ratio style): attempts per game a
   team generates in each cell, times the attempts per game the opponent
   concedes there, divided by the sample-wide average — then multiplied by
   the cell conversion rate to give projected xG per cell.

This is a statistical projection from historical shot locations, not a
prediction of what will happen. Lineups, goaltenders, injuries and score
effects are not modelled.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import math
import re
import sys
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NHL_API_ROOT = "https://api-web.nhle.com/v1"
USER_AGENT = "VesselFramework-HockeyHeatmap/1.0"
MAX_RESPONSE_BYTES = 20 * 1024 * 1024

NET_X = 89.0
BLUE_LINE_X = 25.0
BOARDS_X = 100.0
HALF_WIDTH = 42.5

FENWICK_EVENTS = frozenset({"goal", "shot-on-goal", "missed-shot"})

# ColorBrewer YlOrRd 9-class (sequential, colour-blind safe; Cynthia Brewer, Apache-2.0).
SEQUENTIAL_PALETTE: tuple[str, ...] = (
    "#ffffcc",
    "#ffeda0",
    "#fed976",
    "#feb24c",
    "#fd8d3c",
    "#fc4e2a",
    "#e31a1c",
    "#bd0026",
    "#800026",
)
EMPTY_COLOR = "#f4f4f4"

_TEAM_RE = re.compile(r"^[A-Z]{2,3}$")
_GAME_ID_RE = re.compile(r"^\d{10}$")
_SEASON_RE = re.compile(r"^\d{8}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Shot:
    """One unblocked shot attempt, normalised to attack the net at (+89, 0)."""

    game_id: int
    shooter: str
    defender: str
    x: float
    y: float
    goal: bool

    @property
    def distance(self) -> float:
        return math.hypot(NET_X - self.x, self.y)


@dataclass(frozen=True)
class Game:
    game_id: int
    game_date: str
    home: str
    away: str
    shots: tuple[Shot, ...]

    @property
    def teams(self) -> tuple[str, str]:
        return self.home, self.away


@dataclass(frozen=True)
class Grid:
    """Offensive half-rink grid (x from centre ice to the end boards)."""

    cols: int = 10
    rows: int = 10

    def __post_init__(self) -> None:
        if not (2 <= self.cols <= 50 and 2 <= self.rows <= 50):
            raise ValueError("grid cols/rows must be between 2 and 50")

    @property
    def cell_w(self) -> float:
        return BOARDS_X / self.cols

    @property
    def cell_h(self) -> float:
        return 2 * HALF_WIDTH / self.rows

    def cell(self, x: float, y: float) -> tuple[int, int]:
        col = int(min(max(x, 0.0), BOARDS_X - 1e-9) // self.cell_w)
        row = int(min(max(HALF_WIDTH - y, 0.0), 2 * HALF_WIDTH - 1e-9) // self.cell_h)
        return row, col

    def center(self, row: int, col: int) -> tuple[float, float]:
        return (col + 0.5) * self.cell_w, HALF_WIDTH - (row + 0.5) * self.cell_h


@dataclass
class XGModel:
    """Distance logistic prior + empirical-Bayes per-cell conversion."""

    intercept: float
    slope: float
    mean_distance: float
    sd_distance: float
    cell_rate: list[list[float]]
    shots_fitted: int
    goals_fitted: int

    def prior(self, distance: float) -> float:
        z = (distance - self.mean_distance) / self.sd_distance
        return _sigmoid(self.intercept + self.slope * z)


@dataclass
class TeamMap:
    team: str
    opponent: str
    attempts: list[list[float]]
    xg: list[list[float]]
    games_for: int
    games_against: int
    notes: list[str] = field(default_factory=list)

    @property
    def total_attempts(self) -> float:
        return sum(sum(r) for r in self.attempts)

    @property
    def total_xg(self) -> float:
        return sum(sum(r) for r in self.xg)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _team_abbrev(side: Any, label: str) -> tuple[int, str]:
    if not isinstance(side, dict):
        raise TypeError(f"play-by-play {label} must be an object")
    team_id, abbrev = side.get("id"), side.get("abbrev")
    if isinstance(abbrev, dict):  # some feeds use {"default": "STL"}
        abbrev = abbrev.get("default")
    if not isinstance(team_id, int) or not isinstance(abbrev, str):
        raise TypeError(f"play-by-play {label} needs integer id and string abbrev")
    return team_id, abbrev.upper()


def _empty_net(situation: Any, defender_is_home: bool) -> bool:
    """``situationCode`` = away goalie, away skaters, home skaters, home goalie."""
    if not isinstance(situation, str) or len(situation) != 4 or not situation.isdigit():
        return False
    return situation[3 if defender_is_home else 0] == "0"


def parse_play_by_play(data: Any) -> Game:
    """Parse an ``api-web.nhle.com/v1/gamecenter/{id}/play-by-play`` document."""
    if not isinstance(data, dict):
        raise TypeError("play-by-play document must be a JSON object")
    game_id = data.get("id")
    if not isinstance(game_id, int):
        raise TypeError("play-by-play is missing integer 'id'")
    home_id, home = _team_abbrev(data.get("homeTeam"), "homeTeam")
    away_id, away = _team_abbrev(data.get("awayTeam"), "awayTeam")
    plays = data.get("plays")
    if not isinstance(plays, list):
        raise TypeError("play-by-play is missing 'plays' list")

    shots: list[Shot] = []
    for play in plays:
        if not isinstance(play, dict) or play.get("typeDescKey") not in FENWICK_EVENTS:
            continue
        period = play.get("periodDescriptor")
        if isinstance(period, dict) and period.get("periodType") == "SO":
            continue
        details = play.get("details")
        if not isinstance(details, dict):
            continue
        x, y, owner = details.get("xCoord"), details.get("yCoord"), details.get("eventOwnerTeamId")
        if isinstance(x, bool) or isinstance(y, bool):
            continue
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue
        if owner == home_id:
            shooter, defender, shooter_home = home, away, True
        elif owner == away_id:
            shooter, defender, shooter_home = away, home, False
        else:
            continue
        if _empty_net(play.get("situationCode"), defender_is_home=not shooter_home):
            continue
        side = play.get("homeTeamDefendingSide")
        if side in ("left", "right"):
            attacks_right = (side == "left") == shooter_home
        else:
            attacks_right = float(x) >= 0
        fx, fy = (float(x), float(y)) if attacks_right else (-float(x), -float(y))
        shots.append(
            Shot(
                game_id=game_id,
                shooter=shooter,
                defender=defender,
                x=fx,
                y=fy,
                goal=play.get("typeDescKey") == "goal",
            )
        )
    game_date = data.get("gameDate")
    return Game(
        game_id=game_id,
        game_date=game_date if isinstance(game_date, str) else "",
        home=home,
        away=away,
        shots=tuple(shots),
    )


def load_games(paths: Iterable[Path]) -> list[Game]:
    """Load play-by-play JSON files (directories are scanned for ``*.json``)."""
    games: dict[int, Game] = {}
    for path in paths:
        files = sorted(path.glob("*.json")) if path.is_dir() else [path]
        for file in files:
            with file.open("r", encoding="utf-8") as handle:
                game = parse_play_by_play(json.load(handle))
            games[game.game_id] = game
    return [games[k] for k in sorted(games)]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _fit_logistic(z: Sequence[float], labels: Sequence[int], ridge: float) -> tuple[float, float]:
    """Two-parameter ridge logistic regression via Newton-Raphson."""
    a = b = 0.0
    for _ in range(50):
        ga = gb = 0.0
        haa = hab = hbb = ridge
        ga -= ridge * a
        gb -= ridge * b
        for zi, yi in zip(z, labels, strict=True):
            p = _sigmoid(a + b * zi)
            w = p * (1 - p)
            ga += yi - p
            gb += (yi - p) * zi
            haa += w
            hab += w * zi
            hbb += w * zi * zi
        det = haa * hbb - hab * hab
        if det <= 1e-12:
            break
        da = (hbb * ga - hab * gb) / det
        db = (haa * gb - hab * ga) / det
        a, b = a + da, b + db
        if abs(da) < 1e-9 and abs(db) < 1e-9:
            break
    return a, b


def fit_xg_model(games: Sequence[Game], grid: Grid, prior_strength: float = 25.0) -> XGModel:
    shots = [s for g in games for s in g.shots]
    if not shots:
        raise ValueError("no unblocked shot attempts in the supplied play-by-play")
    dists = [s.distance for s in shots]
    mean = sum(dists) / len(dists)
    sd = math.sqrt(sum((d - mean) ** 2 for d in dists) / len(dists)) or 1.0
    labels = [1 if s.goal else 0 for s in shots]
    a, b = _fit_logistic([(d - mean) / sd for d in dists], labels, ridge=1.0)

    goals = [[0] * grid.cols for _ in range(grid.rows)]
    counts = [[0] * grid.cols for _ in range(grid.rows)]
    for s in shots:
        r, c = grid.cell(s.x, s.y)
        counts[r][c] += 1
        goals[r][c] += int(s.goal)
    model = XGModel(a, b, mean, sd, [], len(shots), sum(labels))
    for r in range(grid.rows):
        row: list[float] = []
        for c in range(grid.cols):
            cx, cy = grid.center(r, c)
            p0 = model.prior(math.hypot(NET_X - cx, cy))
            row.append((goals[r][c] + prior_strength * p0) / (counts[r][c] + prior_strength))
        model.cell_rate.append(row)
    return model


def _per_game(
    games: Sequence[Game], grid: Grid, team: str, *, for_team: bool
) -> tuple[list[list[float]], int]:
    counts = [[0.0] * grid.cols for _ in range(grid.rows)]
    n = 0
    for g in games:
        if team not in g.teams:
            continue
        n += 1
        for s in g.shots:
            if (s.shooter if for_team else s.defender) == team:
                r, c = grid.cell(s.x, s.y)
                counts[r][c] += 1
    return counts, n


def project(
    games: Sequence[Game],
    team: str,
    opponent: str,
    grid: Grid | None = None,
    model: XGModel | None = None,
    smoothing_games: float = 2.0,
) -> TeamMap:
    """Project ``team``'s attempts and xG per cell against ``opponent``."""
    grid = grid or Grid()
    model = model or fit_xg_model(games, grid)
    t_for, g_for = _per_game(games, grid, team, for_team=True)
    o_against, g_against = _per_game(games, grid, opponent, for_team=False)
    notes: list[str] = []
    if g_for == 0:
        raise ValueError(f"no games involving {team} in the supplied play-by-play")
    if g_against == 0:
        notes.append(f"no games involving {opponent}: projection uses {team}'s own rates only")

    league = [[0.0] * grid.cols for _ in range(grid.rows)]
    for g in games:
        for s in g.shots:
            r, c = grid.cell(s.x, s.y)
            league[r][c] += 1
    team_games = 2 * len(games)

    attempts = [[0.0] * grid.cols for _ in range(grid.rows)]
    xg = [[0.0] * grid.cols for _ in range(grid.rows)]
    for r in range(grid.rows):
        for c in range(grid.cols):
            lg = league[r][c] / team_games
            tf = (t_for[r][c] + smoothing_games * lg) / (g_for + smoothing_games)
            if g_against and lg > 0:
                oa = (o_against[r][c] + smoothing_games * lg) / (g_against + smoothing_games)
                value = tf * oa / lg
            else:
                value = tf
            attempts[r][c] = value
            xg[r][c] = value * model.cell_rate[r][c]
    return TeamMap(team, opponent, attempts, xg, g_for, g_against, notes)


def observed(game: Game, team: str, grid: Grid, model: XGModel) -> TeamMap:
    """Actual attempts/xG by ``team`` in one played game, on the same grid."""
    if team not in game.teams:
        raise ValueError(f"{team} did not play in game {game.game_id}")
    opponent = game.away if team == game.home else game.home
    attempts = [[0.0] * grid.cols for _ in range(grid.rows)]
    for s in game.shots:
        if s.shooter == team:
            r, c = grid.cell(s.x, s.y)
            attempts[r][c] += 1
    xg = [
        [attempts[r][c] * model.cell_rate[r][c] for c in range(grid.cols)] for r in range(grid.rows)
    ]
    goals = sum(1 for s in game.shots if s.shooter == team and s.goal)
    return TeamMap(
        team, opponent, attempts, xg, 1, 1, [f"observed game {game.game_id}: {goals} goal(s)"]
    )


# ---------------------------------------------------------------------------
# Fetching (public NHL API)
# ---------------------------------------------------------------------------


def _get_json(url: str, timeout: float) -> Any:
    if not url.startswith(NHL_API_ROOT + "/"):
        raise ValueError(f"refusing to fetch non-NHL URL: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError(f"response from {url} exceeds {MAX_RESPONSE_BYTES} bytes")
    return json.loads(payload.decode("utf-8"))


def season_for(date: str) -> str:
    """NHL season id (e.g. ``20262027``) containing ``YYYY-MM-DD``."""
    year, month = int(date[:4]), int(date[5:7])
    start = year if month >= 7 else year - 1
    return f"{start}{start + 1}"


def recent_game_ids(team: str, before: str, limit: int, timeout: float = 20.0) -> list[int]:
    """Completed regular-season games for ``team`` strictly before ``before``."""
    current = season_for(before)
    previous = f"{int(current[:4]) - 1}{int(current[:4])}"
    found: dict[int, str] = {}
    for season in (previous, current):
        data = _get_json(f"{NHL_API_ROOT}/club-schedule-season/{team}/{season}", timeout)
        games = data.get("games") if isinstance(data, dict) else None
        for g in games if isinstance(games, list) else []:
            if not isinstance(g, dict):
                continue
            gid, gdate = g.get("id"), g.get("gameDate")
            if (
                isinstance(gid, int)
                and isinstance(gdate, str)
                and g.get("gameType") == 2
                and g.get("gameState") in ("OFF", "FINAL")
                and gdate < before
            ):
                found[gid] = gdate
    ordered = sorted(found, key=lambda gid: (found[gid], gid))
    return ordered[-limit:]


def fetch_play_by_play(game_id: int, cache_dir: Path, timeout: float = 20.0) -> Path:
    if not _GAME_ID_RE.match(str(game_id)):
        raise ValueError(f"invalid NHL game id: {game_id}")
    target = cache_dir / f"{game_id}.json"
    if not target.exists():
        data = _get_json(f"{NHL_API_ROOT}/gamecenter/{game_id}/play-by-play", timeout)
        parse_play_by_play(data)  # validate before caching
        cache_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data), encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _text_color(background: str) -> str:
    r, g, b = _hex_to_rgb(background)
    # WCAG relative-luminance approximation; dark text on light cells.
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#111111" if luminance > 140 else "#ffffff"


def _ansi_bg(hex_color: str) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return f"\x1b[48;2;{r};{g};{b}m"


def color_for_share(share: float) -> str:
    """Map ``0..1`` onto the sequential palette (0 → empty)."""
    if share <= 0:
        return EMPTY_COLOR
    position = min(share, 1.0) * (len(SEQUENTIAL_PALETTE) - 1)
    lower = int(position)
    if lower >= len(SEQUENTIAL_PALETTE) - 1:
        return SEQUENTIAL_PALETTE[-1]
    frac = position - lower
    lo, hi = _hex_to_rgb(SEQUENTIAL_PALETTE[lower]), _hex_to_rgb(SEQUENTIAL_PALETTE[lower + 1])
    return _rgb_to_hex(
        (
            round(lo[0] + (hi[0] - lo[0]) * frac),
            round(lo[1] + (hi[1] - lo[1]) * frac),
            round(lo[2] + (hi[2] - lo[2]) * frac),
        )
    )


def _scale(maps: Sequence[TeamMap]) -> float:
    return max((v for m in maps for row in m.xg for v in row), default=0.0) or 1.0


def _svg(team_map: TeamMap, grid: Grid, vmax: float, px: float = 6.0) -> str:
    w, h = BOARDS_X * px, 2 * HALF_WIDTH * px
    out = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
            f'viewBox="0 0 {w:.0f} {h:.0f}" role="img" '
            f'aria-label="{html.escape(team_map.team)} projected xG by zone">'
        )
    ]
    for r in range(grid.rows):
        for c in range(grid.cols):
            value = team_map.xg[r][c]
            fill = color_for_share(value / vmax)
            out.append(
                f'<rect x="{c * grid.cell_w * px:.1f}" y="{r * grid.cell_h * px:.1f}" '
                f'width="{grid.cell_w * px:.1f}" height="{grid.cell_h * px:.1f}" fill="{fill}">'
                f"<title>xG {value:.3f} | attempts {team_map.attempts[r][c]:.2f}</title></rect>"
            )
            if value / vmax >= 0.15:
                out.append(
                    f'<text x="{(c + 0.5) * grid.cell_w * px:.1f}" y="{(r + 0.5) * grid.cell_h * px + 4:.1f}" '
                    f'font-size="11" text-anchor="middle" fill="{_text_color(fill)}">{value:.2f}</text>'
                )
    blue, goal = BLUE_LINE_X * px, NET_X * px
    mid = HALF_WIDTH * px
    out += [
        f'<line x1="{blue}" y1="0" x2="{blue}" y2="{h}" stroke="#1f4e9c" stroke-width="4" opacity="0.7"/>',
        f'<line x1="{goal}" y1="0" x2="{goal}" y2="{h}" stroke="#c00" stroke-width="2" opacity="0.7"/>',
        (
            f'<path d="M {goal} {mid - 6 * px} A {6 * px} {6 * px} 0 0 0 {goal} {mid + 6 * px}" '
            'fill="#7fb2e5" fill-opacity="0.35" stroke="#c00" stroke-width="1.5"/>'
        ),
        (
            f'<rect x="{goal}" y="{mid - 3 * px}" width="{3.3 * px}" height="{6 * px}" fill="none" '
            'stroke="#333" stroke-width="2"/>'
        ),
        f'<rect x="0" y="0" width="{w}" height="{h}" rx="{28 * px}" fill="none" stroke="#333" stroke-width="3"/>',
        "</svg>",
    ]
    return "".join(out)


def render_html(maps: Sequence[TeamMap], grid: Grid, title: str, sources: Sequence[str]) -> str:
    vmax = _scale(maps)
    esc = html.escape
    out = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        f"<title>{esc(title)}</title>",
        (
            "<style>body{font-family:system-ui,sans-serif;margin:24px;color:#222}"
            "h2{margin-bottom:4px}.meta{color:#555;font-size:13px}"
            ".legend span{display:inline-block;width:28px;height:12px}</style></head><body>"
        ),
        f"<h1>{esc(title)}</h1>",
    ]
    for m in maps:
        out.append(f"<h2>{esc(m.team)} attacking vs {esc(m.opponent)}</h2>")
        out.append(
            f"<p class='meta'>Projected unblocked attempts {m.total_attempts:.1f} | projected xG "
            f"{m.total_xg:.2f} | sample: {m.games_for} {esc(m.team)} games, {m.games_against} "
            f"{esc(m.opponent)} games. Net is on the right; blue line marked.</p>"
        )
        for note in m.notes:
            out.append(f"<p class='meta'>Note: {esc(note)}</p>")
        out.append(_svg(m, grid, vmax))
    legend = "".join(f"<span style='background:{c}'></span>" for c in SEQUENTIAL_PALETTE)
    out.append(f"<p class='legend'>low {legend} high (max cell xG {vmax:.3f})</p>")
    out.append(
        "<p class='meta'>Method: Fenwick attempts from public NHL play-by-play; distance logistic "
        "xG prior with empirical-Bayes zone conversion; log5 matchup of team-for vs opponent-against "
        "rates. Statistical projection only — lineups, goaltending and score effects are not modelled.</p>"
    )
    if sources:
        out.append("<p class='meta'>Sources: " + ", ".join(esc(s) for s in sources) + "</p>")
    out.append("</body></html>")
    return "\n".join(out) + "\n"


def render_text(maps: Sequence[TeamMap], grid: Grid, *, color: bool) -> str:
    vmax = _scale(maps)
    blue_col = max(1, round(BLUE_LINE_X / grid.cell_w))
    lines: list[str] = []
    for m in maps:
        lines.append(
            f"{m.team} attacking vs {m.opponent}: projected xG {m.total_xg:.2f}, "
            f"attempts {m.total_attempts:.1f}  (net →, '|' = blue line)"
        )
        for r in range(grid.rows):
            cells: list[str] = []
            for c in range(grid.cols):
                value = m.xg[r][c]
                label = f"{value:5.2f}"
                if color:
                    fill = color_for_share(value / vmax)
                    fg = "\x1b[30m" if _text_color(fill) == "#111111" else "\x1b[97m"
                    label = f"{_ansi_bg(fill)}{fg}{label}\x1b[0m"
                sep = "|" if c + 1 == blue_col else " "
                cells.append(label + sep)
            lines.append("".join(cells))
        lines.extend(f"  note: {n}" for n in m.notes)
        lines.append("")
    return "\n".join(lines)


def render_csv(maps: Sequence[TeamMap], grid: Grid) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["team", "opponent", "row", "col", "x_center", "y_center", "attempts", "xg"])
    for m in maps:
        for r in range(grid.rows):
            for c in range(grid.cols):
                cx, cy = grid.center(r, c)
                writer.writerow(
                    [
                        m.team,
                        m.opponent,
                        r,
                        c,
                        f"{cx:.1f}",
                        f"{cy:.1f}",
                        f"{m.attempts[r][c]:.4f}",
                        f"{m.xg[r][c]:.4f}",
                    ]
                )
    return buf.getvalue()


def to_json(maps: Sequence[TeamMap], grid: Grid, model: XGModel) -> str:
    return (
        json.dumps(
            {
                "grid": {
                    "cols": grid.cols,
                    "rows": grid.rows,
                    "cell_w_ft": grid.cell_w,
                    "cell_h_ft": grid.cell_h,
                },
                "model": {
                    "shots_fitted": model.shots_fitted,
                    "goals_fitted": model.goals_fitted,
                    "intercept": model.intercept,
                    "slope_per_sd_distance": model.slope,
                    "mean_distance_ft": model.mean_distance,
                    "sd_distance_ft": model.sd_distance,
                },
                "maps": [
                    {
                        "team": m.team,
                        "opponent": m.opponent,
                        "games_for": m.games_for,
                        "games_against": m.games_against,
                        "total_attempts": round(m.total_attempts, 4),
                        "total_xg": round(m.total_xg, 4),
                        "attempts": [[round(v, 4) for v in row] for row in m.attempts],
                        "xg": [[round(v, 4) for v in row] for row in m.xg],
                        "notes": m.notes,
                    }
                    for m in maps
                ],
            },
            indent=2,
        )
        + "\n"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _team(value: str) -> str:
    upper = value.upper()
    if not _TEAM_RE.match(upper):
        raise argparse.ArgumentTypeError("team must be a 2-3 letter NHL abbreviation, e.g. STL")
    return upper


def _date(value: str) -> str:
    if not _DATE_RE.match(value):
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vf-hockey-heatmap",
        description="Projected scoring-chance (xG) heat map by rink zone from public NHL play-by-play.",
    )
    parser.add_argument("pbp", nargs="*", type=Path, help="Play-by-play JSON files or directories.")
    parser.add_argument("--team", type=_team, required=True, help="Team to project, e.g. STL.")
    parser.add_argument("--opponent", type=_team, required=True, help="Opponent, e.g. COL.")
    parser.add_argument(
        "--date", type=_date, help="Game date YYYY-MM-DD (only earlier games are used)."
    )
    parser.add_argument(
        "--fetch", action="store_true", help="Download recent games from api-web.nhle.com."
    )
    parser.add_argument(
        "--games", type=int, default=20, help="Recent games per team to fetch (default 20)."
    )
    parser.add_argument("--cache-dir", type=Path, default=Path("outputs/hockey/pbp"))
    parser.add_argument(
        "--observed", help="Game id or play-by-play file of the played game to overlay."
    )
    parser.add_argument("--cols", type=int, default=10)
    parser.add_argument("--rows", type=int, default=10)
    parser.add_argument("--format", choices=("html", "text", "csv", "json"), default="text")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args(argv)

    sources: list[str] = []
    try:
        grid = Grid(args.cols, args.rows)
        paths: list[Path] = list(args.pbp)
        if args.fetch:
            if not args.date:
                raise ValueError("--fetch requires --date")
            if not 1 <= args.games <= 82:
                raise ValueError("--games must be between 1 and 82")
            ids: set[int] = set()
            for team in (args.team, args.opponent):
                ids.update(recent_game_ids(team, args.date, args.games))
            paths += [fetch_play_by_play(gid, args.cache_dir) for gid in sorted(ids)]
            sources.append(f"{NHL_API_ROOT}/gamecenter/{{id}}/play-by-play ({len(ids)} games)")
        games = load_games(paths)
        if args.date:
            games = [g for g in games if not g.game_date or g.game_date < args.date]
        model = fit_xg_model(games, grid)
        maps = [
            project(games, args.team, args.opponent, grid, model),
            project(games, args.opponent, args.team, grid, model),
        ]
        if args.observed:
            obs_path = Path(args.observed)
            if not obs_path.exists():
                if not _GAME_ID_RE.match(args.observed):
                    raise ValueError("--observed must be a play-by-play file or 10-digit game id")
                obs_path = fetch_play_by_play(int(args.observed), args.cache_dir)
            with obs_path.open("r", encoding="utf-8") as handle:
                played = parse_play_by_play(json.load(handle))
            maps += [
                observed(played, args.team, grid, model),
                observed(played, args.opponent, grid, model),
            ]
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"HOCKEY HEATMAP FAILED: {error}", file=sys.stderr)
        return 1

    title = args.title or (
        f"{args.team} vs {args.opponent} projected scoring chances"
        + (f" — {args.date}" if args.date else "")
    )
    if args.format == "html":
        rendered = render_html(maps, grid, title, sources)
    elif args.format == "csv":
        rendered = render_csv(maps, grid)
    elif args.format == "json":
        rendered = to_json(maps, grid, model)
    else:
        use_color = not args.no_color and args.output is None and sys.stdout.isatty()
        rendered = render_text(maps, grid, color=use_color)

    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"HOCKEY HEATMAP WRITTEN: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
