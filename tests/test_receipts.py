import json

import pytest

from vessell import receipts as r

KEY = b"k" * 32
OTHER = b"o" * 32


def leaves(n):
    return [{"path": f"out/{i}.jsonl", "sha256": f"{i:064x}"} for i in range(n)]


def test_sign_and_verify_up():
    rec = r.sign(leaves(5), KEY, "phase0", run_at=1.0)
    assert r.verify(rec, KEY) == []
    assert r.gate(r.verify(rec, KEY)) == "UP"
    assert rec["anchored"] is False


@pytest.mark.parametrize("field,value", [("loop_id", "other"), ("run_at", 2.0), ("merkle_root", "00" * 32)])
def test_tamper_is_down(field, value):
    rec = r.sign(leaves(3), KEY, "phase0", run_at=1.0)
    rec[field] = value
    assert r.gate(r.verify(rec, KEY)) == "DOWN"


def test_tampered_leaf_breaks_root_and_tag():
    rec = r.sign(leaves(3), KEY, "phase0", run_at=1.0)
    rec["leaves"][1]["sha256"] = "f" * 64
    problems = r.verify(rec, KEY)
    assert any("merkle root" in p for p in problems) and any("tag" in p for p in problems)


def test_duplicate_leaf_rejected():
    dup = leaves(2) + [leaves(2)[0]]
    with pytest.raises(ValueError):
        r.sign(dup, KEY, "phase0")
    rec = r.sign(leaves(2), KEY, "phase0", run_at=1.0)
    rec["leaves"].append(rec["leaves"][0])
    assert any("duplicate" in p for p in r.verify(rec, KEY))


def test_removed_leaf_is_down():
    rec = r.sign(leaves(4), KEY, "phase0", run_at=1.0)
    rec["leaves"].pop()
    assert r.gate(r.verify(rec, KEY)) == "DOWN"


def test_key_rotation_requires_matching_key():
    rec = r.sign(leaves(2), KEY, "phase0", run_at=1.0)
    problems = r.verify(rec, OTHER)
    assert any("key_id" in p for p in problems) and any("tag" in p for p in problems)
    assert r.verify(r.sign(leaves(2), OTHER, "phase0", run_at=1.0), OTHER) == []


def test_correction_supersedes_without_rewriting_old():
    old = r.sign(leaves(2), KEY, "phase0", run_at=1.0)
    before = json.dumps(old, sort_keys=True)
    new = r.sign(leaves(3), KEY, "phase0", supersedes=old["receipt_id"], run_at=2.0)
    assert new["supersedes"] == old["receipt_id"]
    assert r.verify(new, KEY) == [] and r.verify(old, KEY) == []
    assert json.dumps(old, sort_keys=True) == before


@pytest.mark.parametrize("n", [1, 2, 3, 5, 8, 13])
def test_membership_proofs(n):
    ls = leaves(n)
    root = r.merkle_root(ls)
    for i, leaf in enumerate(ls):
        assert r.verify_membership(leaf, r.membership_proof(ls, i), root)
    fake = {"path": "out/x.jsonl", "sha256": "e" * 64}
    assert not r.verify_membership(fake, r.membership_proof(ls, 0), root)


def test_leaf_and_node_domains_differ():
    a, b = leaves(2)
    assert r.merkle_root([a, b]) != r.leaf_hash(a).hex()


def test_check_files_detects_change_and_missing(tmp_path):
    f = tmp_path / "a.jsonl"
    f.write_text("one\n")
    leaf = {"path": "a.jsonl", "sha256": __import__("hashlib").sha256(b"one\n").hexdigest()}
    rec = r.sign([leaf], KEY, "phase0", run_at=1.0)
    assert r.verify(rec, KEY, check_files=True, root_dir=tmp_path) == []
    f.write_text("two\n")
    assert any("changed" in p for p in r.verify(rec, KEY, check_files=True, root_dir=tmp_path))
    f.unlink()
    assert any("missing" in p for p in r.verify(rec, KEY, check_files=True, root_dir=tmp_path))


def test_load_key_creates_private_600(tmp_path):
    path = tmp_path / "private" / "k.key"
    key = r.load_key(path, create=True)
    assert len(key) == 32 and oct(path.stat().st_mode)[-3:] == "600"
    assert r.load_key(path) == key
