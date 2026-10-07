import json

import pytest
from jsonschema import Draft202012Validator

from vessell.research_catalog import main, render_catalog, validate_catalog
from vessell.validation import load_schema

QUESTION = "How are work-life support and employee stress associated?"

RECORD = {
    "id": "study-1",
    "citation": "Illustrative test citation",
    "source_type": "EMPIRICAL_STUDY",
    "source_locator": {"kind": "DOI", "value": "10.1234/example.1"},
    "screening_decision": "INCLUDED",
    "source_check_status": "NOT_CHECKED",
    "extraction_basis": "CITATION_ONLY",
    "population_and_setting": "Not extracted",
    "design": "Not extracted",
    "constructs": [],
    "measures": [],
    "outcomes": [],
    "findings_summary": "Not extracted",
    "limitations": ["Not appraised"],
    "applicability_note": "Not assessed",
    "appraisal_status": "NOT_APPRAISED",
}


def test_empty_starter_catalog_is_valid_and_report_states_limits() -> None:
    path = "examples/organizational_psychology_evidence_catalog.json"
    with open(path, encoding="utf-8") as file:
        catalog = json.load(file)
    validate_catalog(catalog)
    report = render_catalog(catalog)
    assert "No sources are cataloged yet." in report
    assert "does not verify" in report
    assert "No employee or participant data belong" in report


def test_catalog_schema_and_record_validation() -> None:
    schema = load_schema("research-evidence-catalog.schema.json")
    Draft202012Validator.check_schema(schema)
    validate_catalog(
        {"catalog_version": 1, "research_question": QUESTION, "records": [RECORD]}
    )


@pytest.mark.parametrize(
    "update",
    [
        {"screening_decision": "EXCLUDED"},
        {"source_locator": {"kind": "DOI", "value": "not-a-doi"}},
        {"appraisal_status": "APPRAISED"},
        {"limitations": []},
        {"source_check_status": "AUTHENTICATED"},
    ],
)
def test_invalid_or_overclaiming_catalog_fields_are_rejected(update: dict) -> None:
    record = {**RECORD, **update}
    with pytest.raises(ValueError):
        validate_catalog(
            {"catalog_version": 1, "research_question": QUESTION, "records": [record]}
        )


def test_duplicate_record_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="IDs must be unique"):
        validate_catalog(
            {
                "catalog_version": 1,
                "research_question": QUESTION,
                "records": [RECORD, dict(RECORD)],
            }
        )


def test_appraised_record_requires_method_and_notes() -> None:
    record = {
        **RECORD,
        "appraisal_status": "APPRAISED",
        "appraisal_method": "Reviewer-selected checklist",
        "appraisal_notes": "Reviewer-entered note",
    }
    catalog = {"catalog_version": 1, "research_question": QUESTION, "records": [record]}
    validate_catalog(catalog)
    report = render_catalog(catalog)
    assert "Reviewer-selected checklist" in report
    assert "Reviewer-entered note" in report


def test_cli_writes_report_only_after_validating_input(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.json"
    output_path = tmp_path / "catalog.md"
    catalog_path.write_text(
        json.dumps({"catalog_version": 1, "research_question": QUESTION, "records": []}),
        encoding="utf-8",
    )
    assert main([str(catalog_path), "--output", str(output_path)]) == 0
    assert "No sources are cataloged yet." in output_path.read_text(encoding="utf-8")

    catalog_path.write_text('{"catalog_version": 0}', encoding="utf-8")
    assert main([str(catalog_path), "--output", str(output_path)]) == 1
    assert "No sources are cataloged yet." in output_path.read_text(encoding="utf-8")


def test_cli_refuses_to_overwrite_catalog_with_report(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.json"
    original = json.dumps(
        {"catalog_version": 1, "research_question": QUESTION, "records": []}
    )
    catalog_path.write_text(original, encoding="utf-8")
    assert main([str(catalog_path), "--output", str(catalog_path)]) == 1
    assert catalog_path.read_text(encoding="utf-8") == original
