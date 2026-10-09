"""Read-only Python metadata with the shared R GitHub learning engine."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

SCHEMA_VERSION = 1


class TestRecord(TypedDict):
    test_id: str
    outcome: str
    seconds: float


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def command(root: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments, cwd=root, check=False, text=True, capture_output=True, timeout=1200,
    )


def git_metadata(root: Path) -> dict[str, Any]:
    revision = command(root, ["git", "rev-parse", "HEAD"])
    status = command(root, ["git", "status", "--porcelain"])
    if revision.returncode or status.returncode:
        raise RuntimeError(f"Git metadata failed: {revision.stderr}{status.stderr}")
    return {"revision": revision.stdout.strip(), "working_tree_clean": not status.stdout.strip()}


def source_metadata(root: Path) -> list[dict[str, Any]]:
    result = command(root, ["git", "ls-files", "-z", "--", "*.py"])
    if result.returncode:
        raise RuntimeError(f"Tracked source listing failed: {result.stderr}")
    records = []
    for relative in sorted(filter(None, result.stdout.split("\0"))):
        path = root / relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Expected a regular repository source file: {relative}")
        content = path.read_bytes()
        tree = ast.parse(content, filename=relative)
        nodes = list(ast.walk(tree))
        records.append({
            "path": relative,
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
            "physical_lines": len(content.splitlines()),
            "functions": sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in nodes),
            "classes": sum(isinstance(n, ast.ClassDef) for n in nodes),
            "decision_nodes": sum(
                isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.ExceptHandler))
                for n in nodes
            ),
        })
    return records


def package_metadata() -> list[dict[str, str]]:
    return sorted(
        (
            {"name": distribution.metadata["Name"], "version": distribution.version}
            for distribution in importlib.metadata.distributions()
            if distribution.metadata["Name"]
        ),
        key=lambda package: (package["name"].lower(), package["version"]),
    )


def summarize_junit(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    if root.tag not in {"testsuites", "testsuite"}:
        raise ValueError("Expected a pytest JUnit testsuite(s) document.")
    records: list[TestRecord] = []
    for testcase in root.iter("testcase"):
        identity = "\0".join((
            testcase.get("classname", ""), testcase.get("name", ""),
        ))
        if not identity.strip("\0"):
            raise ValueError("JUnit testcase has no identity.")
        raw_duration = testcase.get("time")
        if raw_duration is None:
            raise ValueError("JUnit testcase is missing its duration.")
        duration = float(raw_duration)
        if duration < 0 or not (duration < float("inf")):
            raise ValueError("JUnit duration must be finite and nonnegative.")
        outcome = "passed"
        for tag in ("skipped", "failure", "error"):
            if testcase.find(tag) is not None:
                outcome = {"skipped": "skipped", "failure": "failed", "error": "error"}[tag]
        records.append({
            "test_id": hashlib.sha256(identity.encode()).hexdigest(),
            "outcome": outcome, "seconds": duration,
        })
    counts = {outcome: sum(r["outcome"] == outcome for r in records)
              for outcome in ("passed", "failed", "error", "skipped")}
    evaluated = counts["passed"] + counts["failed"] + counts["error"]
    durations = sorted(r["seconds"] for r in records)
    position = 0.95 * (len(durations) - 1) if durations else 0
    lower = int(position)
    upper = min(lower + 1, len(durations) - 1)
    p95 = (durations[lower] + (position - lower) * (durations[upper] - durations[lower])
           if durations else None)
    return {
        "records": records, "counts": counts, "evaluated": evaluated,
        "failure_fraction": (counts["failed"] + counts["error"]) / evaluated
        if evaluated else None,
        "median_seconds": statistics.median(durations) if durations else None,
        "p95_seconds": p95,
    }


def collect_tests(root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="vessell-observatory-") as directory:
        report = Path(directory) / "tests.xml"
        started = time.perf_counter()
        result = command(root, [
            sys.executable, "-m", "pytest", "-q", f"--junitxml={report}",
        ])
        elapsed = time.perf_counter() - started
        if result.returncode == 0 and not report.exists():
            raise RuntimeError("Successful pytest invocation did not write its JUnit report.")
        summary = summarize_junit(report) if report.exists() else None
    if result.returncode:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    return {
        "status": "PASSED" if result.returncode == 0 else
        "TEST_FAILURES" if result.returncode == 1 else "TEST_RUN_ERROR",
        "exit_code": result.returncode, "wall_seconds": elapsed, "summary": summary,
    }


def collect_python_metadata(root: Path, run_tests: bool) -> dict[str, Any]:
    pip_check = command(root, [sys.executable, "-m", "pip", "check"])
    if pip_check.returncode:
        print(pip_check.stdout, file=sys.stderr)
        print(pip_check.stderr, file=sys.stderr)
    return {
        "schema_version": SCHEMA_VERSION,
        "collected_at": datetime.now(UTC).isoformat(),
        "source": git_metadata(root),
        "runtime": {
            "python_version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "os_family": platform.system(),
            "machine": platform.machine(),
        },
        "packages": package_metadata(),
        "dependency_check": {
            "status": "PASSED" if pip_check.returncode == 0 else "CHECK_FAILED",
            "exit_code": pip_check.returncode,
        },
        "source_files": source_metadata(root),
        "tests": collect_tests(root) if run_tests else {"status": "NOT_REQUESTED", "exit_code": 0},
        "local_learning": {
            "status": "NOT_MODELED_LOCAL_METADATA",
            "reason": "One environment snapshot is not a labeled, varied training dataset.",
        },
    }


def collect_shared_github(root: Path, output: Path, max_pages: int) -> dict[str, Any]:
    result = command(root, [
        "Rscript", "r/run_github_observatory.R", str(output), str(max_pages),
    ])
    if result.returncode:
        raise RuntimeError(f"GitHub/R collection failed:\n{result.stdout}\n{result.stderr}")
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    directories = list(output.iterdir())
    if len(directories) != 1 or not directories[0].is_dir():
        raise RuntimeError("Expected one new shared GitHub/R output directory.")
    directory = directories[0]
    learning = json.loads((directory / "learning.json").read_text(encoding="utf-8"))
    preview = json.loads((directory / "suggestions.json").read_text(encoding="utf-8"))
    return {
        "directory": str(directory),
        "learning_status": learning["status"],
        "scores": learning.get("scores"),
        "suggestions": preview["suggestions"],
        "collection_status": preview["collection_status"],
    }


def python_suggestions(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    if metadata["dependency_check"]["status"] != "PASSED":
        suggestions.append({
            "kind": "REVIEW_DEPENDENCIES",
            "suggestion": "Inspect the explicit pip-check failure before changing dependencies.",
            "evidence": "python.json#/dependency_check",
        })
    tests = metadata["tests"]
    if tests["status"] in {"TEST_FAILURES", "TEST_RUN_ERROR"}:
        suggestions.append({
            "kind": "REVIEW_TEST_FAILURES",
            "suggestion": "Review the failed test run; failure is not evidence of a particular cause.",
            "evidence": "python.json#/tests",
        })
    if tests.get("summary") and tests["summary"]["records"]:
        slowest = sorted(tests["summary"]["records"], key=lambda r: r["seconds"], reverse=True)[:5]
        suggestions.append({
            "kind": "REVIEW_TEST_COST",
            "suggestion": "Profile these observed slow tests before proposing performance changes.",
            "test_ids": [r["test_id"] for r in slowest],
            "evidence": "python.json#/tests/summary",
        })
    suggestions.append({
        "kind": "REVIEW_LOCAL_DATA_LIMIT",
        "suggestion": "Do not train a local-environment predictor from one snapshot or infer code quality "
                      "from source size/decision counts. More varied, labeled history is needed.",
        "evidence": "python.json#/local_learning",
    })
    return suggestions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path, default=Path("outputs/python-observatory"))
    parser.add_argument("--github", action="store_true", help="Run the shared R GitHub learning engine.")
    parser.add_argument("--run-tests", action="store_true", help="Run repository pytest and collect timings.")
    parser.add_argument("--max-pages", type=int, default=20)
    arguments = parser.parse_args(argv)
    root = arguments.repository_root.resolve()
    if not (root / "pyproject.toml").is_file() or not (root / ".git").exists():
        parser.error("repository-root must be a source Git checkout, not an installed package directory.")
    if not 1 <= arguments.max_pages <= 100:
        parser.error("max-pages must be from 1 to 100.")
    output_root = arguments.output_root
    if not output_root.is_absolute():
        output_root = root / output_root
    directory = output_root / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:12]
    )
    directory.mkdir(parents=True, exist_ok=False)
    try:
        metadata = collect_python_metadata(root, arguments.run_tests)
        write_json(directory / "python.json", metadata)
        suggestions = python_suggestions(metadata)
        shared = collect_shared_github(root, directory / "github", arguments.max_pages) \
            if arguments.github else {"learning_status": "NOT_REQUESTED"}
        preview = {
            "state": "PREVIEW_REQUIRES_HUMAN_REVIEW",
            "python_suggestions": suggestions, "github": shared,
            "limits": [
                "Current interpreter environment and tracked repository Python files only.",
                "No environment variables, hostname, user ID, dependency URLs, source text or raw logs saved.",
                "Test identities are hashed; hashes are identifiers, not guarantees of anonymity.",
                "No automatic source changes, approvals, report release or execution authority.",
            ],
        }
        write_json(directory / "suggestions.json", preview)
        lines = [
            "# Python and GitHub observatory: human-review preview", "",
            f"Python tests: {metadata['tests']['status']}",
            f"Dependency check: {metadata['dependency_check']['status']}",
            f"GitHub learning: {shared['learning_status']}", "",
            "No automated code changes or framework report release permitted.", "",
        ]
        for suggestion in suggestions:
            lines.extend([f"## {suggestion['kind']}", suggestion["suggestion"],
                          f"Evidence: {suggestion['evidence']}", ""])
        if arguments.github:
            github_directory = Path(shared["directory"]).relative_to(directory)
            lines.extend([
                "## Shared GitHub learning and evidence",
                f"[GitHub review preview]({github_directory.as_posix()}/review-preview.md)",
                f"[Held-out model metrics]({github_directory.as_posix()}/learning.json)", "",
            ])
        lines.extend(["## Limits", *preview["limits"]])
        (directory / "review-preview.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Saved Python observatory preview to: {directory}")
        return 1 if (metadata["tests"]["exit_code"] or
                     metadata["dependency_check"]["exit_code"]) else 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, ET.ParseError) as error:
        write_json(directory / "error.json", {
            "state": "COLLECTION_FAILED", "error": str(error),
            "collected_at": datetime.now(UTC).isoformat(),
        })
        print(f"Observatory failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
