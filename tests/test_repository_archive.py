"""Archive history stays intact and separate from current reference discovery."""

import hashlib
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from vessell.hosted_agent import REFERENCE_PATHS

ROOT = Path(__file__).parents[1]
ARCHIVED = (
    ("installation/VesselFramework_Path_Sync_Log_v3.8.md",
     "01aacf2ca3eb852d617f7a05baee6b8b9a3b86a2ad3c715d992b01a3696101bc"),
    ("installation/VesselFramework_v3.8.1_Stale_State_Correction.md",
     "7844a42d8dc4cedc9ce3ecbb51fe643219f4f4547800fe59f9328339da709e6d"),
    ("installation/VesselFramework_v3.8_Installation_Manifest.md",
     "425cf29e214b787e6333381d35fc4e13c0ad663b9b321f0f9c406d384b26a895"),
    ("demonstrations/VessellFramework_Portfolio_Showcase_SKILL_v1.0.md",
     "5703a9161e4e2c7acea1564eb5fd039824da24530d3007064740951940b3f7bd"),
    ("demonstrations/example_case_report.md",
     "85ec0132c0fdfbc2f2867ef27e08c475ae7802b118a564929af7ce0190579904"),
    ("game/game-integration-v3.9.1.md",
     "9774019baf1f7a6bae66950ec9987ced60e5c25fa7cb5e9950067dea12561dc2"),
    ("game/local-hail-ai-future-run-prompt.md",
     "939807013a232b1ee2c12cccd54faba01545486805092ead0e891bd0a49eff9d"),
)


@pytest.mark.parametrize("relative,expected", ARCHIVED)
def test_archived_snapshot_bytes_are_preserved(relative: str, expected: str) -> None:
    archived = ROOT / "archive" / relative
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == expected
    assert relative in (ROOT / "archive/README.md").read_text()


def test_archive_does_not_enter_active_reference_discovery() -> None:
    assert all(not path.startswith("archive/") for path in REFERENCE_PATHS)
    for relative, _ in ARCHIVED:
        assert (ROOT / "archive" / relative).name not in {
            Path(path).name for path in REFERENCE_PATHS
        }


@pytest.mark.parametrize("relative", [
    "README.md", "PROFESSOR_README.md", "PROFESSOR_PACKET_MANIFEST.md",
    "CANONICAL_REFERENCE.md", "META_REVIEW_AND_ROADMAP.md", "SKILL.md",
    "GAME_DEVELOPMENT_SKILL.md", "VesselFramework_Agent.md", "AGENTS.md",
    "VISION_AND_SCOPE.md", "archive/README.md", "docs/game-integration.md",
    "docs/repository-maintenance.md",
])
def test_current_cleanup_guides_have_existing_local_link_targets(relative: str) -> None:
    source = ROOT / relative
    for destination in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", source.read_text()):
        if destination.startswith(("https://", "http://", "mailto:", "#")):
            continue
        path = unquote(destination.split("#", 1)[0])
        assert (source.parent / path).exists(), f"{relative}: {destination}"
