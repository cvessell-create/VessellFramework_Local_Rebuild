import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prune", ROOT / "scripts" / "prune_provable_lines.py")
assert spec and spec.loader
prune = importlib.util.module_from_spec(spec)
sys.modules["prune"] = prune
spec.loader.exec_module(prune)

BURST = prune.Constant(
    "BURST_MIN_SOURCES",
    4.0,
    "vessell/x.py",
    1,
    "vessell.x",
    frozenset({"burst", "sources"}),
    frozenset({"x"}),
)
COVERED = {"vessell.x": "tests/test_x.py"}


def test_restated_threshold_is_provable() -> None:
    found = prune.proof("| burst | >= 4 sources |", [BURST], COVERED)
    assert found == [
        {
            "value": 4.0,
            "constant": "BURST_MIN_SOURCES",
            "code": "vessell/x.py:1",
            "test": "tests/test_x.py",
        }
    ]


def test_negated_untested_or_unmatched_lines_are_kept() -> None:
    assert prune.proof("No 4 sources burst rule.", [BURST], COVERED) is None
    assert prune.proof("| burst | >= 4 sources |", [BURST], {}) is None
    assert prune.proof("| burst | >= 5 sources |", [BURST], COVERED) is None
    assert prune.proof("Use port 4 here.", [BURST], COVERED) is None


def test_owner_and_paper_sources_are_excluded() -> None:
    for path in (
        "docs/paper-source-reconciliation.md",
        "docs/owner-fourth-person-perspective.md",
        "case_studies/a.md",
    ):
        assert any(rule.search(path) for rule in prune.EXCLUDED)
