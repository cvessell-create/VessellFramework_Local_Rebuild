import hashlib
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_owner_paper_remains_exact_reconciled_source():
    record = json.loads((ROOT / "docs/paper-source-reconciliation.json").read_text())
    source = ROOT / record["canonical_path"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == record["source_document_sha256"]
    assert record["historical_external_records_verified"] is False


def test_supplied_sixth_pillar_logs_are_preserved_not_rewritten():
    register = json.loads((ROOT / "docs/game-theory/source-register.json").read_text())
    assert len(register["files"]) == 21
    for entry in register["files"]:
        source = ROOT / "docs/game-theory/source-log" / entry["path"]
        data = source.read_bytes()
        assert len(data) == entry["bytes"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]


def test_authorship_policy_is_wired_and_does_not_claim_interference_as_fact():
    name = "docs/civilian-authorship-and-model-interference.md"
    for target in ("AGENTS.md", "VISION_AND_SCOPE.md", ".github/copilot-instructions.md",
                   "SKILL.md", "README.md", "MANIFEST.in"):
        assert name in (ROOT / target).read_text()
    text = (ROOT / name).read_text()
    assert "not established by" in text
    assert "cannot\n   disable host/provider controls" in text
    assert (ROOT / "SKILL.md").read_bytes() == (
        ROOT / "mnt/skills/user/vessel-framework-analyst/SKILL.md").read_bytes()


def test_readme_preserves_product_boundaries_and_source_references():
    readme = (ROOT / "README.md").read_text()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    assert f"**{version}**" in readme
    assert "**full-stack SI sub-agent**" in readme
    assert "[Human review workspace](docs/ambient-workflows.md)" in readme
    assert "Supporting control plane" in readme
    assert "Intake, analysis, report release and\nexecution have separate permissions." in readme
    for source in (
        "VISION_AND_SCOPE.md",
        "VesselFramework_Knowing_Field_SKILL_v0.1.md",
        "VesselFramework_Game_Theory_SKILL_v0.1.md",
        "docs/paper-source-reconciliation.md",
        "docs/claim-verifier.md",
        "docs/specialist-agent.md",
        "docs/ambient-workflows.md",
        "scripts/sync_repository_artifacts.py",
    ):
        assert source in readme
    assert "Every report needs human Knowing Field completion against its sources and\npreview" in readme
    assert "Test fixtures stay separate from\nthe original paper's incidents." in readme


def test_personal_family_direction_is_a_proposal_not_a_capability_or_license_change():
    guide = "docs/personal-family-protection-guide.md"
    spec = "docs/personal-family-agent-spec.md"
    for target in ("README.md", "VISION_AND_SCOPE.md", "PROFESSOR_README.md",
                   "CANONICAL_REFERENCE.md", "MANIFEST.in"):
        text = (ROOT / target).read_text()
        assert guide in text
        assert spec in text
    professor = (ROOT / "PROFESSOR_README.md").read_text()
    assert "six analytical pillars" in professor
    assert "docs/claim-correction-case-study.md" in professor
    assert "Family isolation, safe\nsharing and protective workflows are unfinished." in professor
    assert "Empirical usefulness and transfer\nto personal/family protection still need study." in professor
    specification = (ROOT / spec).read_text()
    assert "NOT IMPLEMENTED / NOT VALIDATED" in specification
    assert "NOT_SELECTED" in specification
    assert "Distinct state vocabularies" in specification
    protection = (ROOT / guide).read_text()
    assert "OWNER-ORIENTED DRAFT" in protection
    assert "The [Apache license](../LICENSE) remains unchanged." in protection
