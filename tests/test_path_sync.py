import hashlib

import pytest

import install_vesselframework_v3_8 as sync


def test_sync_replace_matches_source_and_records_read_back_hash(tmp_path, monkeypatch) -> None:
    source = tmp_path / "canonical.md"
    source.write_text("Canonical skill\n", encoding="utf-8")
    monkeypatch.setattr(sync, "TARGET_ROOT", tmp_path)
    cfg = {"source": source, "role": "live_skill", "mode": "replace", "required": True}
    result = sync.sync_one("/copy/SKILL.md", cfg, True, True, tmp_path / "log.jsonl")
    assert result["status"] == "UPDATED"
    assert result["post_hash"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert (tmp_path / "copy/SKILL.md").read_bytes() == source.read_bytes()


def test_corrupted_readback_is_not_reported_as_synchronized(tmp_path, monkeypatch) -> None:
    source = tmp_path / "canonical.md"
    source.write_text("Canonical skill\n", encoding="utf-8")
    monkeypatch.setattr(sync, "TARGET_ROOT", tmp_path)
    monkeypatch.setattr(sync, "atomic_write_text", lambda target, text: target.write_text("wrong"))
    cfg = {"source": source, "role": "live_skill", "mode": "replace", "required": True}
    result = sync.sync_one("/copy/SKILL.md", cfg, True, True, tmp_path / "log.jsonl")
    assert result["status"] == "ERROR"
    assert "Post-write hash" in result["error"]


@pytest.mark.parametrize("mode", ["replace", "managed_block"])
@pytest.mark.parametrize("corrupt", [False, True])
def test_windows_multiline_write_verification(tmp_path, monkeypatch, mode, corrupt) -> None:
    fdopen = sync.os.fdopen

    def windows_fdopen(fd, mode, *, encoding, newline=None):
        return fdopen(fd, mode, encoding=encoding, newline="\r\n" if newline is None else newline)

    monkeypatch.setattr(sync.os, "fdopen", windows_fdopen)
    probe = tmp_path / "windows-default.md"
    fd, probe_name = sync.tempfile.mkstemp(dir=tmp_path)
    with sync.os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write("first\nsecond\n")
    sync.os.replace(probe_name, probe)
    assert probe.read_bytes() == b"first\r\nsecond\r\n"

    content = "Canonical skill\nSecond line: caf\u00e9\n"
    if mode == "managed_block":
        content = f"{sync.MANAGED_START}\n{content}{sync.MANAGED_END}\n"
    source = tmp_path / "canonical.md"
    source.write_bytes(content.encode("utf-8"))
    monkeypatch.setattr(sync, "TARGET_ROOT", tmp_path)
    target = tmp_path / "copy/SKILL.md"
    if mode == "managed_block":
        target.parent.mkdir()
        target.write_bytes(b"Owner prefix\n\n")
        content = sync.update_managed_block("Owner prefix\n\n", content)

    if corrupt:
        replace = sync.os.replace

        def corrupt_replace(src, dst):
            replace(src, dst)
            dst.write_bytes(dst.read_bytes().replace(b"\n", b"\r\n"))

        monkeypatch.setattr(sync.os, "replace", corrupt_replace)

    cfg = {"source": source, "role": "live_skill", "mode": mode, "required": True}
    result = sync.sync_one("/copy/SKILL.md", cfg, True, True, tmp_path / "log.jsonl")
    assert result["post_hash"] == hashlib.sha256(target.read_bytes()).hexdigest()
    if corrupt:
        assert result["status"] == "ERROR"
        assert "Post-write hash" in result["error"]
        assert target.read_bytes() != content.encode("utf-8")
    else:
        assert result["status"] == "UPDATED"
        assert target.read_bytes() == content.encode("utf-8")
