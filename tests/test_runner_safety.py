import json
from dataclasses import replace
from pathlib import Path

import pytest

import run_live_kev_case
import run_operational_master
from vessell.app import main
from vessell.app.pipeline import run_case_pipeline
from vessell.harm_gate import REQUIRED_FIELDS


@pytest.mark.parametrize("runner", [main, run_live_kev_case, run_operational_master])
@pytest.mark.parametrize("gate_state", ["missing", "uncleared", "cleared"])
def test_runner_harm_gate_exit(runner, gate_state, tmp_path, monkeypatch, capsys) -> None:
    case = json.loads(Path("example_case.json").read_text(encoding="utf-8"))
    case["harm_gate"] = dict.fromkeys(REQUIRED_FIELDS, False)
    case["harm_gate"]["benefit_proportionate"] = gate_state == "cleared"
    result = run_case_pipeline(case, track_provenance=False)
    if gate_state == "missing":
        result = replace(result, harm_gate=None)
    monkeypatch.setattr(runner, "run_case_pipeline", lambda case: result)
    argv = ["runner", "--output-dir", str(tmp_path / "reports")]
    if runner is main:
        source = tmp_path / "case.json"
        source.write_text(json.dumps(case), encoding="utf-8")
        argv.extend(["--input", str(source)])
    else:
        monkeypatch.setattr(runner, "fetch_kev_catalog", dict)
        monkeypatch.setattr(runner, "build_case_from_kev", lambda *args, **kwargs: case)
    if runner is run_operational_master:
        monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: None)
        monkeypatch.setattr(runner, "load_asset_inventory", lambda path: [])
        monkeypatch.setattr(runner, "build_defense_plan", lambda *args: {"matched_action_count": 0})
        monkeypatch.setattr(runner, "write_defense_plan", lambda *args: tmp_path / "plan.json")
    monkeypatch.setattr("sys.argv", argv)
    assert runner.main() == (0 if gate_state == "cleared" else 1)
    output = capsys.readouterr().out
    assert ("RUNNER STATUS: REVIEW REQUIRED (Harm Gate)" in output) == (gate_state != "cleared")


@pytest.mark.parametrize("error", [OSError("unreadable"), TypeError("invalid type"), ValueError("malformed")])
def test_operational_runner_invalid_input_fails_cleanly(error, monkeypatch, capsys) -> None:
    def fail():
        raise error

    monkeypatch.setattr("sys.argv", ["run_operational_master"])
    monkeypatch.setattr(run_operational_master.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_operational_master, "fetch_kev_catalog", fail)
    assert run_operational_master.main() == 1
    assert capsys.readouterr().out == f"RUN FAILED: {error}\n"


@pytest.mark.parametrize(
    ("payload", "status", "message"),
    [
        ("{bad", 1, "unable to read input JSON"),
        ("[]", 2, "invalid case payload"),
        ('{"title": "incomplete"}', 2, "invalid case payload"),
    ],
)
def test_program_invalid_input_fails_cleanly(payload, status, message, tmp_path, monkeypatch, capsys) -> None:
    source = tmp_path / "case.json"
    source.write_text(payload, encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["vf-program", "--input", str(source)])
    assert main.main() == status
    assert capsys.readouterr().out.startswith(f"RUN FAILED: {message}")


@pytest.mark.parametrize("error", [OSError("unwritable"), ValueError("reports do not match")])
def test_program_report_failure_fails_cleanly(error, tmp_path, monkeypatch, capsys) -> None:
    def fail(*args):
        raise error

    monkeypatch.setattr(main, "write_outputs", fail)
    monkeypatch.setattr("sys.argv", ["vf-program", "--input", "example_case.json",
                                    "--output-dir", str(tmp_path)])
    assert main.main() == 2
    assert capsys.readouterr().out == f"RUN FAILED: unable to persist verified reports: {error}\n"
