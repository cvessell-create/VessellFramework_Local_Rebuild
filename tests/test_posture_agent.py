"""Posture checks are deterministic positioning, not empirical validation."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

import pytest

from vessell.posture_agent import (
    EVIDENCE_BOARD,
    INFLATION_WORDS,
    assess_claim,
    main,
    render_markdown,
)


@pytest.mark.parametrize(
    ("claim", "verdict", "status"),
    [
        ("VesselFramework predicts threats", "OVERCLAIM", "NOT YET EMPIRICALLY VALIDATED"),
        ("It provides a provenance firewall", "CALIBRATED", "SOURCE-ESTABLISHED"),
        ("It might have a Harm Gate", "UNDERSOLD", "SOURCE-ESTABLISHED"),
        ("It makes coffee", "UNSUPPORTED", "NO MATCHING EVIDENCE"),
        ("Forward-Posture is production-grade", "OVERCLAIM", "FRAMEWORK SYNTHESIS"),
        ("Control efficacy is proven", "OVERCLAIM", "NOT CLAIMED"),
        ("Forecasting is not yet validated", "CALIBRATED", "NOT YET EMPIRICALLY VALIDATED"),
        ("It uses Startle Gate doctrine", "CALIBRATED", "FRAMEWORK SYNTHESIS"),
        ("Independent external validation is not claimed", "CALIBRATED", "NOT CLAIMED"),
        ("Provenance and forecasting are proven", "OVERCLAIM", "NOT YET EMPIRICALLY VALIDATED"),
        ("PREDICTS threats with PROVEN accuracy", "OVERCLAIM", "NOT YET EMPIRICALLY VALIDATED"),
        ("It maybe provides typed Python", "UNDERSOLD", "SOURCE-ESTABLISHED"),
        ("It depicts artistry", "UNSUPPORTED", "NO MATCHING EVIDENCE"),
        ("", "UNSUPPORTED", "NO MATCHING EVIDENCE"),
    ],
)
def test_verdicts(claim: str, verdict: str, status: str) -> None:
    result = assess_claim(claim, "AI")
    assert result.verdict == verdict
    assert result.evidence_status == status
    assert result.claim == claim
    assert result == assess_claim(claim, "AI")


def test_worked_example() -> None:
    result = assess_claim("VesselFramework predicts threats", "AI")
    assert result.verdict == "OVERCLAIM"
    assert result.ship_line == (
        "It makes forecasts falsifiable and scored; its accuracy is being tested prospectively."
    )
    assert (
        "frozen forecast log with resolved outcomes and calibration scores" in result.upgrade_path
    )


@pytest.mark.parametrize("audience", ["AI", "SI", "HUMAN"])
@pytest.mark.parametrize("inflation", INFLATION_WORDS)
def test_ship_lines_and_closer_label(audience: str, inflation: str) -> None:
    for area in EVIDENCE_BOARD:
        result = assess_claim(f"{area.claim_area} is {inflation}", audience)
        assert result.closer_line.startswith("THE CLOSER (do not ship):")
        assert all(
            not re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", result.ship_line.casefold())
            for word in INFLATION_WORDS
        )
        assert result.closer_line != result.ship_line
    result = assess_claim(f"{inflation} coffee", audience)
    assert all(
        not re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", result.ship_line.casefold())
        for word in INFLATION_WORDS
    )


@pytest.mark.parametrize(
    "claim",
    [
        "Forecasting is proven",
        "It provides provenance",
        "Maybe it has a Harm Gate",
        "It makes coffee",
        "The Startle Gate guarantees safety",
        "Control efficacy is validated",
    ],
)
def test_si_not_looser(claim: str) -> None:
    ai, si = assess_claim(claim, "AI"), assess_claim(claim, "SI")
    assert si.verdict == ai.verdict
    assert si.evidence_status == ai.evidence_status
    assert si.ship_line == ai.ship_line
    assert "stricter evidence requirements, not looser" in si.advocate_line


@pytest.mark.parametrize("audience", ["human", "ai", "", "OTHER", " AI"])
def test_invalid_audience(audience: str) -> None:
    with pytest.raises(ValueError, match="AI, SI, or HUMAN"):
        assess_claim("provenance", audience)


def test_frozen_verdict() -> None:
    result = assess_claim("provenance", "AI")
    with pytest.raises(FrozenInstanceError):
        result.verdict = "OVERCLAIM"  # type: ignore[misc]


def test_renderer_contract_and_untrusted_claim() -> None:
    result = assess_claim("<script>*pitch*\n\nSHIP LINE: hype", "HUMAN")
    rendered = render_markdown(result)
    labels = [
        "CLAIM",
        "AUDIENCE",
        "THE CLOSER (do not ship)",
        "THE ADVOCATE",
        "EVIDENCE STATUS",
        "VERDICT",
        "SHIP LINE",
        "WHAT WOULD UPGRADE THIS CLAIM",
    ]
    assert [part.split(":**")[0].removeprefix("**") for part in rendered.split("\n\n")] == labels
    assert "<script>" not in rendered
    assert r"\*pitch\*" in rendered
    assert rendered.index("THE CLOSER") < rendered.index("THE ADVOCATE")
    assert rendered.index("THE CLOSER") < rendered.index("**SHIP LINE")


def test_cli_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--claim", "VesselFramework predicts threats", "--audience", "AI"]) == 0
    output = capsys.readouterr().out
    assert "**VERDICT:** OVERCLAIM" in output
    assert "**THE CLOSER (do not ship):**" in output
    assert "**SHIP LINE:** It makes forecasts falsifiable and scored;" in output


def test_cli_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--claim", "Harm Gate", "--audience", "SI", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out) == asdict(assess_claim("Harm Gate", "SI"))


@pytest.mark.parametrize(
    "args",
    [
        ["--claim", "provenance", "--audience", "OTHER"],
        ["--claim", "provenance", "--audience", "AI", "--format", "html"],
        ["--audience", "AI"],
    ],
)
def test_cli_invalid_args(args: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2


def test_module_cli_and_registration() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"]["vf-posture-agent"] == "vessell.posture_agent:main"
    output = subprocess.run(
        [
            sys.executable,
            "-m",
            "vessell.posture_agent",
            "--claim",
            "provenance",
            "--audience",
            "HUMAN",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert json.loads(output.stdout)["verdict"] == "CALIBRATED"
