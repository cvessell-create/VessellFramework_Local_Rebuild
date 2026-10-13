import json

import pytest
from fastapi.testclient import TestClient

from vessell.verifier_app import MAX_BODY_BYTES, create_app


def _client() -> TestClient:
    return TestClient(create_app(), base_url="http://127.0.0.1")


def test_local_page_explains_limits_and_sets_security_headers():
    response = _client().get("/")

    assert response.status_code == 200
    assert "does not search the web" in response.text
    assert response.headers["cache-control"] == "no-store"
    assert "connect-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"


def test_claim_endpoint_uses_framework_verification_functions():
    response = _client().post(
        "/api/v1/verification/claims",
        json={
            "claim": "A recorded event occurred",
            "sightings": [{
                "source_name": "Official record",
                "tier": "SOURCE-ESTABLISHED",
                "root": "official-record-1",
                "is_official_record": True,
                "note": "Submitted operator description",
            }],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_access"] == "NOT_PERFORMED"
    assert body["release_status"] == "ANALYSIS_ONLY_NOT_RELEASED"
    assert body["verification"]["verdict"] == "VERIFIED"
    assert body["planted_news"]["verdict"] == "AUTHENTIC"


def test_job_endpoint_groups_roles_and_uses_framework_ghost_job_check():
    posting = {
        "title": "Operations Analyst",
        "employer": "Example Co",
        "location": "Olympia, WA",
        "description_text": "Same role description",
        "claimed_posted": "2026-09-25",
        "first_seen": "2025-12-24",
        "url": "https://example.org/job",
    }
    response = _client().post(
        "/api/v1/verification/jobs",
        json={"postings": [
            {**posting, "source": "Board A", "listing_id": "a1"},
            {**posting, "source": "Board B", "listing_id": "b1"},
            {**posting, "source": "Board C", "listing_id": "c1"},
        ]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["postings_received"] == 3
    assert body["release_status"] == "ANALYSIS_ONLY_NOT_RELEASED"
    assert len(body["roles"]) == 1
    assert body["roles"][0]["verdict"] == "LIKELY_GHOST"
    assert body["roles"][0]["distinct_sources"] == 3


def test_rejects_invalid_input_without_echoing_submitted_values():
    private_value = "do-not-echo-this-value"
    response = _client().post(
        "/api/v1/verification/claims",
        json={"claim": private_value, "sightings": [{"source_name": "", "tier": "BAD"}]},
    )

    assert response.status_code == 422
    assert private_value not in response.text
    assert response.json()["error"] == "Invalid verifier input."


def test_rejects_non_loopback_host_and_cross_origin_requests():
    client = _client()
    remote_host = client.get("/", headers={"host": "example.org"})
    cross_origin = client.post(
        "/api/v1/verification/claims",
        headers={"origin": "https://example.org"},
        json={"claim": "Claim", "sightings": []},
    )

    assert remote_host.status_code == 403
    assert cross_origin.status_code == 403


def test_rejects_oversized_request_body():
    response = _client().post(
        "/api/v1/verification/claims",
        content=json.dumps({"claim": "x" * (MAX_BODY_BYTES + 100), "sightings": []}),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413


@pytest.mark.parametrize("host", ["[invalid", "user@localhost", "localhost:not-a-port"])
def test_rejects_malformed_loopback_authority(host: str) -> None:
    response = _client().get("/", headers={"host": host})
    assert response.status_code == 403
    assert "error" in response.json()


@pytest.mark.parametrize("value", ["2026-09-25garbage", "2026-09-25T99:99:99"])
def test_rejects_posting_dates_with_invalid_suffix(value: str) -> None:
    response = _client().post(
        "/api/v1/verification/jobs",
        json={"postings": [{
            "title": "Synthetic role", "employer": "Synthetic employer",
            "location": "Synthetic location", "description_text": "Synthetic description",
            "source": "Synthetic board", "claimed_posted": value,
        }]},
    )
    assert response.status_code == 422
