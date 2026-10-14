import base64
import json

from vessell import footprint_scan, name_search

SITE = {"name": "Example Site", "uri_check": "https://ex.test/u/{account}", "e_code": 200, "e_string": "profile",
        "m_code": 404, "m_string": "not found", "cat": "social"}


def fake(responses):
    calls = []

    def fetch(url, method="GET", data=None, headers=None):
        calls.append((url, method, data))
        return responses[url]
    fetch.calls = calls
    return fetch


def test_variants_derive_usernames_from_full_name():
    names = footprint_scan.variants("Christopher Ray Vessell")
    for expected in ("christopherrayvessell", "cvessell", "chrisvessell"):
        assert expected in names
    assert len(names) == len(set(names))


def test_check_applies_whatsmyname_rules_and_posts_when_needed():
    fetch = fake({"https://ex.test/u/a": (200, "<h1>profile</h1>"), "https://ex.test/u/b": (404, "not found"),
                  "https://ex.test/u/c": (503, "busy")})
    assert [footprint_scan.check(SITE, u, fetch) for u in "abc"] == ["hit", "miss", "unclear"]
    post = dict(SITE, post_body='{"u":"{account}"}')
    footprint_scan.check(post, "a", fetch)
    assert fetch.calls[-1] == ("https://ex.test/u/a", "POST", b'{"u":"a"}')


def test_finding_attaches_justdeleteme_fix_and_marks_unconfirmed():
    jdm = footprint_scan.jdm_index([{"name": "Example-Site", "url": "https://ex.test/delete", "difficulty": "hard"}])
    row = footprint_scan.finding(SITE, "cvessell", jdm)
    assert row["url"] == "https://ex.test/u/cvessell"
    assert row["fix"]["url"] == "https://ex.test/delete" and row["fix"]["difficulty"] == "hard"
    assert row["ownership"].startswith("UNCONFIRMED")


def test_scan_counts_and_only_reports_hits():
    fetch = fake({"https://ex.test/u/a": (200, "profile"), "https://ex.test/u/b": (404, "not found")})
    result = footprint_scan.scan(["a", "b"], [SITE], [], fetch=fetch, workers=2)
    assert result["counts"] == {"hit": 1, "miss": 1, "unclear": 0}
    assert [f["username"] for f in result["findings"]] == ["a"]


def test_parse_bing_decodes_redirect_links():
    target = base64.urlsafe_b64encode(b"https://people.test/x").decode().rstrip("=")
    page = (f'<li class="b_algo"><h2><a href="https://www.bing.com/ck/a?!&amp;u=a1{target}&amp;n=1">'
            '<b>Chris</b> Vessell</a></h2><p>Age 40, phone</p></li>')
    assert name_search.parse_bing(page) == [{"url": "https://people.test/x", "title": "Chris Vessell",
                                             "snippet": "Age 40, phone", "engine": "bing"}]


def test_parse_brave_reads_result_links():
    page = '<a href="https://ex.test/p" target="_self" class="svelte-1 l1"><div class="title s">Chris Vessell</div></a>'
    assert name_search.parse_brave(page) == [{"url": "https://ex.test/p", "title": "Chris Vessell",
                                              "snippet": "", "engine": "brave"}]


def test_classify_and_save_dedupe(tmp_path):
    broker = name_search.classify({"url": "https://www.whitepages.com/name/X", "title": "Chris Vessell phone address",
                                   "snippet": "", "engine": "t"}, "Chris Vessell")
    assert broker["category"] == "data_broker" and broker["ownership"].startswith("UNCONFIRMED")
    other = name_search.classify({"url": "https://blog.test/a", "title": "hello", "snippet": "", "engine": "t"},
                                 "Chris Vessell")
    assert other["category"] == "web_mention" and "exact phrase not in snippet" in other["ownership"]
    path = tmp_path / "exposures.jsonl"
    assert name_search.save([broker, other, broker], path) == 2
    assert name_search.save([broker], path) == 0
    assert len([json.loads(x) for x in path.read_text().splitlines()]) == 2
