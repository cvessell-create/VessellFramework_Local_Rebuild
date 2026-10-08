import hashlib
import json
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
