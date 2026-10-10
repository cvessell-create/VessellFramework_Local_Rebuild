"""Validate catalog coverage and evidence labels, not legal correctness."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming",
}


def test_state_catalog_has_exact_coverage_and_explicit_source_access():
    catalog = json.loads((ROOT / "docs/state-law-protections.json").read_text())
    rows = catalog["states"]
    names = {row["state"] for row in rows}
    assert len(names) == len(rows)
    assert names <= STATES
    assert catalog["included_state_count"] == len(rows)
    assert catalog["pending_state_count"] == 50 - len(rows)
    if catalog["completion"] == "COMPLETE_BOUNDED_PASS":
        assert names == STATES
    else:
        assert catalog["completion"] == "PARTIAL"
        assert catalog["pending_state_count"] > 0
    for row in rows:
        for subject in ("electronic_transactions", "trade_secrets"):
            entry = row[subject]
            record = entry["search_record"]
            assert entry["status"] in {"SOURCE-ESTABLISHED", "UNVERIFIED"}
            assert record["status"] == entry["status"]
            assert record["query"] and record["tool"] and record["scope"]
            assert isinstance(record["result_count"], int)
            assert record["result_count"] >= 0
            assert isinstance(record["limit_hit"], bool)
            assert record["what_was_not_checked"]
            assert entry["note"]
            if entry["status"] == "SOURCE-ESTABLISHED":
                assert record["primary_source_opened"] is True
                assert entry["url"].startswith("https://")
                assert entry["citation"]
            else:
                assert record["primary_source_opened"] is False


def test_legal_notices_preserve_license_and_informational_boundaries():
    assert hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest() == (
        "988ee76427017d910675fd72b00e284aa51dbffa369f4b721247445afefcaf27"
    )
    electronic = (ROOT / "docs/washington-rcw-19.74.md").read_text()
    assert "**chapter 1.80 RCW**" in electronic
    assert "1633.7" in electronic
    trade = (ROOT / "docs/trade-secrets-notice.md").read_text()
    assert "3426.1" in trade
    assert "publicly available repository contents are trade\nsecrets" in trade
    assert "does not withdraw or modify the Apache License" in trade
    for text in (electronic, trade):
        assert "state-law-protections.md" in text
    catalog = (ROOT / "docs/state-law-protections.md").read_text()
    assert "not legal advice" in catalog
    assert "not automatic nationwide protection" in catalog
