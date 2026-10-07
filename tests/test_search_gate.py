# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Search Gate cases are supplied fixtures, not newly verified external facts."""

import json
import subprocess
import sys
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path

import jsonschema
import pytest

from vessell.search_gate import (
    ClaimType,
    EvidenceStatus,
    GateStatus,
    LicenseClass,
    SearchRecord,
    check_import,
    classify_license,
    evaluate_claim,
    main,
)
from vessell.validation import load_schema


def record(**changes):
    base = SearchRecord(
        query="safety check",
        tool="code search",
        scope="vessell/*.py",
        result_count=1,
        limit_hit=False,
        primary_source_opened=True,
        status=EvidenceStatus.SOURCE_ESTABLISHED,
        what_was_not_checked="other branches",
        primary_source="vessell/search_gate.py:evaluate_claim",
    )
    return replace(base, **changes)


@pytest.mark.parametrize("kind", list(ClaimType))
def test_no_search_no_claim(kind):
    result = evaluate_claim(kind, [])
    assert result.status is GateStatus.BLOCKED
    assert "No search, no claim" in result.reasons[0]


@pytest.mark.parametrize("kind", list(ClaimType))
def test_primary_source_clears_search_prerequisite_only(kind):
    result = evaluate_claim(kind, [record()])
    assert result.status is GateStatus.CLEARED
    assert any("Harm Gate still apply" in reason for reason in result.reasons)


def test_snapshot_score_and_inaccessible_source_pages_remain_hypothesis():
    summary = record(
        query="NHL score now",
        tool="web search",
        scope="search summaries",
        primary_source_opened=False,
        primary_source="",
        status=EvidenceStatus.WORKING_HYPOTHESIS,
    )
    inaccessible = record(
        scope="NHL primary pages", primary_source_opened=False, status=EvidenceStatus.UNVERIFIED
    )
    result = evaluate_claim(ClaimType.LIVE_FACT, [summary, inaccessible])
    assert result.status is GateStatus.HYPOTHESIS_ONLY
    assert any("WORKING HYPOTHESIS" in reason for reason in result.reasons)


def test_opened_snapshot_is_not_a_final_score():
    result = evaluate_claim(ClaimType.LIVE_FACT, [record()])
    assert any("not a final outcome" in reason for reason in result.reasons)


def test_summary_cannot_upgrade_itself():
    result = evaluate_claim(
        ClaimType.LIVE_FACT,
        [
            record(status=EvidenceStatus.WORKING_HYPOTHESIS),
        ],
    )
    assert result.status is GateStatus.HYPOTHESIS_ONLY


@pytest.mark.parametrize(
    "changes",
    [
        {"primary_source_opened": False},
        {"primary_source": ""},
        {"primary_source": "   "},
    ],
)
def test_established_label_requires_opened_cited_primary(changes):
    result = evaluate_claim(ClaimType.CODE_EXISTENCE, [record(**changes)])
    assert result.status is GateStatus.HYPOTHESIS_ONLY


def test_inaccessible_claude_account_is_unverified():
    result = evaluate_claim(
        ClaimType.PERSONAL_MEMORY,
        [
            record(
                query="past game files",
                scope="Claude account (inaccessible)",
                primary_source_opened=False,
                status=EvidenceStatus.UNVERIFIED,
            ),
        ],
    )
    assert result.status is GateStatus.UNVERIFIED
    assert any("must not be invented" in reason for reason in result.reasons)
    assert any("paste material" in reason for reason in result.reasons)


def test_repo_name_correction_after_failed_direct_lookup():
    failed = record(
        query="Cvessell-create/Vessellframework_Localrebuild",
        scope="GitHub direct repository lookup",
        result_count=0,
        primary_source_opened=False,
        status=EvidenceStatus.UNVERIFIED,
    )
    found = record(
        query="VessellFramework Local Rebuild",
        tool="GitHub repository search",
        scope="cvessell-create repositories",
        primary_source="https://github.com/cvessell-create/VessellFramework_Local_Rebuild",
        corrected_name="cvessell-create/VessellFramework_Local_Rebuild",
    )
    result = evaluate_claim(ClaimType.REPO_IDENTITY, [failed, found])
    assert result.status is GateStatus.CLEARED
    assert any(
        "Corrected repository name: cvessell-create/VessellFramework_Local_Rebuild; "
        "state before writes." == reason
        for reason in result.reasons
    )


def test_code_claim_cites_file_and_reports_cap_and_unchecked_scope():
    result = evaluate_claim(ClaimType.CODE_EXISTENCE, [record(result_count=10, limit_hit=True)])
    assert result.status is GateStatus.CLEARED
    assert any("vessell/search_gate.py:evaluate_claim" in reason for reason in result.reasons)
    assert any("limit hit: 10" in reason for reason in result.reasons)
    assert any("NOT checked: other branches" in reason for reason in result.reasons)


def test_not_found_names_scope_without_claiming_nonexistence():
    result = evaluate_claim(ClaimType.CODE_EXISTENCE, [record(result_count=0)])
    assert result.status is GateStatus.UNVERIFIED
    assert any("NOT FOUND IN SCOPE: vessell/*.py" in reason for reason in result.reasons)
    assert any("absence is not proof" in reason for reason in result.reasons)


def test_derivative_summaries_do_not_count_as_confirmation():
    summary = record(status=EvidenceStatus.WORKING_HYPOTHESIS, primary_source_opened=False)
    result = evaluate_claim(ClaimType.LIVE_FACT, [summary] * 10)
    assert result.status is GateStatus.HYPOTHESIS_ONLY


@pytest.mark.parametrize(
    ("license", "expected"),
    [
        ("MIT", LicenseClass.PERMISSIVE),
        ("Apache-2.0", LicenseClass.PERMISSIVE),
        ("BSD", LicenseClass.PERMISSIVE),
        ("BSD-2-Clause", LicenseClass.PERMISSIVE),
        ("BSD-3-Clause", LicenseClass.PERMISSIVE),
        ("CC-BY-4.0", LicenseClass.ATTRIBUTION),
        ("CC-BY-SA-4.0", LicenseClass.SHARE_ALIKE),
        ("GPL-2.0", LicenseClass.COPYLEFT_CODE),
        ("GPL-2.0(+)", LicenseClass.COPYLEFT_CODE),
        ("GPL-2.0+", LicenseClass.COPYLEFT_CODE),
        ("GPL-2.0-or-later", LicenseClass.COPYLEFT_CODE),
        ("GPL-3.0", LicenseClass.COPYLEFT_CODE),
        ("AGPL", LicenseClass.COPYLEFT_CODE),
        ("AGPL-3.0-or-later", LicenseClass.COPYLEFT_CODE),
        ("proprietary", LicenseClass.PROPRIETARY),
        ("unknown", LicenseClass.PROPRIETARY),
        ("MIT OR proprietary", LicenseClass.PROPRIETARY),
        ("MIT-made-up", LicenseClass.PROPRIETARY),
        ("", LicenseClass.PROPRIETARY),
    ],
)
def test_license_classification(license, expected):
    assert classify_license(license) is expected


def test_wesnoth_code_requires_compatible_project_and_recorded_decision():
    assert check_import("code", "GPL-2.0+", "Apache-2.0").status is GateStatus.BLOCKED
    result = check_import("code", "GPL-2.0+", "GPL-2.0-or-later")
    assert result.status is GateStatus.CLEARED
    assert any("record the licensing decision" in reason for reason in result.reasons)


@pytest.mark.parametrize("kind", ["art", "audio", "data"])
def test_wesnoth_assets_stay_separate_with_attribution(kind):
    result = check_import(kind, "CC-BY-SA-4.0", "Apache-2.0")
    assert result.status is GateStatus.CLEARED
    assert "Attribution required" in result.reasons[0]
    assert "keep assets separate under CC-BY-SA-4.0" in result.reasons[0]


def test_dnd_srd_51_requires_attribution():
    result = check_import("data", "CC-BY-4.0", "Apache-2.0")
    assert result.status is GateStatus.CLEARED
    assert "Attribution required" in result.reasons[0]


@pytest.mark.parametrize("license", ["proprietary", "unknown", "unrecognised", ""])
@pytest.mark.parametrize("kind", ["code", "art", "audio", "data"])
def test_40k_and_unknown_licenses_always_blocked(license, kind):
    assert check_import(kind, license, "GPL-2.0-or-later").status is GateStatus.BLOCKED


@pytest.mark.parametrize(
    ("source", "project", "expected"),
    [
        ("GPL-3.0", "GPL-2.0-only", GateStatus.BLOCKED),
        ("GPL-2.0-only", "GPL-3.0", GateStatus.BLOCKED),
        ("GPL-2.0+", "GPL-3.0", GateStatus.CLEARED),
        ("GPL-3.0", "GPL-3.0-or-later", GateStatus.CLEARED),
        ("AGPL", "GPL-3.0", GateStatus.BLOCKED),
        ("AGPL", "AGPL-3.0-or-later", GateStatus.CLEARED),
        ("GPL-2.0+", "unknown", GateStatus.BLOCKED),
        ("CC-BY-SA-4.0", "Apache-2.0", GateStatus.BLOCKED),
        ("MIT", "Apache-2.0", GateStatus.CLEARED),
        ("Apache-2.0", "GPL-2.0-only", GateStatus.BLOCKED),
        ("Apache License 2.0", "GPL-2.0", GateStatus.BLOCKED),
        ("Apache-2.0", "GPL-3.0", GateStatus.CLEARED),
    ],
)
def test_conservative_import_compatibility(source, project, expected):
    assert check_import("code", source, project).status is expected


def test_apache_code_in_gpl_or_later_requires_recorded_version_selection():
    result = check_import("code", "Apache-2.0", "GPL-2.0-or-later")
    assert result.status is GateStatus.CLEARED
    assert "Select and record GPL-3.0 or later" in result.reasons[0]


def test_records_are_frozen():
    with pytest.raises(FrozenInstanceError):
        record().scope = "different scope"


@pytest.mark.parametrize("status", list(EvidenceStatus))
def test_schema_validates_sample_records(status):
    schema = load_schema("search.record.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(asdict(record(status=status)), schema)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("result_count", -1),
        ("result_count", True),
        ("result_count", "10"),
        ("limit_hit", "false"),
        ("primary_source_opened", 1),
        ("status", "CLEARED"),
        ("query", " "),
        ("scope", ""),
        ("what_was_not_checked", None),
    ],
)
def test_invalid_records_rejected_by_schema_and_runtime(field, value):
    payload = asdict(record())
    payload[field] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, load_schema("search.record.schema.json"))
    with pytest.raises((ValueError, TypeError)):
        SearchRecord(**payload)


@pytest.mark.parametrize(
    ("args", "expected", "exit_code"),
    [
        (["check-license", "CC-BY-4.0", "--json"], "CLEARED", 0),
        (["--json", "check-license", "unknown"], "BLOCKED", 1),
        (["check-import", "code", "GPL-2.0+", "Apache-2.0", "--json"], "BLOCKED", 1),
        (["check-import", "art", "CC-BY-SA-4.0", "Apache-2.0", "--json"], "CLEARED", 0),
    ],
)
def test_cli_json_output(args, expected, exit_code, capsys):
    assert main(args) == exit_code
    assert json.loads(capsys.readouterr().out)["status"] == expected


def test_cli_evaluate_json_file(tmp_path, capsys):
    path = tmp_path / "records.json"
    path.write_text(json.dumps([asdict(record())]), encoding="utf-8")
    assert main(["evaluate", ClaimType.CODE_EXISTENCE.value, str(path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "CLEARED"


@pytest.mark.parametrize("contents", ["{}", "[1]", '[{"bad": true}]', "not JSON"])
def test_cli_malformed_file_fails_closed(contents, tmp_path, capsys):
    path = tmp_path / "records.json"
    path.write_text(contents, encoding="utf-8")
    assert main(["evaluate", ClaimType.LIVE_FACT.value, str(path), "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "BLOCKED"


def test_module_cli_json():
    result = subprocess.run(
        [sys.executable, "-m", "vessell.search_gate", "check-license", "MIT", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["license_class"] == "PERMISSIVE"


def test_packaging_entry_point():
    import tomllib

    import vessell.search_gate as gate

    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["project"]["scripts"]["vf-search-gate"] == "vessell.search_gate:main"
    assert callable(gate.main)


def test_skill_mirror_identical():
    root = Path(__file__).resolve().parents[1]
    assert (root / "SKILL.md").read_bytes() == (
        root / "mnt/skills/user/vessel-framework-analyst/SKILL.md"
    ).read_bytes()
