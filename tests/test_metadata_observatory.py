import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from vessell import metadata_observatory as observatory


def test_junit_retains_only_outcomes_hashed_ids_and_timings(tmp_path: Path) -> None:
    path = tmp_path / "tests.xml"
    path.write_text(
        '<testsuites><testsuite>'
        '<testcase classname="private" name="secret-parameter" time="1"/>'
        '<testcase classname="a" name="b" time="2"><failure>private</failure></testcase>'
        '<testcase classname="a" name="c" time="3"><skipped>private</skipped></testcase>'
        '<system-out>credentials</system-out></testsuite></testsuites>'
    )
    summary = observatory.summarize_junit(path)
    encoded = json.dumps(summary)
    assert "private" not in encoded and "secret-parameter" not in encoded
    assert "credentials" not in encoded
    assert summary["counts"] == {"passed": 1, "failed": 1, "error": 0, "skipped": 1}
    assert summary["failure_fraction"] == 0.5
    assert summary["median_seconds"] == 2
    assert summary["p95_seconds"] == pytest.approx(2.9)
    assert all(len(row["test_id"]) == 64 for row in summary["records"])


@pytest.mark.parametrize("duration", ["nan", "inf", "-1"])
def test_junit_invalid_durations_stop(tmp_path: Path, duration: str) -> None:
    path = tmp_path / "tests.xml"
    path.write_text(f'<testsuite><testcase name="test" time="{duration}"/></testsuite>')
    with pytest.raises(ValueError, match="duration"):
        observatory.summarize_junit(path)


def test_empty_junit_has_no_success_shaped_metrics(tmp_path: Path) -> None:
    path = tmp_path / "tests.xml"
    path.write_text("<testsuites/>")
    summary = observatory.summarize_junit(path)
    assert summary["failure_fraction"] is None
    assert summary["median_seconds"] is None


def test_source_metadata_stores_counts_not_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "one.py").write_text("def f(x):\n    if x:\n        return 'private'\n")
    monkeypatch.setattr(observatory, "command", lambda *_: subprocess.CompletedProcess(
        [], 0, "one.py\0", "",
    ))
    records = observatory.source_metadata(tmp_path)
    assert records[0]["functions"] == 1
    assert records[0]["decision_nodes"] == 1
    assert len(records[0]["sha256"]) == 64
    assert "private" not in json.dumps(records)


def test_source_path_escape_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(observatory, "command", lambda *_: subprocess.CompletedProcess(
        [], 0, "../outside.py\0", "",
    ))
    with pytest.raises(ValueError, match="regular repository"):
        observatory.source_metadata(tmp_path)


def test_test_runner_failure_is_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(observatory, "command", lambda *_: subprocess.CompletedProcess(
        [], 2, "interrupted", "",
    ))
    result = observatory.collect_tests(tmp_path)
    assert result["status"] == "TEST_RUN_ERROR"
    assert result["exit_code"] == 2 and result["summary"] is None


def test_test_runner_success_without_report_is_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(observatory, "command", lambda *_: subprocess.CompletedProcess(
        [], 0, "", "",
    ))
    with pytest.raises(RuntimeError, match="JUnit report"):
        observatory.collect_tests(tmp_path)


def test_shared_engine_failure_has_no_stale_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(observatory, "command", lambda *_: subprocess.CompletedProcess(
        [], 1, "", "GitHub failed",
    ))
    with pytest.raises(RuntimeError, match="GitHub failed"):
        observatory.collect_shared_github(tmp_path, tmp_path / "github", 20)


def local_metadata(exit_code: int = 0) -> dict[str, Any]:
    return {
        "dependency_check": {"status": "PASSED", "exit_code": 0},
        "tests": {"status": "TEST_FAILURES" if exit_code else "NOT_REQUESTED",
                  "exit_code": exit_code},
        "local_learning": {"status": "NOT_MODELED_LOCAL_METADATA"},
    }


@pytest.mark.parametrize("exit_code", [0, 1])
def test_cli_persists_preview_and_propagates_test_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int,
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("")
    monkeypatch.setattr(observatory, "collect_python_metadata", lambda *_: local_metadata(exit_code))
    assert observatory.main(["--repository-root", str(tmp_path)]) == exit_code
    directory = next((tmp_path / "outputs/python-observatory").iterdir())
    preview = json.loads((directory / "suggestions.json").read_text())
    assert preview["state"] == "PREVIEW_REQUIRES_HUMAN_REVIEW"
    assert preview["github"]["learning_status"] == "NOT_REQUESTED"
    assert (directory / "python.json").is_file()


def test_cli_collection_error_is_saved_and_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("")

    def fail(*_: object) -> dict[str, Any]:
        raise RuntimeError("explicit failure")

    monkeypatch.setattr(observatory, "collect_python_metadata", fail)
    assert observatory.main(["--repository-root", str(tmp_path)]) == 1
    directory = next((tmp_path / "outputs/python-observatory").iterdir())
    assert json.loads((directory / "error.json").read_text())["state"] == "COLLECTION_FAILED"
    assert not (directory / "suggestions.json").exists()
