import hashlib
import json
from pathlib import Path

import pytest

from scripts.sync_repository_artifacts import MANIFEST_NAME, MIRROR_PATH, refresh_artifacts


def make_sources(root: Path) -> list[str]:
    (root / "SKILL.md").write_bytes(b"canonical\n")
    mirror = root / MIRROR_PATH
    mirror.parent.mkdir(parents=True)
    mirror.write_bytes(b"stale\n")
    (root / MANIFEST_NAME).write_text(json.dumps({
        "package_version": "3.12.0", "runtime_state_claim": "UNVERIFIED", "files": [],
    }))
    return ["SKILL.md", MIRROR_PATH.as_posix(), MANIFEST_NAME]


def test_refresh_preserves_metadata_and_synchronizes_only_declared_sources(tmp_path: Path):
    paths = make_sources(tmp_path)
    (tmp_path / "private.txt").write_text("not tracked")
    assert refresh_artifacts(tmp_path, paths) == 2
    assert (tmp_path / MIRROR_PATH).read_bytes() == (tmp_path / "SKILL.md").read_bytes()
    manifest = json.loads((tmp_path / MANIFEST_NAME).read_text())
    assert manifest["runtime_state_claim"] == "UNVERIFIED"
    assert manifest["package_version"] == "3.12.0"
    assert {entry["path"] for entry in manifest["files"]} == set(paths) - {MANIFEST_NAME}
    for entry in manifest["files"]:
        assert entry["sha256"] == hashlib.sha256(
            (tmp_path / entry["path"]).read_bytes()
        ).hexdigest()


@pytest.mark.parametrize("invalid", ["../outside", "/outside", "build/copy.py", ".env"])
def test_refresh_rejects_invalid_sources_before_writing(tmp_path: Path, invalid: str):
    paths = make_sources(tmp_path)
    before = (tmp_path / MIRROR_PATH).read_bytes()
    with pytest.raises(ValueError, match="distribution source"):
        refresh_artifacts(tmp_path, paths + [invalid])
    assert (tmp_path / MIRROR_PATH).read_bytes() == before
