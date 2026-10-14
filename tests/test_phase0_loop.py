import json
from pathlib import Path

import pytest

from vessell import phase0_loop as p0
from vessell.si_chat import LoopMemory, loops_snapshot


def fake_fetch(url, body=None):
    if body is not None:
        method = json.loads(body)["method"]
        result = "0x14a34" if method == "eth_chainId" else "0x2de1f69"
        return 200, json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}).encode()
    if url in p0.BTC_TIPS:
        return 200, b"900000"
    src = next((s for s in p0.SOURCES if s["url"] == url), None)
    text = f"<title>{src['topic']}</title> {src['expect']}" if src else "ok"
    return 200, text.encode()


def write_inputs(tmp_path):
    mem = tmp_path / "memory.jsonl"
    rows = [{"kind": "lesson", "lesson": "Be specific and answer the question asked."},
            {"kind": "lesson", "lesson": "Be specific and answer the question asked please."}]
    rows += [{"kind": "episode", "generation": g, "mission": 4, "outcome": "timeout", "kills": 0} for g in range(12)]
    mem.write_text("".join(json.dumps(r) + "\n" for r in rows))
    levels = tmp_path / "levels.jsonl"
    levels.write_text(json.dumps({"levels": [{"level": "L1 Chatbot", "state": "up", "checks": [
        {"check": "answers: Who are you", "passed": False}]}]}) + "\n")
    ideas = tmp_path / "ideas.jsonl"
    ideas.write_text(json.dumps({"si_pitch": "A St. Louis Stalker ambush", "evidence_refs": ["E1"]}) + "\n")
    return mem, levels, ideas


def test_rpc_refuses_write_methods():
    with pytest.raises(PermissionError):
        p0.rpc(fake_fetch, p0.BASE_SEPOLIA_RPC, "eth_sendRawTransaction")


def test_run_offline_with_cited_roadmap(tmp_path):
    mem, levels, ideas = write_inputs(tmp_path)

    def gen(model, messages, max_tokens):
        return ("STEP: Sign loop receipts with a local test key and verify offline [R2,L7]\n"
                "STEP: Invented step [Z9]\nnot a step")

    rec = p0.run(fetch=fake_fetch, generate=gen, out_dir=tmp_path / "out", memory_path=mem,
                 levels_path=levels, idea_paths=(ideas,))
    assert all(s["status"] == "SOURCE OPENED" for s in rec["sources"])
    assert rec["status"] == "RESEARCH OBSERVATIONS / PENDING_HUMAN_REVIEW"
    assert all(t["ok"] for t in rec["touch"])
    assert rec["rereport"]["stall"]["length"] == 12
    assert rec["rereport"]["counts"]["ideas_on_theme"] == 1
    assert rec["rereport"]["counts"]["distinct_lessons"] == 1
    assert [s["evidence"] for s in rec["phase1_steps"]] == [["R2", "L7"]]
    assert rec["receipt_preview"]["signed"] is False and rec["receipt_preview"]["anchored"] is False
    assert rec["gate"]["state"].startswith("PHASE 0 COMPLETE") and rec["gate"]["phase1_authorized"] is False
    assert (tmp_path / "out" / "latest.json").exists()


def test_gate_flags_unreachable_network(tmp_path):
    mem, levels, ideas = write_inputs(tmp_path)
    rec = p0.run(fetch=lambda url, body=None: (0, b""), out_dir=tmp_path / "out", memory_path=mem,
                 levels_path=levels, idea_paths=(ideas,))
    assert rec["gate"]["state"] == "PHASE 0 IN PROGRESS"
    assert all(s["status"] == "NOT REACHED" for s in rec["sources"])


def test_change_detection_and_merkle(tmp_path):
    mem, levels, ideas = write_inputs(tmp_path)
    kw = dict(out_dir=tmp_path / "out", memory_path=mem, levels_path=levels, idea_paths=(ideas,))
    p0.run(fetch=fake_fetch, **kw)
    rec = p0.run(fetch=lambda u, b=None: (200, b"<title>x</title> changed " + u.encode()) if b is None else fake_fetch(u, b), **kw)
    assert rec["sources"][0]["changed_since_last"] is True
    a, b = "a" * 64, "b" * 64
    assert p0.merkle_root([a, b]) == p0.merkle_root([b, a])


def test_loops_snapshot_includes_phase0(tmp_path):
    mem, levels, ideas = write_inputs(tmp_path)
    p0.run(fetch=fake_fetch, out_dir=tmp_path / "out", memory_path=mem, levels_path=levels, idea_paths=(ideas,))
    snap = loops_snapshot(LoopMemory(mem), levels, ideas, phase0_path=tmp_path / "out" / "latest.json")
    assert snap["phase0"]["gate"]["phase1_authorized"] is False
    assert snap["phase0"]["findings"] and snap["phase0"]["sources"]


def test_roadmap_drops_echoes_and_single_sided_steps():
    ev = {"R2": "R2: OpenTimestamps client - SOURCE OPENED", "L7": "L7: STALL: 113 identical episodes"}
    text = ("STEP: Implement OpenTimestamps client [R2]\n"
            "STEP: Identify identical episodes [L7]\n"
            "STEP: OpenTimestamps client identical episodes [R2,L7]\n"
            "STEP: Hash each stalled autopilot run into a local receipt batch [R2,L7]")
    steps = p0.roadmap_steps(text, set(ev), ev)
    assert [s["step"] for s in steps] == ["Hash each stalled autopilot run into a local receipt batch"]


def test_phase1_immutable_receipt_and_strict_gate(tmp_path):
    from vessell import receipts
    mem, levels, ideas = write_inputs(tmp_path)
    key_path = tmp_path / "key"
    rec = p0.run(fetch=fake_fetch, out_dir=tmp_path / "out", memory_path=mem,
                 levels_path=levels, idea_paths=(ideas,), phase1=True, receipt_key_path=key_path)
    assert rec["formula"]["state"] == "UP"
    assert rec["phase1"]["state"] == "LOCAL_RECEIPT_VERIFIED"
    receipt = json.loads(Path(rec["phase1"]["receipt_path"]).read_text())
    key = receipts.load_key(key_path)
    assert receipts.verify(receipt, key, check_files=True) == []
    # Mutable loop inputs and latest.json do not invalidate the immutable run.
    mem.write_text("changed")
    (tmp_path / "out" / "latest.json").write_text("{}")
    assert receipts.verify(receipt, key, check_files=True) == []
    Path(rec["phase1"]["snapshot_path"]).write_text("{}")
    assert receipts.verify(receipt, key, check_files=True)


def test_one_source_failure_blocks_phase1_despite_policy_pass(tmp_path):
    mem, levels, ideas = write_inputs(tmp_path)
    def one_failure(url, body=None):
        return (0, b"") if url == p0.SOURCES[0]["url"] else fake_fetch(url, body)
    key_path = tmp_path / "key"
    rec = p0.run(fetch=one_failure, out_dir=tmp_path / "out", memory_path=mem,
                 levels_path=levels, idea_paths=(ideas,), phase1=True, receipt_key_path=key_path)
    assert rec["gate"]["state"].startswith("PHASE 0 COMPLETE")
    assert rec["formula"]["state"] == "DOWN"
    assert rec["phase1"]["state"] == "BLOCKED"
    assert not key_path.exists()


def test_formula_status_is_sanitized_and_rejects_stale_run(tmp_path):
    from vessell.si_chat import formula_snapshot
    mem, levels, ideas = write_inputs(tmp_path)
    rec = p0.run(fetch=fake_fetch, out_dir=tmp_path / "out", memory_path=mem,
                 levels_path=levels, idea_paths=(ideas,))
    path = tmp_path / "out" / "latest.json"
    status = formula_snapshot(path, now=rec["at"])
    assert status["state"] == "UP"
    assert "sources" not in status and "findings" not in status
    assert formula_snapshot(path, now=rec["at"] + 3601)["state"] == "DOWN"
    assert formula_snapshot(path, now=rec["at"] - 1)["state"] == "DOWN"
    assert formula_snapshot(tmp_path / "missing")["state"] == "DOWN"


def test_formula_status_binds_current_checks_to_signed_snapshot(tmp_path, monkeypatch):
    from vessell import receipts
    from vessell.si_chat import formula_snapshot
    mem, levels, ideas = write_inputs(tmp_path)
    key_path = tmp_path / "key"
    rec = p0.run(fetch=fake_fetch, out_dir=tmp_path / "out", memory_path=mem,
                 levels_path=levels, idea_paths=(ideas,), phase1=True, receipt_key_path=key_path)
    key = receipts.load_key(key_path)
    monkeypatch.setattr(receipts, "load_key", lambda: key)
    path = tmp_path / "out" / "latest.json"
    assert formula_snapshot(path, now=rec["at"])["phase1"] == "LOCAL_RECEIPT_VERIFIED"
    rec["formula"]["checks"][0]["passed"] = False
    path.write_text(json.dumps(rec))
    status = formula_snapshot(path, now=rec["at"])
    assert status["state"] == "DOWN" and status["phase1"] == "DOWN"
