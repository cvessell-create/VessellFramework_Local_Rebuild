import json

from vessell import footprint, si_chat

SCAN_TEXT = """Critical

Brokerline Index

Data broker

High

Oldplay

Account

Medium

[leaky-mirror.example](https://leaky-mirror.example)

Dark Web
"""


def _run(mem, order, outcome="complete"):
    seq = [{"id": f"F{i}", "category": c, "severity": "high", "t": i} for i, c in enumerate(order)]
    mem.append("episode", {"mission": 8, "outcome": outcome, "footprints": footprint.clean_footprints(seq)})


def test_clean_footprints_drops_free_text_and_unknown_values():
    raw = [{"id": "F1", "category": "dark_web", "severity": "critical", "t": "3.26", "note": "secret"},
           {"id": "F2", "category": "gossip", "severity": "high"},
           {"id": "F3", "category": "account", "severity": "low", "difficulty": "impossible"},
           {"id": "F4", "category": "account", "severity": "low", "difficulty": "trivial"},
           {"id": "bad id!", "category": "account", "severity": "low"}, "junk"]
    assert footprint.clean_footprints(raw) == [
        {"id": "F1", "category": "dark_web", "severity": "critical", "t": 3.3},
        {"id": "F3", "category": "account", "severity": "low", "t": 0.0, "difficulty": "impossible"},
        {"id": "F4", "category": "account", "severity": "low", "t": 0.0}]


def test_record_episode_keeps_only_sanitised_footprints(tmp_path):
    mem = si_chat.LoopMemory(tmp_path / "m.jsonl")
    chat = si_chat.SIChat(memory=mem, myth=[])
    rec = chat.record_episode({"mission": 8, "outcome": "complete", "footprints_total": 9,
                               "footprints": [{"id": "F1", "category": "account", "severity": "low", "who": "x"}]})
    assert rec["footprints"] == [{"id": "F1", "category": "account", "severity": "low", "t": 0.0}]
    assert rec["footprints_total"] == 9


def test_policy_learns_category_order_from_completed_runs_only(tmp_path):
    mem = si_chat.LoopMemory(tmp_path / "m.jsonl")
    _run(mem, ["dark_web", "data_broker", "account", "leaked_domain"])
    _run(mem, ["dark_web", "account", "data_broker", "leaked_domain"])
    _run(mem, ["leaked_domain", "account", "data_broker", "dark_web"], outcome="dead")
    policy = footprint.learn_policy(mem)
    assert policy["runs"] == 3 and policy["completed"] == 2
    order = policy["category_order"]
    assert order[0] == "dark_web" and order.index("leaked_domain") == 3 and order[-1] == "web_mention"
    assert policy["severity_order"][0] == "critical" and policy["status"] == "NOT_VERIFIED"


def test_scan_import_and_plan_are_drafts_ranked_by_severity_then_policy(tmp_path):
    rows = footprint.parse_scan_text(SCAN_TEXT)
    assert [(r["severity"], r["category"]) for r in rows] == [
        ("critical", "data_broker"), ("high", "account"), ("medium", "dark_web")]
    assert rows[2]["name"] == "leaky-mirror.example"
    path = tmp_path / "scan.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in reversed(rows)) + "not json\n")
    policy = footprint.learn_policy(si_chat.LoopMemory(tmp_path / "empty.jsonl"))
    plan = footprint.build_plan(footprint.load_scan(path), policy)
    assert [i["severity"] for i in plan["items"]] == ["critical", "high", "medium"]
    assert all(i["status"] == footprint.STATUS and i["steps"] for i in plan["items"])
    assert "nothing was sent" in plan["limits"][0]


def test_private_scan_folder_is_git_ignored():
    assert "/private/" in (footprint.ROOT / ".gitignore").read_text().splitlines()
