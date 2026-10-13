import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaValidationError
from pydantic import ValidationError

from vessell import hosted_agent as agent

ROOT = Path(__file__).parents[1]


def request(operation="evidence-analysis"):
    value = json.loads((ROOT / "examples/hosted-agent-evidence.json").read_text())
    value["operation"] = operation
    if operation in ("claim-analysis", "spread-analysis"):
        value["payload"] = {
            "claim": "Synthetic example only",
            "sightings": [{"source_name": "synthetic report", "text": "Example only"}],
        }
    elif operation == "job-analysis":
        value["payload"] = {"postings": [{
            "title": "Example role", "employer": "Synthetic employer",
            "location": "Synthetic city", "description_text": "Example only",
            "source": "synthetic listing",
        }]}
    elif operation == "reference-search":
        value["payload"] = {"query": "human release", "limit": 5}
    return value


def run(value):
    return agent.run_request(json.dumps(value).encode())


@pytest.mark.parametrize("operation", [
    "evidence-analysis", "claim-analysis", "spread-analysis", "job-analysis", "reference-search",
])
def test_all_operations_have_unreleased_result_contract(operation):
    value = request(operation)
    result = run(value)
    output = result.model_dump(mode="json")
    assert result.state == "UNRELEASED_PREVIEW"
    assert result.analysis_only is True
    assert result.report_released is False
    assert result.execution_authorized is False
    assert result.human_field_completion_required is True
    assert result.human_release_required is True
    assert result.execution is None
    assert result.input_standing == "WORKING HYPOTHESIS"
    assert result.external_claim_state.endswith("UNVERIFIED EXTERNAL CLAIM")
    Draft202012Validator(agent.PreviewResult.model_json_schema()).validate(output)
    Draft202012Validator(agent.REQUEST_ADAPTER.json_schema()).validate(value)
    assert result.preview_sha256 == agent.digest(agent.canonical(result.preview))
    assert run(value) == result


def test_existing_evidence_kernel_keeps_ceiling_and_missing_pillars():
    result = run(request()).preview["pipeline"]
    assert result["confidence_ceiling"] == "VERY LOW"
    assert result["counts"]["source_established"] == 0
    assert result["counts"]["working_hypothesis"] == 2
    assert result["field_inquiry"]["status"] == "MISSING"
    assert result["game_theory"]["status"] == "NOT_SUPPLIED"


def test_optional_synthetic_game_is_preserved_without_authority():
    case = json.loads((ROOT / "examples/game-theory-case.json").read_text())
    task = request()
    task["payload"]["evidence"] = [
        {key: row[key] for key in ("source_id", "description")} for row in case["evidence"]
    ]
    task["payload"]["game_theory"] = case["game_theory"]
    result = run(task)
    assert result.preview["pipeline"]["game_theory"]["status"] == "COMPUTED_CONDITIONAL"
    assert result.preview["pipeline"]["confidence_ceiling"] == "VERY LOW"
    assert result.report_released is result.execution_authorized is False


def test_existing_synthetic_field_context_cannot_release_preview(field_assessment):
    task = request()
    task["payload"]["evidence"] = [
        {"source_id": "external-event", "description": "Synthetic regression fixture only"},
    ]
    task["payload"]["field_inquiry"] = field_assessment
    result = run(task)
    field = result.preview["pipeline"]["field_inquiry"]
    assert field["status"] == "DOCUMENTED_UNREVIEWED"
    assert field["assessment"] == field_assessment
    assert result.human_field_completion_required is True
    assert result.report_released is False


@pytest.mark.parametrize("field,value", [
    ("contract_version", "2.0"), ("request_id", "not-a-uuid"),
    ("request_id", "5A7F6360-6504-4CB8-9512-86C13E788228"),
    ("data_classification", "private"), ("data_classification", True),
    ("operation", "execute"), ("approved", True), ("release", True),
])
def test_rejects_unknown_contracts_fields_and_authority(field, value):
    task = request()
    task[field] = value
    with pytest.raises((ValueError, ValidationError)):
        run(task)


@pytest.mark.parametrize("field,value", [
    ("timestamp", "2026-10-09T12:00:00"), ("timestamp", "2026-02-30T12:00:00Z"),
    ("evidence", []), ("question", " "),
    ("field_inquiry", {"status": "COMPLETE"}),
    ("game_theory", {"kind": "invented"}),
    ("approved", True),
])
def test_specialist_payload_validation_is_not_bypassed(field, value):
    task = request()
    task["payload"][field] = value
    with pytest.raises((ValueError, TypeError, ValidationError)):
        run(task)


def test_duplicate_evidence_ids_and_size_limits():
    task = request()
    task["payload"]["evidence"][1]["source_id"] = "illustrative-report"
    with pytest.raises(ValueError):
        run(task)
    task = request()
    task["payload"]["evidence"] *= 13
    with pytest.raises(ValueError):
        run(task)
    with pytest.raises(ValueError, match="32768"):
        agent.run_request(b" " * 32769)
    valid = json.dumps(request()).encode()
    assert agent.run_request(valid + b" " * (32768 - len(valid))).state == "UNRELEASED_PREVIEW"
    task = request()
    task["payload"]["evidence"] = [
        {"source_id": f"synthetic-{number}", "description": "Synthetic example only"}
        for number in range(24)
    ]
    assert run(task).preview["pipeline"]["counts"]["total_evidence"] == 24


@pytest.mark.parametrize("raw", [
    b'{"operation":"reference-search","operation":"evidence-analysis"}',
    b'{"nested":{"x":1,"x":2}}', b'{"x":NaN}', b'{"x":Infinity}', b"not-json",
])
def test_ambiguous_or_invalid_json_is_rejected(raw):
    with pytest.raises(ValueError):
        agent.run_request(raw)


@pytest.mark.parametrize("patch", [
    {"tier": "SOURCE-ESTABLISHED"}, {"tier": "FRAMEWORK SYNTHESIS"},
    {"tier": "ILLUSTRATIVE"}, {"is_official_record": True},
    {"denies": "false"}, {"seen_at": "2026-02-30"}, {"approved": True},
])
def test_sighting_authority_dates_and_types_are_rejected(patch):
    task = request("claim-analysis")
    task["payload"]["sightings"][0].update(patch)
    with pytest.raises(ValueError):
        run(task)
    if "tier" in patch or "is_official_record" in patch:
        with pytest.raises(SchemaValidationError):
            Draft202012Validator(agent.REQUEST_ADAPTER.json_schema()).validate(task)


def test_claim_and_job_collection_bounds_and_role_identity():
    for operation, name in (("claim-analysis", "sightings"), ("job-analysis", "postings")):
        task = request(operation)
        task["payload"][name] *= 25
        with pytest.raises(ValueError):
            run(task)
        task["payload"][name] = []
        with pytest.raises(ValueError):
            run(task)
    task = request("job-analysis")
    other = copy.deepcopy(task["payload"]["postings"][0])
    other["employer"] = "Different employer"
    task["payload"]["postings"].append(other)
    with pytest.raises(ValueError, match="one employer"):
        run(task)


@pytest.mark.parametrize("payload", [
    {"query": " "}, {"query": "!!!"}, {"query": "x" * 201},
    {"query": "rights", "limit": 0}, {"query": "rights", "limit": 11},
    {"query": "rights", "limit": "5"}, {"query": "rights", "limit": True},
    {"query": "rights", "path": "../../private"},
])
def test_search_rejects_unbounded_and_arbitrary_scopes(payload):
    task = request("reference-search")
    task["payload"] = payload
    with pytest.raises(ValueError):
        run(task)


def test_search_shape_counts_citations_and_absence_limits():
    task = request("reference-search")
    task["payload"] = {"query": "human", "limit": 1}
    result = run(task).preview
    assert result["document_count"] == 12
    assert result["scope"] == list(agent.REFERENCE_PATHS)
    assert result["total_matches"] > 1
    assert result["result_count"] == 1
    assert result["limit_hit"] is True
    hit = result["results"][0]
    data = (ROOT / hit["path"]).read_bytes()
    assert hit["source_sha256"] == agent.digest(data)
    assert hit["snippet"] == data.decode().splitlines()[hit["line"] - 1][:1000]
    assert hit["url"].endswith(f"{hit['path']}#L{hit['line']}")
    task["payload"]["query"] = "zznotfoundinscopezz"
    result = run(task).preview
    assert result["status"] == "NOT FOUND IN SCOPE"
    assert result["results"] == []
    assert result["total_matches"] == result["result_count"] == 0
    assert result["limit_hit"] is False
    assert result["what_was_not_checked"]


def test_generated_discovery_and_reference_snapshots_are_current():
    index = ROOT / "docs/agent-reference-index.json"
    capabilities = ROOT / "docs/agent-capabilities.json"
    assert index.read_bytes() == agent.canonical(agent.build_index(ROOT))
    assert capabilities.read_bytes() == agent.canonical(agent.discovery(ROOT))
    descriptor = json.loads(capabilities.read_bytes())
    assert descriptor["reference_index_sha256"] == agent.digest(index.read_bytes())
    assert descriptor["deployment_status"] == "NOT_VERIFIED"
    assert descriptor["anonymous_api"] is descriptor["private_family_intake"] is False
    Draft202012Validator.check_schema(descriptor["input_schema"])
    Draft202012Validator.check_schema(descriptor["result_schema"])


def test_tampered_or_wrong_corpus_is_explicit_failure(tmp_path, monkeypatch):
    index = agent.build_index(ROOT)
    index["documents"][0]["text"] += " tampered"
    path = tmp_path / "index.json"
    path.write_text(json.dumps(index))
    monkeypatch.setattr(agent, "INDEX_PATH", path)
    with pytest.raises(ValueError, match="digest mismatch"):
        run(request("reference-search"))
    index["documents"].pop()
    path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="fixed corpus"):
        run(request("reference-search"))


def github_environment(monkeypatch):
    for key, value in {
        "GITHUB_REPOSITORY": agent.REPOSITORY, "GITHUB_REF": "refs/heads/master",
        "GITHUB_ACTOR": "cvessell-create", "GITHUB_SHA": "a" * 40,
        "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2",
        "GITHUB_EVENT_NAME": "workflow_dispatch", "VF_REQUEST_JSON": json.dumps(request()),
    }.items():
        monkeypatch.setenv(key, value)


@pytest.mark.parametrize("field,value", [
    ("GITHUB_REPOSITORY", "different/repo"), ("GITHUB_REF", "refs/heads/branch"),
    ("GITHUB_ACTOR", "unknown-agent"), ("GITHUB_SHA", "bad"),
    ("GITHUB_RUN_ID", "0"), ("GITHUB_RUN_ATTEMPT", "x"), ("GITHUB_EVENT_NAME", "push"),
])
def test_github_identity_boundary_rejects_without_success_artifact(
    tmp_path, monkeypatch, capsys, field, value,
):
    github_environment(monkeypatch)
    monkeypatch.setenv(field, value)
    output = tmp_path / "preview.json"
    assert agent.main(["--github", "--output", str(output)]) == 1
    assert not output.exists()
    assert "AGENT" in capsys.readouterr().err


def test_cli_success_binds_identity_and_preserves_input(tmp_path, monkeypatch):
    github_environment(monkeypatch)
    output = tmp_path / "preview.json"
    assert agent.main(["--github", "--output", str(output)]) == 0
    result = json.loads(output.read_text())
    assert result["execution"]["source_revision"] == "a" * 40
    assert result["execution"]["run_id"] == "123"
    assert result["execution"]["run_attempt"] == "2"
    raw = tmp_path / "request.json"
    raw.write_text(json.dumps(request()))
    original = raw.read_bytes()
    assert agent.main(["--request", str(raw), "--output", str(raw)]) == 1
    assert raw.read_bytes() == original


@pytest.mark.parametrize("field", ["unexpected", "operation"])
def test_cli_validation_does_not_echo_sensitive_input(tmp_path, capsys, field):
    raw = tmp_path / "invalid.json"
    value = request()
    value[field] = "PRIVATE-MARKER-DO-NOT-ECHO"
    raw.write_text(json.dumps(value))
    assert agent.main(["--request", str(raw)]) == 1
    output = capsys.readouterr()
    assert "AGENT INPUT REJECTED" in output.err
    assert "PRIVATE-MARKER-DO-NOT-ECHO" not in output.err
    assert not output.out


def test_browser_and_python_reference_search_match():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for browser search parity")
    queries = ["human release", "HUMAN", "legal", "zznotfoundinscopezz", "Straße"]
    code = """
const { searchIndex } = require(process.argv[1]);
const index = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
process.stdout.write(JSON.stringify(JSON.parse(process.argv[3]).map(q => searchIndex(index, q, 5))));
"""
    completed = subprocess.run(
        [node, "-e", code, str(ROOT / "docs/agent-search.js"),
         str(agent.INDEX_PATH), json.dumps(queries)],
        capture_output=True, text=True, check=True,
    )
    for query, browser in zip(queries, json.loads(completed.stdout), strict=True):
        result = agent.search_references(agent.SearchPayload(query=query, limit=5))
        for name in ("total_matches", "result_count", "limit_hit", "status"):
            assert result[name] == browser[name]
        for left, right in zip(result["results"], browser["results"], strict=True):
            assert {key: left[key] for key in right} == right


def test_workflow_and_pages_are_wired_without_widening_control_panel():
    workflow = (ROOT / ".github/workflows/agent-analysis.yml").read_text()
    for clause in (
        "workflow_dispatch:", "contents: read", "persist-credentials: false",
        'test "$GITHUB_REF" = "refs/heads/master"',
        'test "$GITHUB_ACTOR" = "cvessell-create"',
        "VF_REQUEST_JSON: ${{ inputs.request_json }}",
        "python -m vessell.hosted_agent --github --output results/preview.json",
        "retention-days: 7", "if-no-files-found: error",
    ):
        assert clause in workflow
    assert workflow.count("${{ inputs.request_json }}") == 1
    assert "pull_request" not in workflow
    assert "schedule:" not in workflow
    assert "always()" not in workflow
    control = (ROOT / ".github/workflows/run-framework.yml").read_text()
    assert "agent-analysis" not in control
    assert "reference-search" not in control
    assert "agents.html" in (ROOT / "docs/index.html").read_text()
    for path in ("README.md", "VISION_AND_SCOPE.md", "PROFESSOR_README.md",
                 "docs/specialist-agent.md", "docs/github-control-panel.md", "MANIFEST.in"):
        assert "github-agent-integration.md" in (ROOT / path).read_text()


def test_module_cli_executes_from_public_example(tmp_path):
    output = tmp_path / "preview.json"
    completed = subprocess.run(
        [sys.executable, "-m", "vessell.hosted_agent", "--request",
         str(ROOT / "examples/hosted-agent-search.json"), "--output", str(output)],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.read_text())["state"] == "UNRELEASED_PREVIEW"
