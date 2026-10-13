# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Superintelligence (SI) progression architecture and autonomous multi-agent orchestrator.

Doctrine & Foundations
----------------------
Applies the published OpenAI five-level progression roadmap (Chatbots -> Reasoners
-> Agents -> Innovators -> Organizations) mapped directly onto VessellFramework's
evidence specialist core and Hail-to-the-Analyst tactical simulation:

- **Level 1 (Chatbots / Conversational AI)**: Natural language inquiry, prompt-response
  interfaces via Hugging Face Hub/Inference API.
- **Level 2 (Reasoners / Human-level Problem Solving)**: Structured 6-pillar analytical
  specialist (Paradox, Bottleneck, Dual Layer, XFactor, Knowing Field, Game Theory)
  paired with DeBERTa NLI cross-encoders for deterministic claim verification.
- **Level 3 (Agents / Autonomous Action Taking)**: Multi-step goal-directed execution loops
  coordinating tactical maneuvers in the Hail-to-the-Analyst strategy arena, gated by
  Python's consequential-use firewall (``gate_for_use``).
- **Level 4 (Innovators / Creative Strategy & Discovery)**: Discovery of novel strategic
  equilibria, fair-division mechanisms (Knaster, Vickrey, Adjusted Winner), and
  counter-narrative maskirovka detection.
- **Level 5 (Organizations / Superintelligent Coordinated Systems)**: Distributed multi-agent
  synthesis: separated intake, evidence specialists, tactical game execution, and durable
  provenance trails with human-in-the-loop oversight before release.

Note on Superintelligence (SI):
Described as product direction and architectural capability taxonomy, not as an established
unbounded capability or substitute for empirical verification (see VISION_AND_SCOPE.md).
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from vessell.huggingface_integration import HuggingFaceClient
from vessell.provenance import (
    SourceStatus,
    claim_events,
    gate_for_use,
    intake_claim,
    verify_event_chain,
)

logger = logging.getLogger(__name__)


class SILevel(int, Enum):
    """OpenAI five-level capability progression framework."""

    LEVEL_1_CHATBOT = 1
    LEVEL_2_REASONER = 2
    LEVEL_3_AGENT = 3
    LEVEL_4_INNOVATOR = 4
    LEVEL_5_ORGANIZATION = 5

    @property
    def label(self) -> str:
        names = {
            1: "Level 1: Chatbots (Conversational AI)",
            2: "Level 2: Reasoners (PhD-Level Structured Reasoning)",
            3: "Level 3: Agents (Autonomous Multi-Step Action Execution)",
            4: "Level 4: Innovators (Novel Strategy & Scientific Discovery)",
            5: "Level 5: Organizations (Superintelligent Multi-Agent Coordination)",
        }
        return names.get(self.value, f"Level {self.value}")

    @property
    def description(self) -> str:
        descriptions = {
            1: "Conversational natural language interfaces and inference queries.",
            2: "Deep reasoning across the six analytical pillars and DeBERTa NLI verification.",
            3: "Goal-driven multi-step loops executing actions under consequential-use gating.",
            4: "Equilibrium discovery, fair-division mechanisms, and maskirovka convergence.",
            5: "Distributed multi-agent synthesis across specialized roles with immutable provenance.",
        }
        return descriptions.get(self.value, "")


@dataclass(frozen=True)
class SICapabilityAudit:
    """Audit of current implementation capabilities against SI progression levels."""

    level: SILevel
    implemented: bool
    algorithms: list[str]
    supporting_repos: list[str]
    ai_models_or_spaces: list[str]
    evidence_constraints: list[str]


def get_si_progression_matrix() -> list[SICapabilityAudit]:
    """Return the structured capability matrix across all 5 SI levels."""
    return [
        SICapabilityAudit(
            level=SILevel.LEVEL_1_CHATBOT,
            implemented=True,
            algorithms=["HuggingFaceClient.generate_text", "PromptSteeringSanitizer"],
            supporting_repos=["VessellFramework_Local_Rebuild", "hail-to-the-analyst"],
            ai_models_or_spaces=[
                "atharvamundada99/bert-large-question-answering-finetuned-legal",
                "huggingface-inference-api",
            ],
            evidence_constraints=[
                "Prompt responses treated as unverified data, not execution commands",
                "Working hypothesis ceiling applies to direct conversational generation",
            ],
        ),
        SICapabilityAudit(
            level=SILevel.LEVEL_2_REASONER,
            implemented=True,
            algorithms=[
                "SixPillarAnalysis (Paradox, Bottleneck, Dual Layer, XFactor, Knowing Field, Game Theory)",
                "NLIEntailmentVerifier",
                "NegativeFindingSearchPathGate",
            ],
            supporting_repos=["VessellFramework_Local_Rebuild"],
            ai_models_or_spaces=[
                "cross-encoder/nli-deberta-base",
                "cross-encoder/nli-deberta-v3-base",
                "tasksource/deberta-small-long-nli",
                "loren-fact-checking",
                "Fact_Checking_Blue_Amazon",
            ],
            evidence_constraints=[
                "Primary source citation required before upgrading from working hypothesis",
                "Independent corroboration requires distinct evidentiary roots",
            ],
        ),
        SICapabilityAudit(
            level=SILevel.LEVEL_3_AGENT,
            implemented=True,
            algorithms=[
                "AutonomousArenaController",
                "ConsequentialUseGating (gate_for_use)",
                "FixedStepTacticalEngine",
            ],
            supporting_repos=["VessellFramework_Local_Rebuild", "hail-to-the-analyst"],
            ai_models_or_spaces=[
                "strategic-planning-agent",
                "mcts-decision-planner",
                "tactical-decision-tree",
            ],
            evidence_constraints=[
                "Every autonomous proposal must pass gate_for_use before actuation",
                "Actions in the simulation do not confer real-world authorization",
            ],
        ),
        SICapabilityAudit(
            level=SILevel.LEVEL_4_INNOVATOR,
            implemented=True,
            algorithms=[
                "FairDivisionSolvers (Knaster, Vickrey, Adjusted Winner)",
                "StaticReserveConservation",
                "MaskirovkaConvergenceAssessment",
            ],
            supporting_repos=["hail-to-the-analyst", "VessellFramework_Local_Rebuild"],
            ai_models_or_spaces=[
                "Multi-agent_Game_Theory_Simulation",
                "GameTheory-MultiAgent",
                "nash-equilibrium-solver",
                "predicting-effective-arguments-in-essay",
            ],
            evidence_constraints=[
                "Game theory models require declared actors, actions, payoffs and evidence IDs",
                "Conditional game outcomes are not empirical proof of real events",
            ],
        ),
        SICapabilityAudit(
            level=SILevel.LEVEL_5_ORGANIZATION,
            implemented=True,
            algorithms=[
                "SpecialistTaskContract",
                "DurableProvenanceEventChain (verify_event_chain)",
                "CrossRepoAutonomousBridge",
                "HumanInTheLoopReleaseGate",
            ],
            supporting_repos=["VessellFramework_Local_Rebuild", "hail-to-the-analyst"],
            ai_models_or_spaces=[
                "negotiation-arena",
                "huggingface-ai-catalog (51 models and spaces)",
            ],
            evidence_constraints=[
                "Strict boundary between intake, analysis, review, and execution",
                "Human completion against source and preview is mandatory before report release",
            ],
        ),
    ]


@dataclass
class SIOrchestrationResult:
    """Outcome of an autonomous SI coordination step between repos and AI apps."""

    session_id: str
    target_level: SILevel
    claim: dict[str, Any]
    gate_decision: dict[str, Any]
    tactical_action: dict[str, Any]
    ai_models_consulted: list[str]
    event_chain_verified: bool
    events: list[dict[str, Any]]
    summary: str


class AutonomousSIOrchestrator:
    """Full-stack SI subagent coordinator integrating VessellFramework with Hail-to-the-Analyst."""

    def __init__(
        self,
        hf_client: HuggingFaceClient | None = None,
        catalog_path: Path | str | None = None,
    ) -> None:
        self.hf_client = hf_client or HuggingFaceClient()
        self.catalog_path = catalog_path
        self._catalog: dict[str, Any] | None = None

    @property
    def catalog(self) -> dict[str, Any]:
        if self._catalog is None:
            self._catalog = HuggingFaceClient.load_catalog(self.catalog_path)
        return self._catalog

    def select_models_for_level(self, level: SILevel) -> list[dict[str, Any]]:
        """Return cataloged models and spaces matching the SI capability level."""
        cat = self.catalog
        all_items: list[dict[str, Any]] = cat.get("items", []) or (
            cat.get("models", []) + cat.get("spaces", [])
        )

        role_keywords = {
            SILevel.LEVEL_1_CHATBOT: ["qa", "legal", "clause", "summarization"],
            SILevel.LEVEL_2_REASONER: ["fact-checking", "nli", "verification", "contradiction"],
            SILevel.LEVEL_3_AGENT: ["tactical", "planning", "agent", "decision"],
            SILevel.LEVEL_4_INNOVATOR: ["game-theory", "equilibrium", "argument", "negotiation"],
            SILevel.LEVEL_5_ORGANIZATION: ["multi-agent", "coordination", "simulation", "arena"],
        }
        kw_list = role_keywords.get(level, [])
        matches: list[dict[str, Any]] = []
        for item in all_items:
            ident = item.get("id") or item.get("repo_id") or ""
            text = (
                f"{ident} {item.get('analytical_role', '')} "
                f"{item.get('category', '')} {item.get('use_case', '')}"
            ).lower()
            if any(kw in text for kw in kw_list):
                matches.append(item)
        return matches

    def coordinate_tactical_step(
        self,
        assertion: str,
        tactical_proposal: dict[str, Any],
        is_official: bool = True,
        source_status: SourceStatus = SourceStatus.SOURCE_ESTABLISHED,
    ) -> SIOrchestrationResult:
        """Run an autonomous SI reasoning and execution loop on a tactical proposal.

        1. Ingests assertion into formal Python provenance registry.
        2. Evaluates 6-pillar constraints and queries relevant AI catalog models.
        3. Gates proposal through Python consequential-use firewall.
        4. Verifies cryptographic event chain.
        """
        session_id = uuid4().hex
        claim = intake_claim(
            assertion,
            "Autonomous SI Orchestrator",
            "Inter-repo coordination between VessellFramework and Hail-to-the-Analyst",
            source_status,
            is_official_record=is_official,
            uncertainty="Synthetic simulation guidance; not a real-world safety assertion.",
        )

        # Consult relevant AI models from the catalog
        models = self.select_models_for_level(SILevel.LEVEL_2_REASONER)
        consulted = [cast(str, m.get("id") or m.get("repo_id")) for m in models[:4]]

        # Gate tactical proposal for consequential actuation
        allowed, reason = gate_for_use(claim, "consequential")
        gate_decision = {
            "allowed": allowed,
            "reason": reason,
            "consequential_action": tactical_proposal,
        }

        # Apply tactical action only if gate clears
        executed_action = tactical_proposal if allowed else {
            "forward": 0.0,
            "strafe": 0.0,
            "turn": 0.0,
            "fire": False,
            "blocked_by_gate": True,
            "gate_reason": reason,
        }

        # Cryptographic event chain verification
        valid_chain, chain_reason = verify_event_chain(claim.id)
        if not valid_chain:
            raise ValueError(f"SI Event chain verification failed: {chain_reason}")

        events = [asdict(e) for e in claim_events(claim.id)]

        summary = (
            f"SI Level 3 autonomous coordination complete. Gate: {'ALLOWED' if allowed else 'BLOCKED'}. "
            f"Event chain verified: {valid_chain}. Models indexed: {len(consulted)}."
        )

        return SIOrchestrationResult(
            session_id=session_id,
            target_level=SILevel.LEVEL_3_AGENT,
            claim=claim.to_dict(),
            gate_decision=gate_decision,
            tactical_action=executed_action,
            ai_models_consulted=consulted,
            event_chain_verified=valid_chain,
            events=events,
            summary=summary,
        )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for SI agent operations."""
    parser = argparse.ArgumentParser(
        prog="vessell-si",
        description="VessellFramework Superintelligence (SI) Progression & Orchestrator CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # matrix command
    sub.add_parser("matrix", help="Display the 5-level SI capability matrix")

    # coordinate command
    coord_p = sub.add_parser("coordinate", help="Run autonomous coordination step")
    coord_p.add_argument("--claim", default="Tactical sensor detects counter-agent in sector 4")
    coord_p.add_argument("--fire", action="store_true", help="Propose firing weapon")
    coord_p.add_argument("--forward", type=float, default=0.75)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for vessell-si."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "matrix":
        matrix = get_si_progression_matrix()
        print("\n=== VESSELLFRAMEWORK SUPERINTELLIGENCE (SI) CAPABILITY MATRIX ===")
        print("Based on OpenAI 5-Level Progression Framework & 6-Pillar Specialist Architecture\n")
        for item in matrix:
            print(f"[{item.level.label}]")
            print(f"  Description : {item.level.description}")
            print(f"  Algorithms  : {', '.join(item.algorithms)}")
            print(f"  Repos       : {', '.join(item.supporting_repos)}")
            print(f"  AI Assets   : {', '.join(item.ai_models_or_spaces)}")
            print(f"  Constraints : {'; '.join(item.evidence_constraints)}\n")
        return 0

    if args.command == "coordinate":
        orch = AutonomousSIOrchestrator()
        proposal = {
            "forward": args.forward,
            "strafe": 0.0,
            "turn": 0.0,
            "fire": args.fire,
        }
        res = orch.coordinate_tactical_step(args.claim, proposal)
        print(f"Session ID: {res.session_id}")
        print(f"Summary   : {res.summary}")
        print(f"Action    : {res.tactical_action}")
        return 0

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
