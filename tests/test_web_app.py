# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Tests for the Claim Verifier web app (vessell/app/server.py).

Covers request parsing/validation and the live HTTP endpoints against
the real vessell/verify.py doctrine.
"""

from __future__ import annotations

import ast
import http.client
import json
import logging
import re
import shutil
import subprocess
import sys
import threading
import tomllib
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from vessell.app.client import VerifierClient, VerifierError, launch
from vessell.app.server import (
    VerifierHandler,
    build_claim_check,
    build_posting,
    build_postings,
    build_sighting,
    parse_tier,
)
from vessell.provenance import SourceStatus


def _sighting(**overrides):
    base = {"source_name": "USGS", "tier": "SOURCE-ESTABLISHED"}
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_parse_tier_accepts_loose_forms() -> None:
    assert parse_tier("SOURCE-ESTABLISHED") is SourceStatus.SOURCE_ESTABLISHED
    assert parse_tier("source_established") is SourceStatus.SOURCE_ESTABLISHED
    assert parse_tier("  Framework Synthesis ") is SourceStatus.FRAMEWORK_SYNTHESIS
    assert parse_tier("working_hypothesis") is SourceStatus.WORKING_HYPOTHESIS
    assert parse_tier("ILLUSTRATIVE") is SourceStatus.ILLUSTRATIVE


def test_parse_tier_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown source tier"):
        parse_tier("TRUST ME BRO")


def test_handler_log_message_accepts_base_class_keyword(caplog: pytest.LogCaptureFixture) -> None:
    handler = VerifierHandler.__new__(VerifierHandler)
    with caplog.at_level(logging.INFO, logger="vessell.app.server"):
        handler.log_message(format="Request handled")
    assert "Request handled" in caplog.text


@pytest.mark.parametrize("value", ["2026-09-25garbage", "2026-09-25T99:99:99"])
def test_build_posting_rejects_invalid_date_suffix(value: str) -> None:
    with pytest.raises(ValueError, match="ISO date or timestamp"):
        build_posting({
            "title": "Synthetic role", "employer": "Synthetic employer",
            "location": "Synthetic location", "description_text": "Synthetic description",
            "claimed_posted": value,
        })


def test_build_posting_preserves_valid_timestamp() -> None:
    value = "2026-09-25T09:30:00-07:00"
    result = build_posting({
        "title": "Synthetic role", "employer": "Synthetic employer",
        "location": "Synthetic location", "description_text": "Synthetic description",
        "claimed_posted": value,
    })
    assert result.claimed_posted == value


def test_build_sighting_requires_source_name() -> None:
    with pytest.raises(ValueError, match="source_name"):
        build_sighting({"tier": "SOURCE-ESTABLISHED"})


def test_build_sighting_maps_fields() -> None:
    sighting = build_sighting(
        _sighting(
            url="https://example.com",
            root="ap-wire",
            denies="yes",
            is_official_record=True,
            note="event page",
        )
    )
    assert sighting.source_name == "USGS"
    assert sighting.tier is SourceStatus.SOURCE_ESTABLISHED
    assert sighting.url == "https://example.com"
    assert sighting.root == "ap-wire"
    assert sighting.denies is True
    assert sighting.is_official_record is True
    assert sighting.note == "event page"


def test_build_claim_check_requires_claim() -> None:
    with pytest.raises(ValueError, match="claim"):
        build_claim_check({"sightings": []})


def test_build_claim_check_builds_sightings() -> None:
    check = build_claim_check(
        {"claim": "It rained", "sightings": [_sighting(), _sighting(source_name="NWS")]}
    )
    assert check.claim == "It rained"
    assert len(check.sightings) == 2
    assert check.sightings[1].source_name == "NWS"


def _posting(**overrides):
    base = {
        "title": "Operations Manager",
        "employer": "Uline",
        "location": "Lacey, WA",
        "description_text": "Operations Manager. Pay from $96,000 to $160,000 per year.",
    }
    base.update(overrides)
    return base


def test_build_posting_requires_core_fields() -> None:
    with pytest.raises(ValueError, match="title"):
        build_posting(_posting(title=""))


def test_build_postings_requires_nonempty_list() -> None:
    with pytest.raises(ValueError, match="postings"):
        build_postings({"postings": []})


# ---------------------------------------------------------------------------
# Live HTTP endpoints
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), VerifierHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def _post(base: str, path: str, payload: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def test_index_serves_html(live_server: str) -> None:
    with urllib.request.urlopen(live_server + "/") as response:
        assert response.status == 200
        body = response.read().decode("utf-8")
    assert "Claim Verifier" in body
    assert "VessellFramework" in body


def test_api_verify_end_to_end(live_server: str) -> None:
    status, data = _post(
        live_server,
        "/api/verify",
        {
            "claim": "M4.2 earthquake near Wauna, WA",
            "sightings": [
                {
                    "source_name": "USGS",
                    "tier": "SOURCE-ESTABLISHED",
                    "is_official_record": True,
                },
                {"source_name": "KOMO", "tier": "SOURCE-ESTABLISHED"},
            ],
        },
    )
    assert status == 200
    assert data["verdict"] == "VERIFIED"
    assert data["official_record"] is True
    assert data["corroboration_score"] == 1.0
    assert data["source_access"] == "NOT_PERFORMED"
    assert data["release_status"] == "ANALYSIS_ONLY_NOT_RELEASED"


def test_api_verify_rejects_bad_tier(live_server: str) -> None:
    status, data = _post(
        live_server,
        "/api/verify",
        {"claim": "X", "sightings": [{"source_name": "Y", "tier": "BOGUS"}]},
    )
    assert status == 400
    assert "Unknown source tier" in data["error"]


def test_api_planted_news_end_to_end(live_server: str) -> None:
    sightings = [
        {
            "source_name": f"Outlet {i}",
            "tier": "ILLUSTRATIVE",
            "root": "viral-post",
            "text": "BREAKING: bridge closed, avoid the area",
            "seen_at": f"2026-10-10T08:{i:02d}:00",
            "published_at": f"2026-10-10T08:{i:02d}:00",
        }
        for i in range(5)
    ]
    status, data = _post(
        live_server, "/api/planted-news", {"claim": "Bridge closed", "sightings": sightings}
    )
    assert status == 200
    assert data["verdict"] == "LIKELY_PLANTED"
    assert data["burst_detected"] is True
    assert data["clone_army_size"] >= 5


def test_api_ghost_job_end_to_end(live_server: str) -> None:
    text = "Operations Manager. Pay from $96,000 to $160,000 per year."
    postings = [
        {
            "title": "Operations Manager",
            "employer": "Uline",
            "location": "Lacey, WA",
            "description_text": text,
            "source": source,
            "listing_id": lid,
            "claimed_posted": claimed,
            "first_seen": seen,
        }
        for source, lid, claimed, seen in [
            ("Monster", "m-1", "2026-09-25", "2025-12-24"),
            ("Ladders", "l-1", "2026-09-23", "2026-01-15"),
            ("CareerBuilder", "c-1", "2026-09-01", "2026-03-02"),
        ]
    ]
    status, data = _post(live_server, "/api/ghost-job", {"postings": postings})
    assert status == 200
    assert data["verdict"] == "LIKELY_GHOST"
    assert data["distinct_sources"] == 3
    assert data["distinct_listing_ids"] == 3


def test_api_ghost_job_rejects_empty(live_server: str) -> None:
    status, data = _post(live_server, "/api/ghost-job", {"postings": []})
    assert status == 400
    assert "postings" in data["error"]


def test_unknown_endpoint_404(live_server: str) -> None:
    status, _ = _post(live_server, "/api/nope", {})
    assert status == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"claim": 5, "sightings": []},
        {"claim": "X", "sightings": False},
        {"claim": "X", "sightings": [_sighting(denies="maybe")]},
        {"claim": "X", "sightings": [_sighting(published_at="not-a-date")]},
        {"claim": "X", "sightings": [_sighting()] * 101},
        {"claim": "X", "sightings": [], "approved": True},
    ],
)
def test_api_rejects_invalid_records(live_server: str, payload: dict) -> None:
    status, data = _post(live_server, "/api/verify", payload)
    assert status == 400
    assert data["error"]


def test_api_rejects_unrelated_job_roles(live_server: str) -> None:
    status, data = _post(
        live_server, "/api/ghost-job",
        {"postings": [_posting(), _posting(title="Inventory Analyst")]},
    )
    assert status == 400
    assert "one employer/title/location" in data["error"]


@pytest.mark.parametrize(
    ("headers", "body", "status"),
    [
        ({"Host": "remote.example"}, b"{}", 403),
        ({"Origin": "https://remote.example"}, b"{}", 403),
        ({"Content-Length": "-1"}, b"", 400),
        ({"Content-Length": "invalid"}, b"", 400),
        ({"Content-Length": "65537"}, b"", 413),
        ({"Transfer-Encoding": "chunked"}, b"", 400),
        ({"Content-Type": "text/plain"}, b"{}", 415),
    ],
)
def test_http_boundary_rejects_invalid_requests(
    live_server: str, headers: dict, body: bytes, status: int,
) -> None:
    connection = http.client.HTTPConnection(live_server.removeprefix("http://"), timeout=5)
    try:
        connection.request(
            "POST", "/api/verify", body=body,
            headers={"Content-Type": "application/json", **headers},
        )
        response = connection.getresponse()
        assert response.status == status
        assert json.loads(response.read())["error"]
        assert response.getheader("Cache-Control") == "no-store"
        assert response.getheader("X-Content-Type-Options") == "nosniff"
    finally:
        connection.close()


def test_ui_marks_examples_and_defaults_as_unverified(live_server: str) -> None:
    with urllib.request.urlopen(live_server + "/") as response:
        body = response.read().decode("utf-8")
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert 'data.tier || "WORKING HYPOTHESIS"' in body
    assert "Examples are fixtures" in body
    assert "URLs are not fetched or authenticated" in body


def test_package_configuration_includes_form_ui() -> None:
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / "pyproject.toml").read_text())
    assert "static/*.html" in config["tool"]["setuptools"]["package-data"]["vessell.app"]
    assert (root / "vessell/app/static/index.html").is_file()


# ---------------------------------------------------------------------------
# Programmatic client
# ---------------------------------------------------------------------------


def test_client_verify_in_process() -> None:
    with launch() as client:
        report = client.verify(
            claim="M4.2 earthquake near Wauna, WA",
            sightings=[
                {"source_name": "USGS", "tier": "SOURCE-ESTABLISHED",
                 "is_official_record": True},
                {"source_name": "KOMO", "tier": "SOURCE-ESTABLISHED"},
            ],
        )
    assert report["verdict"] == "VERIFIED"
    assert report["corroboration_score"] == 1.0


def test_client_planted_news_in_process() -> None:
    sightings = [
        {
            "source_name": f"Outlet {i}",
            "tier": "ILLUSTRATIVE",
            "root": "viral-post",
            "text": "BREAKING: bridge closed, avoid the area",
            "seen_at": f"2026-10-10T08:{i:02d}:00",
            "published_at": f"2026-10-10T08:{i:02d}:00",
        }
        for i in range(5)
    ]
    with launch() as client:
        report = client.planted_news(claim="Bridge closed", sightings=sightings)
    assert report["verdict"] == "LIKELY_PLANTED"
    assert report["burst_detected"] is True


def test_client_ghost_job_in_process() -> None:
    text = "Operations Manager. Pay from $96,000 to $160,000 per year."
    postings = [
        {
            "title": "Operations Manager",
            "employer": "Uline",
            "location": "Lacey, WA",
            "description_text": text,
            "source": source,
            "listing_id": lid,
            "claimed_posted": claimed,
            "first_seen": seen,
        }
        for source, lid, claimed, seen in [
            ("Monster", "m-1", "2026-09-25", "2025-12-24"),
            ("Ladders", "l-1", "2026-09-23", "2026-01-15"),
        ]
    ]
    with launch() as client:
        report = client.ghost_job(postings=postings)
    assert report["verdict"] in ("LIKELY_GHOST", "SUSPECT")
    assert report["distinct_sources"] == 2


def test_client_raises_verifier_error_on_bad_input() -> None:
    with launch() as client, pytest.raises(VerifierError, match="Unknown source tier"):
        client.verify(
            claim="X",
            sightings=[{"source_name": "Y", "tier": "BOGUS"}],
        )


def test_client_talks_to_external_server(live_server: str) -> None:
    client = VerifierClient(live_server)
    report = client.verify(
        claim="M4.2 earthquake near Wauna, WA",
        sightings=[{"source_name": "USGS", "tier": "SOURCE-ESTABLISHED",
                    "is_official_record": True}],
    )
    assert report["verdict"] == "VERIFIED"


# ---------------------------------------------------------------------------
# GitHub Pages bundle (docs/index.html)
# ---------------------------------------------------------------------------

DOCS_INDEX = Path(__file__).resolve().parent.parent / "docs" / "index.html"


def _docs_html() -> str:
    assert DOCS_INDEX.exists(), "docs/index.html missing — the GitHub Pages app is gone"
    return DOCS_INDEX.read_text(encoding="utf-8")


def test_pages_bundle_references_repo_files() -> None:
    """Every Python file the Pages app fetches must exist in the repo."""
    html = _docs_html()
    repo_root = Path(__file__).resolve().parent.parent
    # The bootstrap fetches a literal list of repo-relative .py paths.
    paths = set(re.findall(r'"(vessell/[\w/]+\.py|vesselframework_reference[\w.]+\.py)"', html))
    assert paths, "no Python file list found in docs/index.html"
    missing = [p for p in paths if not (repo_root / p).exists()]
    assert not missing, f"Pages bundle references missing repo files: {missing}"


def test_pages_bundle_glue_is_valid_python() -> None:
    """The Pyodide glue code embedded in docs/index.html must parse."""
    html = _docs_html()
    match = re.search(r"const GLUE = `\n(.*?)`;\n", html, re.DOTALL)
    assert match, "GLUE block not found in docs/index.html"
    ast.parse(match.group(1))  # raises SyntaxError if invalid


def test_pages_bundle_declares_pyodide() -> None:
    html = _docs_html()
    assert "pyodide" in html.lower()
    assert "loadPyodide" in html


@pytest.mark.parametrize("failure", ["", "fetch", "filesystem", "imports"])
def test_pages_bootstrap_uses_absolute_paths_and_reports_failed_stage(failure: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required to execute the browser bootstrap regression")
    html = _docs_html()
    bootstrap = html[html.index("async function boot()"):html.index("// --- UI")]
    script = """
const assert = require("node:assert/strict");
const failure = process.argv[1];
const writes = {};
const buttons = [{disabled: true}, {disabled: true}, {disabled: true}];
const classes = new Set();
const status = {textContent: "", classList: {add(value) { classes.add(value); }}};
const document = {
  getElementById() { return status; },
  querySelectorAll() { return buttons; }
};
const GLUE = "";
let VF = null;
async function loadPyodide() {
  return {
    FS: {
      cwd() { return "/home/pyodide"; },
      mkdirTree(path) {
        assert.ok(path.startsWith("/"), "mkdirTree needs an absolute path");
        if (failure === "filesystem") throw {name: "ErrnoError", errno: 44};
      },
      writeFile(path, text) {
        assert.ok(path.startsWith("/"), "writeFile needs an absolute path");
        writes[path] = text;
      }
    },
    async runPythonAsync() {
      if (failure === "imports") throw new Error("Missing module");
    },
    globals: {get(name) { return name; }}
  };
}
async function fetch() {
  return {ok: failure !== "fetch", status: 503, async text() { return "# module"; }};
}
""" + bootstrap + """
boot().then(() => {
  if (failure) {
    assert.ok(classes.has("failed"));
    assert.ok(!classes.has("ready"));
    assert.ok(buttons.every(button => button.disabled));
    assert.equal(VF, null);
    const stage = failure === "imports" ? "Python imports and verifier glue" : "vessell/verify.py";
    assert.ok(status.textContent.includes(stage));
    if (failure === "filesystem") assert.ok(status.textContent.includes("ErrnoError (errno 44)"));
  } else {
    assert.ok(classes.has("ready"));
    assert.ok(buttons.every(button => !button.disabled));
    assert.ok(writes["/home/pyodide/vessell/provenance_firewall.py"]);
    assert.ok(writes["/home/pyodide/vessell/app/__init__.py"]);
    assert.ok(!writes["/home/pyodide/vessell/app/pipeline.py"]);
    assert.equal(VF.api_verify, "api_verify");
  }
}).catch(error => { console.error(error); process.exitCode = 1; });
"""
    result = subprocess.run(
        [node, "-e", script, failure], capture_output=True, text=True, timeout=15, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_pages_bundle_imports_and_analyzes_without_checkout(tmp_path: Path) -> None:
    html = _docs_html()
    paths = set(re.findall(
        r'"(vessell/[\w/]+\.py|vesselframework_reference[\w.]+\.py)"', html,
    ))
    root = DOCS_INDEX.parent.parent
    for path in paths:
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((root / path).read_bytes())
    for package in ("vessell", "vessell/app"):
        (tmp_path / package / "__init__.py").write_text("")
    match = re.search(r"const GLUE = `\n(.*?)`;\n", html, re.DOTALL)
    assert match
    script = (
        "import sys\nsys.path.insert(0, sys.argv[1])\n" + match.group(1) + """
claim = json.loads(api_verify(json.dumps({"claim": "Illustrative claim", "sightings": []})))
spread = json.loads(api_planted(json.dumps({"claim": "Illustrative claim", "sightings": []})))
job = json.loads(api_ghost(json.dumps({"postings": [{
    "title": "Example", "employer": "Fixture", "location": "Example",
    "description_text": "Illustrative job", "source": "Fixture"
}]})))
for result in (claim, spread, job):
    assert "error" not in result, result
    assert result["source_access"] == "NOT_PERFORMED"
    assert result["release_status"] == "ANALYSIS_ONLY_NOT_RELEASED"
"""
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(tmp_path)],
        capture_output=True, text=True, timeout=15, cwd=tmp_path, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_pages_bundle_preserves_analysis_boundaries() -> None:
    html = _docs_html()
    assert "VessellFramework_Local_Rebuild@master/" in html
    assert 'data.tier || "WORKING HYPOTHESIS"' in html
    assert "illustrative fixtures" in html
    match = re.search(r"const GLUE = `\n(.*?)`;\n", html, re.DOTALL)
    assert match
    namespace: dict = {}
    exec(compile(match.group(1), str(DOCS_INDEX), "exec"), namespace)  # noqa: S102 - test the repository-owned browser glue
    report = json.loads(namespace["api_verify"](json.dumps({
        "claim": "Synthetic claim",
        "sightings": [{"source_name": "Synthetic source", "tier": "WORKING HYPOTHESIS"}],
    })))
    assert report["source_access"] == "NOT_PERFORMED"
    assert report["release_status"] == "ANALYSIS_ONLY_NOT_RELEASED"
    mixed_roles = [
        {"title": title, "employer": "Synthetic", "location": "Test",
         "description_text": "Synthetic description"}
        for title in ("Engineer", "Manager")
    ]
    rejected = json.loads(namespace["api_ghost"](json.dumps({"postings": mixed_roles})))
    assert "one employer, title and location" in rejected["error"]
