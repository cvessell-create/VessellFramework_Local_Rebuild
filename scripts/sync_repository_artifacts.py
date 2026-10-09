"""Refresh reviewed tracked-file hashes and the canonical packaged skill mirror."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

MANIFEST_NAME = "VessellFramework_v3.8.1_SHA256_Manifest.json"
MIRROR_PATH = Path("mnt/skills/user/vessel-framework-analyst/SKILL.md")
EXCLUDED_PARTS = {
    ".git", ".venv", "build", "dist", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", ".next",
}


def refresh_artifacts(root: Path, tracked_paths: list[str]) -> int:
    root = root.resolve()
    paths = sorted(set(tracked_paths) - {MANIFEST_NAME})
    for name in paths:
        path = Path(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or EXCLUDED_PARTS.intersection(path.parts)
            or any(part.endswith(".egg-info") for part in path.parts)
            or path.name == ".env"
        ):
            raise ValueError(f"Not a distribution source artifact: {name}")
        target = root / path
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"Expected a regular tracked source file: {name}")
        target.resolve().relative_to(root)

    if "SKILL.md" not in paths or MIRROR_PATH.as_posix() not in paths:
        raise ValueError("Both the canonical skill and packaged mirror must be tracked.")
    manifest_path = root / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise TypeError("Expected a manifest object containing a files list.")
    (root / MIRROR_PATH).write_bytes((root / "SKILL.md").read_bytes())
    manifest["files"] = [
        {"path": name, "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()}
        for name in paths
    ]
    manifest["generated_utc"] = datetime.now(UTC).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return len(paths)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Refresh artifacts after reviewing and staging the intended source changes.",
    )
    args = parser.parse_args()
    if not args.apply:
        parser.error("Review and stage source changes first, then explicitly pass --apply.")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True,
    )
    paths = result.stdout.decode("utf-8").rstrip("\0").split("\0")
    print(f"Refreshed skill mirror and hashes for {refresh_artifacts(root, paths)} files.")


if __name__ == "__main__":
    main()
