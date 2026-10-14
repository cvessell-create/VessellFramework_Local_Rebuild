import json
from pathlib import Path

import pytest

from vessell import blockchain_simulation as simulation, receipts


def test_two_rounds_sign_and_verify_without_network(tmp_path, monkeypatch):
    import urllib.request

    def forbidden(*args, **kwargs):
        raise AssertionError("simulation must not contact networks")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    out = tmp_path / "out"
    key_path = tmp_path / "private" / "key"
    result = simulation.run(2, out_dir=out, key_path=key_path)
    assert result["formula"]["state"] == "UP"
    assert len(result["cases"]) == 24
    assert result["real_onboarding"] == "NOT_PERFORMED"
    assert result["phase_advance_authorized"] is False
    assert all(result[k] == 0 for k in ("network_calls", "wallets_created", "transactions_submitted"))
    receipt = json.loads(Path(result["receipt"]["receipt_path"]).read_text())
    key = receipts.load_key(key_path)
    assert receipts.verify(receipt, key, check_files=True) == []
    Path(result["receipt"]["snapshot_path"]).write_text("{}")
    assert receipts.verify(receipt, key, check_files=True)


def test_failed_boundary_is_retained_and_gate_down(tmp_path, monkeypatch):
    monkeypatch.setattr(simulation, "simulate", lambda inputs, seen: {
        "state": "SIMULATED_DELIVERY", "deliveries": 1})
    result = simulation.run(1, out_dir=tmp_path / "out", key_path=tmp_path / "key")
    assert result["formula"]["state"] == "DOWN"
    assert any(not row["passed"] for row in result["cases"])
    assert json.loads((tmp_path / "out" / "latest.json").read_text())["formula"]["state"] == "DOWN"


def test_correct_state_with_wrong_delivery_count_fails(tmp_path, monkeypatch):
    real_simulate = simulation.simulate

    def wrong_delivery(inputs, seen):
        result = real_simulate(inputs, seen)
        if result["state"] != "SIMULATED_DELIVERY":
            result["deliveries"] = 1
        return result

    monkeypatch.setattr(simulation, "simulate", wrong_delivery)
    result = simulation.run(1, out_dir=tmp_path / "out", key_path=tmp_path / "key")
    assert result["formula"]["state"] == "DOWN"


@pytest.mark.parametrize("rounds", [0, 21, -1])
def test_bounded_rounds(rounds, tmp_path):
    with pytest.raises(ValueError, match="between 1 and 20"):
        simulation.run(rounds, out_dir=tmp_path / "out", key_path=tmp_path / "key")
    assert not (tmp_path / "out").exists()
