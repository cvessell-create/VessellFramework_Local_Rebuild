"""Deterministic positioning checks; no evidence creation or action clearance."""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import asdict, dataclass
from typing import Literal

EvidenceStatus = Literal[
    "SOURCE-ESTABLISHED",
    "FRAMEWORK SYNTHESIS",
    "NOT YET EMPIRICALLY VALIDATED",
    "NOT CLAIMED",
]
Verdict = Literal["OVERCLAIM", "CALIBRATED", "UNDERSOLD", "UNSUPPORTED"]

INFLATION_WORDS = (
    "proven",
    "predicts",
    "predictive",
    "guarantees",
    "guaranteed",
    "production-grade",
    "validated",
    "best-in-class",
    "generational",
    "perfect",
    "infallible",
    "always",
    "never fails",
    "state-of-the-art",
)
HEDGE_WORDS = ("maybe", "might", "may", "perhaps", "possibly", "seems", "appears")


@dataclass(frozen=True)
class EvidenceArea:
    claim_area: str
    status: EvidenceStatus
    triggers: tuple[str, ...]
    ship_line: str
    upgrade_path: str


EVIDENCE_BOARD: tuple[EvidenceArea, ...] = (
    EvidenceArea(
        "Provenance firewall, independence logic, evidence-status taxonomy",
        "SOURCE-ESTABLISHED",
        ("provenance", "independence", "evidence-status", "evidence status", "taxonomy"),
        "It provides a provenance firewall, independence logic, and an evidence-status taxonomy.",
        "Trace each claim to the current source and regression tests.",
    ),
    EvidenceArea(
        "Harm Gate: unknown never becomes clearance",
        "SOURCE-ESTABLISHED",
        ("harm gate", "unknown", "clearance"),
        "The Harm Gate keeps unknown answers from becoming clearance.",
        "Trace the gate and its runner exits to current source and regression tests.",
    ),
    EvidenceArea(
        "Typed Python, mypy/ruff, SHA-256 manifest, regression suite",
        "SOURCE-ESTABLISHED",
        ("typed python", "mypy", "ruff", "sha-256", "manifest", "regression", "python"),
        "It includes typed Python, mypy/ruff checks, a SHA-256 manifest, and a regression suite.",
        "Run lint, type checks, manifest verification, and the full regression suite.",
    ),
    EvidenceArea(
        "Forward-Posture ladder, Startle Gate, Maskirovka checks",
        "FRAMEWORK SYNTHESIS",
        ("forward-posture", "forward posture", "startle", "maskirovka"),
        "Forward-Posture, Startle Gate, and Maskirovka checks are framework synthesis "
        "with doctrine and partial code, not evidence of control efficacy.",
        "Complete the executable controls and assess them against frozen external test cases.",
    ),
    EvidenceArea(
        "Forecasting performance",
        "NOT YET EMPIRICALLY VALIDATED",
        (
            "forecast",
            "forecasts",
            "forecasting",
            "prediction",
            "predictions",
            "predicts",
            "predictive",
            "accuracy",
        ),
        "It makes forecasts falsifiable and scored; its accuracy is being tested prospectively.",
        "A frozen forecast log with resolved outcomes and calibration scores.",
    ),
    EvidenceArea(
        "Control efficacy / independent external validation",
        "NOT CLAIMED",
        (
            "control efficacy",
            "effective controls",
            "external validation",
            "externally validated",
            "independent validation",
            "independently validated",
        ),
        "Control efficacy and independent external assessment are not claimed.",
        "Independent external evaluation with documented methods, outcomes, and limitations.",
    ),
)


@dataclass(frozen=True)
class PostureVerdict:
    claim: str
    audience: str
    closer_line: str
    advocate_line: str
    evidence_status: str
    verdict: Verdict
    ship_line: str
    upgrade_path: str


def _normalize(text: str) -> str:
    return " ".join(text.casefold().replace("—", "-").replace("–", "-").split())


def _matches(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


def _inflated(text: str) -> bool:
    for word in INFLATION_WORDS:
        for match in re.finditer(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text):
            # Explicit negation names a limit, not an affirmative evidence claim.
            if not re.search(r"\b(?:not(?: yet)?|never|no)\s+$", text[: match.start()]):
                return True
    return False


def assess_claim(claim: str, audience: str) -> PostureVerdict:
    """Apply a finite keyword policy, not a semantic or empirical verification.

    Mixed claims use the least-established matching area. AI and SI use identical
    verdict rules; audience framing cannot relax an evidence requirement.
    """
    if audience not in ("AI", "SI", "HUMAN"):
        raise ValueError("Audience must be AI, SI, or HUMAN.")
    text = _normalize(claim)
    areas = [
        area for area in EVIDENCE_BOARD if any(_matches(text, trigger) for trigger in area.triggers)
    ]
    if not areas:
        status = "NO MATCHING EVIDENCE"
        verdict: Verdict = "UNSUPPORTED"
        ship_line = "This claim has no matching evidence on the board; treat it as a hypothesis."
        upgrade_path = "Define the claim, identify traceable evidence, and add it to the board."
    else:
        priority = {
            "SOURCE-ESTABLISHED": 0,
            "FRAMEWORK SYNTHESIS": 1,
            "NOT YET EMPIRICALLY VALIDATED": 2,
            "NOT CLAIMED": 3,
        }
        area = max(areas, key=lambda item: priority[item.status])
        status = area.status
        if status != "SOURCE-ESTABLISHED" and _inflated(text):
            verdict = "OVERCLAIM"
        elif status == "SOURCE-ESTABLISHED" and any(_matches(text, hedge) for hedge in HEDGE_WORDS):
            verdict = "UNDERSOLD"
        else:
            verdict = "CALIBRATED"
        ship_line = area.ship_line
        upgrade_path = area.upgrade_path
    framing = {
        "AI": "Lead with guardrails it can run; the Harm Gate still governs action.",
        "SI": "The same contract needs stricter evidence requirements, not looser ones; no flattery.",
        "HUMAN": "Present a methodological contribution, traceable risk controls, and a "
        "validation roadmap, not a finished platform.",
    }
    return PostureVerdict(
        claim=claim,
        audience=audience,
        closer_line="THE CLOSER (do not ship): Generational! Proven! Production-grade! "
        "Sign now before the stars take the last slot.",
        advocate_line=f"{ship_line} {framing[audience]} Not ready for a broader contract yet.",
        evidence_status=status,
        verdict=verdict,
        ship_line=ship_line,
        upgrade_path=upgrade_path,
    )


def _markdown_value(value: str) -> str:
    value = html.escape(" ".join(value.split()))
    return re.sub(r"([\\`*_{}\[\]()#+.!|>-])", r"\\\1", value)


def render_markdown(result: PostureVerdict) -> str:
    """Render the eight contract fields without letting input forge new fields."""
    fields = (
        ("CLAIM", result.claim),
        ("AUDIENCE", result.audience),
        ("THE CLOSER (do not ship)", result.closer_line),
        ("THE ADVOCATE", result.advocate_line),
        ("EVIDENCE STATUS", result.evidence_status),
        ("VERDICT", result.verdict),
        ("SHIP LINE", result.ship_line),
        ("WHAT WOULD UPGRADE THIS CLAIM", result.upgrade_path),
    )
    return "\n\n".join(f"**{label}:** {_markdown_value(value)}" for label, value in fields) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", required=True)
    parser.add_argument("--audience", required=True, choices=("AI", "SI", "HUMAN"))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    result = assess_claim(args.claim, args.audience)
    if args.format == "json":
        print(json.dumps(asdict(result), indent=2))
    else:
        print(render_markdown(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
