import os

import pytest
from test_static_capture import FIXTURE

from vessell.ambient.capture import capture, load_request, publish
from vessell.ambient.store import Store, canonical, digest


@pytest.mark.skipif(
    os.environ.get("VESSELL_CAPTURE_CONTAINER_TEST") != "1",
    reason="Requires the explicitly built local Docker capture image",
)
def test_real_offline_capture_and_adversarial_static_output(tmp_path):
    req = load_request(FIXTURE, "example")
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    image_id, evidence = capture(req, baseline)
    for name, content in evidence.items():
        (baseline / name).write_bytes(content)
    (baseline / "source.html").write_text(req["source_html"], encoding="utf-8")
    store = Store(tmp_path / "real.sqlite")
    job = publish(store, req, image_id, evidence, "container-test", "Approve fixture capture")
    assert store.work_once()
    job = store.get(job["id"])
    report = job["preview"]["capture_checks"]
    assert all(check["passed"] for check in report["checks"])
    assert report["horizontal_overflow"] is False
    assert report["dimensions"]["clientWidth"] == 800
    assert job["state"] == "AWAITING_APPROVAL"
    assert not store.work_once()
    assert store.artifact(job["id"], "screenshot.png") == evidence["screenshot.png"]

    req["source_html"] = req["source_html"].replace("</article>", """
        <style>.overflow { width: 4000px; } .hidden { display: none; }</style>
        <p class="overflow">Overflow measurement</p>
        <p class="hidden">Invisible</p>
        <img src="https://example.invalid/not-permitted.png" alt="Blocked external image">
        <script>document.querySelector('h1').textContent = 'Script executed';</script>
        </article>
    """)
    req["source_sha256"] = digest(req["source_html"])
    req["checks"].append({"selector": ".hidden", "count": 1, "text": "Invisible"})
    del req["request_sha256"]
    req["request_sha256"] = digest(canonical(req))
    adversarial = tmp_path / "adversarial"
    adversarial.mkdir()
    image_id, evidence = capture(req, adversarial)
    for name, content in evidence.items():
        (adversarial / name).write_bytes(content)
    (adversarial / "source.html").write_text(req["source_html"], encoding="utf-8")
    second = publish(store, req, image_id, evidence, "container-test", "Approve inert adversarial fixture")
    assert store.work_once()
    report = store.get(second["id"])["preview"]["capture_checks"]
    assert report["horizontal_overflow"] is True
    assert report["checks"][0]["actual_text"] == "Evidence before approval"
    assert report["checks"][0]["passed"]
    assert report["checks"][-1]["passed"] is False
    assert report["checks"][-1]["first_visible"] is False
    assert store.get(second["id"])["state"] == "AWAITING_APPROVAL"
