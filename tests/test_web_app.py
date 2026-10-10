# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Tests for the Claim Verifier web app (vessell/app/server.py).

Covers request parsing/validation and the live HTTP endpoints against
the real vessell/verify.py doctrine.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

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
