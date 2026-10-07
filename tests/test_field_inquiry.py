import copy
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from vessell.ambient.api import Settings, create_app
from vessell.ambient.models import AmbientEvent, FieldInquiryAction, FilingAction
from vessell.ambient.specialist import SpecialistTask
from vessell.ambient.store import Conflict, Store, canonical, digest
from vessell.app.pipeline import run_case_pipeline
from vessell.app.reporting import render_markdown_report
from vessell.field_inquiry import PILLARS, InvalidFieldInquiry, assess_field_inquiry, field_template
from vessell.validation import validate_record

ROOT = Path(__file__).parents[1]


@pytest.fixture
def awaiting(tmp_path):
    store = Store(tmp_path / "field.sqlite")
    event = AmbientEvent.model_validate_json(
        (ROOT / "case_studies/ambient/event.json").read_text(),
    )
    job, _ = store.ingest("manual", event)
    assert store.work_once()
    return store, store.get(job["id"])


def complete(store, job, assessment, version=0):
    return store.complete_field_inquiry(job["id"], FieldInquiryAction(
        expected_version=job["version"], expected_field_version=version, assessment=assessment,
    ), "synthetic-human-reviewer")


def test_missing_and_blank_scaffold_never_imply_completion():
    result = assess_field_inquiry(None, {"external-event"})
    assert result.status == "MISSING" and result.assessment is None
    assert result.human_completion_required
    assert not result.validates_experience and not result.grants_authority
    assert PILLARS[-1] == "KNOWING FIELD" and len(PILLARS) == 5
    with pytest.raises(InvalidFieldInquiry):
        assess_field_inquiry(field_template(["external-event"]), {"external-event"})


def test_canonical_size_threshold_and_unicode_are_measured_exactly(field_assessment):
    size = len(canonical(field_assessment).encode())
    remaining = 32768 - size
    extra = []
    while remaining:
        added = min(2003, remaining)
        if remaining - added in (1, 2, 3):
            added -= 4
        assert added >= 4
        extra.append("x" * (added - 3))
        remaining -= added
    field_assessment["blind_spots"].extend(extra[:11])
    field_assessment["alternatives"].extend(extra[11:])
    assert len(canonical(field_assessment).encode()) == 32768
    assert assess_field_inquiry(field_assessment, {"external-event"}).status == "DOCUMENTED_UNREVIEWED"
    field_assessment["limitations"][0] += "x"
    with pytest.raises(InvalidFieldInquiry, match="32 KiB"):
        assess_field_inquiry(field_assessment, {"external-event"})
    field_assessment["limitations"][0] = field_assessment["limitations"][0][:-1]
    field_assessment["blind_spots"][-1] = "\u00e9" + field_assessment["blind_spots"][-1][1:]
    with pytest.raises(InvalidFieldInquiry, match="32 KiB"):
        assess_field_inquiry(field_assessment, {"external-event"})


@pytest.mark.parametrize("mutation", [
    "blank", "missing", "unknown", "duplicate-party", "duplicate-evidence", "extra",
    "invalid-participation", "sparse", "oversize", "non-object",
])
def test_assessment_rejects_invalid_records(field_assessment, mutation):
    if mutation == "blank":
        field_assessment["dissent"] = " \t\n "
    elif mutation == "missing":
        del field_assessment["fourth_person"]
    elif mutation == "unknown":
        field_assessment["evidence_ids"] = ["fabricated-root"]
    elif mutation == "duplicate-party":
        field_assessment["affected_parties"].append(field_assessment["affected_parties"][0])
    elif mutation == "duplicate-evidence":
        field_assessment["evidence_ids"] *= 2
    elif mutation == "extra":
        field_assessment["human_completed"] = True
    elif mutation == "invalid-participation":
        field_assessment["affected_parties"][0]["participation"] = "mandatory"
    elif mutation == "sparse":
        field_assessment["affected_parties"] = []
    elif mutation == "oversize":
        field_assessment["blind_spots"] = ["x" * 2000] * 12
        field_assessment["alternatives"] = ["x" * 2000] * 12
    else:
        field_assessment = []
    with pytest.raises(InvalidFieldInquiry):
        assess_field_inquiry(field_assessment, {"external-event"})


def test_valid_context_preserves_decline_dissent_and_source_independence(field_assessment):
    case = json.loads((ROOT / "tests/fixtures/benchmark_cases/repeated_reporting_case.json").read_text())
    baseline = run_case_pipeline(case, track_provenance=False)
    field_assessment["evidence_ids"] = [case["evidence"][0]["source_id"]]
    case["field_inquiry"] = field_assessment
    case["domain"] = "Synthetic provenance test"
    validate_record(case, "case.schema.json")
    result = run_case_pipeline(case, track_provenance=False)
    assert result.field_inquiry.status == "DOCUMENTED_UNREVIEWED"
    assert result.pillars == PILLARS
    assert result.counts == baseline.counts and result.confidence_ceiling == baseline.confidence_ceiling
    assert result.field_inquiry.assessment["affected_parties"][1]["participation"] == "declined"
    assert result.field_inquiry.assessment["dissent"] == field_assessment["dissent"]
    field_assessment["dissent"] = "Changed caller object"
    assert result.field_inquiry.assessment["dissent"] != field_assessment["dissent"]
    text = render_markdown_report(replace(result, harm_gate=None))
    assert "## Knowing Field: Fifth Pillar" in text
    assert "PREVIEW_REQUIRES_HUMAN_FIELD_COMPLETION" in text
    assert text.index("UNKNOWN: no Harm Gate") < text.index("## Knowing Field")


def test_specialist_context_is_not_human_completion(awaiting, field_assessment):
    store, _ = awaiting
    field_assessment["evidence_ids"] = ["reported-event"]
    task = SpecialistTask.model_validate_json(json.dumps({
        "task_id": "synthetic-caller-field", "caller": "synthetic-agent",
        "timestamp": "2026-10-07T12:00:00Z", "question": "What is missing?",
        "evidence": [{"source_id": "reported-event", "description": "An unverified event."}],
        "field_inquiry": field_assessment,
    }))
    job, _ = store.ingest("agent", task.event())
    assert store.work_once()
    job = store.get(job["id"])
    assert job["preview"]["pipeline"]["field_inquiry"]["status"] == "DOCUMENTED_UNREVIEWED"
    assert job["field_review"]["status"] == "MISSING"
    with pytest.raises(Conflict, match="Knowing Field"):
        store.action(job["id"], "approve", "human", "Not self-completed", job["version"], 1)


def test_completion_release_binding_restart_and_independent_filing(awaiting, field_assessment):
    store, job = awaiting
    with pytest.raises(Conflict, match="Knowing Field"):
        store.action(job["id"], "approve", "human", "No inquiry", job["version"])
    changed = complete(store, job, field_assessment)
    assert changed["field_review"]["status"] == "HUMAN_COMPLETED"
    for key in ("event", "version", "preview", "history", "filing"):
        assert changed[key] == job[key]
    changed = Store(store.path).get(job["id"])
    assert changed["field_review"]["assessment"] == field_assessment
    filed = store.file(job["id"], FilingAction(expected_version=0, folder="archive"), "human")
    assert filed["field_review"] == changed["field_review"]
    with pytest.raises(Conflict):
        complete(store, job, field_assessment)
    for stale in (None, 0, 2):
        with pytest.raises(Conflict, match="Knowing Field"):
            store.action(job["id"], "approve", "human", "Stale inquiry", job["version"], stale)
    approved = store.action(job["id"], "approve", "human", "Bounded test release", job["version"], 1)
    selected_hash = approved["field_review"]["history"][-1]["hash"]
    assert approved["history"][-1]["field_review_hash"] == selected_hash
    with pytest.raises(Conflict):
        complete(store, approved, field_assessment, 1)
    assert Store(store.path).work_once()
    released = Store(store.path).get(job["id"])
    assert released["state"] == "COMPLETED"
    assert all(record["field_review_hash"] == selected_hash for record in released["history"][3:])
    assert released["result"] == job["preview"]
    assert released["field_review"]["assessment"] == field_assessment


def test_competing_completions_have_one_winner(awaiting, field_assessment):
    store, job = awaiting

    def submit(_):
        try:
            complete(store, job, field_assessment)
            return "completed"
        except Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(submit, range(2)))
    assert sorted(result) == ["completed", "conflict"]
    assert store.get(job["id"])["field_review"]["version"] == 1
    revised = copy.deepcopy(field_assessment)
    revised["dissent"] = "Explicit alternative preserved on revision."
    update = complete(store, job, revised, 1)
    assert update["field_review"]["history"][1]["previous_hash"] == update["field_review"]["history"][0]["hash"]
    with pytest.raises(Conflict):
        store.action(job["id"], "approve", "human", "Old assessment", job["version"], 1)


@pytest.mark.parametrize("tamper", ["hash", "preview", "invalid-schema", "deleted", "replace-bound-assessment", "append-after-approval"])
def test_tamper_is_integrity_failure_not_invalid_input(awaiting, field_assessment, tamper):
    store, job = awaiting
    complete(store, job, field_assessment)
    if tamper in ("deleted", "replace-bound-assessment", "append-after-approval"):
        store.action(job["id"], "approve", "human", "Bound assessment", job["version"], 1)
    with store.connection() as db:
        record = json.loads(db.execute("SELECT payload FROM ambient_field_reviews").fetchone()[0])
        if tamper == "hash":
            db.execute("UPDATE ambient_field_reviews SET hash='bad'")
        elif tamper == "deleted":
            db.execute("DELETE FROM ambient_field_reviews")
        elif tamper == "append-after-approval":
            previous_hash = digest(canonical(record))
            record.update(version=2, previous_hash=previous_hash)
            record["assessment"]["dissent"] = "A forged completion revision appended after approval."
            payload = canonical(record)
            db.execute(
                "INSERT INTO ambient_field_reviews(job_id,version,payload,hash) VALUES(?,2,?,?)",
                (job["id"], payload, digest(payload)),
            )
        else:
            if tamper == "preview":
                record["preview_hash"] = digest("wrong preview")
            elif tamper == "invalid-schema":
                record["assessment"]["dissent"] = ""
            else:
                record["assessment"]["dissent"] = "Replaced after approval, even with a recomputed review hash."
            payload = canonical(record)
            db.execute("UPDATE ambient_field_reviews SET payload=?,hash=?", (payload, digest(payload)))
    with pytest.raises(ValueError) as caught:
        store.get(job["id"])
    assert not isinstance(caught.value, InvalidFieldInquiry)


def test_legacy_approved_returns_to_review_and_historical_release_is_preserved(awaiting):
    store, job = awaiting
    with store.connection() as db:
        store._append(db, job["id"], "APPROVED", "legacy-human", "Historical approval without inquiry")
    assert store.work_once()
    restored = store.get(job["id"])
    assert restored["state"] == "AWAITING_APPROVAL" and restored["result"] is None
    assert "Release policy requires" in restored["history"][-1]["reason"]
    with store.connection() as db:
        store._append(db, job["id"], "APPROVED", "legacy-human", "Synthetic historical setup")
        store._append(db, job["id"], "RUNNING", "worker", "Synthetic historical setup")
        db.execute("UPDATE ambient_jobs SET result_json=preview_json WHERE id=?", (job["id"],))
        store._append(db, job["id"], "COMPLETED", "worker", "Synthetic historical setup")
    historical = store.get(job["id"])
    assert historical["field_review"]["status"] == "LEGACY_UNASSESSED"
    assert not Store(store.path).work_once()
    assert Store(store.path).get(job["id"]) == historical


def test_completion_cannot_bypass_harm_gate(tmp_path, field_assessment, monkeypatch):
    from vessell.ambient import store as module

    analyze = module.analyze

    def blocked(event):
        preview = analyze(event)
        preview["pipeline"]["harm_gate"]["cleared"] = False
        return preview

    monkeypatch.setattr(module, "analyze", blocked)
    store = Store(tmp_path / "blocked.sqlite")
    job, _ = store.ingest("manual", AmbientEvent.model_validate_json(
        (ROOT / "case_studies/ambient/event.json").read_text(),
    ))
    store.work_once()
    job = store.get(job["id"])
    complete(store, job, field_assessment)
    with pytest.raises(Conflict, match="Harm Gate"):
        store.action(job["id"], "approve", "human", "Not a waiver", job["version"], 1)
    assert store.action(job["id"], "reject", "human", "Harm remains", job["version"])["state"] == "REJECTED"


def test_api_permissions_schema_and_concurrency(awaiting, field_assessment):
    store, job = awaiting
    settings = Settings(store.path, "admin-synthetic-secret-" * 3, "ingest-synthetic-secret-" * 3,
                        reviewer_identity="server-configured-human")
    with TestClient(create_app(settings)) as client:
        path = f"/api/v1/jobs/{job['id']}/field-inquiry"
        payload = {"expected_version": job["version"], "expected_field_version": 0,
                   "assessment": field_assessment}
        admin = {"Authorization": f"Bearer {settings.admin_token}"}
        ingest = {"Authorization": f"Bearer {settings.ingest_token}"}
        assert client.post(path, json=payload).status_code == 401
        assert client.post(path, json=payload, headers=ingest).status_code == 401
        assert client.post(path, json={**payload, "actor": "spoof"}, headers=admin).status_code == 422
        assert client.post(path, json={**payload, "assessment": {}}, headers=admin).status_code == 422
        assert client.post(path, content="x" * (64 * 1024 + 1), headers=admin).status_code == 413
        response = client.post(path, json=payload, headers=admin)
        assert response.status_code == 200
        assert response.json()["field_review"]["history"][-1]["actor"] == settings.reviewer_identity
        assert client.post(path, json=payload, headers=admin).status_code == 409
        assert client.post(path, json={**payload, "expected_version": 0}, headers=admin).status_code == 409
    changes = store.changes(0)
    assert len(changes) == 4 and len({record["seq"] for record in changes}) == 4


def test_agent_action_shape_never_accepts_completed_assertion(field_assessment):
    with pytest.raises(ValidationError):
        FieldInquiryAction.model_validate({
            "expected_version": True, "expected_field_version": 0, "assessment": field_assessment,
        })


def test_model_instructions_include_new_skills_and_unreleased_boundary():
    import vesselframework_agent as agent

    instructions = agent.read_instructions()
    assert "=== KNOWING FIELD THEORY ===" in instructions
    assert "=== COMBINED FIFTH PILLAR ===" in instructions
    assert "Do not simulate embodied presencing" in instructions


def test_model_instructions_include_exact_scientific_skill_and_evidence_limits():
    import vesselframework_agent as agent

    instructions = agent.read_instructions()
    assert "=== SCIENTIFIC EVIDENCE SKILL ===" in instructions
    assert (ROOT / "VesselFramework_Scientific_Evidence_SKILL_v0.1.md").read_text() in instructions
    assert "A digest does not prove truth, validate the whole theory or earn crypto." in instructions
    assert "prospective comparative evidence rather than software pass counts alone" in instructions


def test_model_instructions_fail_explicitly_if_scientific_skill_is_missing(tmp_path, monkeypatch):
    import vesselframework_agent as agent

    monkeypatch.setattr(agent, "SCIENTIFIC_EVIDENCE_FILE", tmp_path / "missing.md")
    with pytest.raises(FileNotFoundError):
        agent.read_instructions()


def test_compatibility_runner_uses_shared_inquiry_contract(field_assessment):
    import vesselframework_case_runner as runner

    case = json.loads((ROOT / "example_case.json").read_text())
    field_assessment["evidence_ids"] = [case["evidence"][0]["source_id"]]
    case["field_inquiry"] = field_assessment
    report, _ = runner.markdown_report(case, runner.load_reference_module())
    assert "DOCUMENTED_UNREVIEWED" in report
    assert "PREVIEW_REQUIRES_HUMAN_FIELD_COMPLETION" in report
    assert "Analytical pillars:" in report and "KNOWING FIELD" in report
    case["field_inquiry"]["evidence_ids"] = ["invented-source"]
    with pytest.raises(InvalidFieldInquiry, match="unknown evidence"):
        runner.markdown_report(case, runner.load_reference_module())
