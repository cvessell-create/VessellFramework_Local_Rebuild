"""Trusted container entrypoint; only HTML data is accepted, not programs."""
from __future__ import annotations

import base64
import json
import sys

from playwright.sync_api import Route, sync_playwright


def main() -> None:
    raw = sys.stdin.buffer.read(65537)
    if len(raw) > 65536:
        raise ValueError("Capture request exceeds 64 KiB")
    request = json.loads(raw)
    with sync_playwright() as engine:
        browser = engine.chromium.launch(executable_path="/usr/bin/chromium")
        context = browser.new_context(
            viewport=request["viewport"], java_script_enabled=False,
            offline=True, service_workers="block", device_scale_factor=1,
        )
        page = context.new_page()
        served = False

        def serve(route: Route) -> None:
            nonlocal served
            if (
                not served and route.request.url == "http://snapshot.invalid/"
                and route.request.is_navigation_request() and route.request.frame == page.main_frame
            ):
                served = True
                route.fulfill(
                    body=request["source_html"], content_type="text/html; charset=utf-8",
                    headers={"Content-Security-Policy": (
                        "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
                        "base-uri 'none'; form-action 'none'"
                    )},
                )
            else:
                route.abort()

        context.route("**/*", serve)
        page.goto("http://snapshot.invalid/", wait_until="load", timeout=10000)
        checks = []
        for check in request["checks"]:
            locator = page.locator("css=" + check["selector"])
            count = locator.count()
            text = locator.first.inner_text(timeout=1000) if count else ""
            visible = bool(count and locator.first.is_visible())
            checks.append({
                **check, "actual_count": count, "actual_text": text[:2000], "first_visible": visible,
                "passed": count == check["count"] and (check["count"] == 0 or visible) and (
                    check["text"] is None or text.strip() == check["text"]
                ),
            })
        dimensions = page.evaluate("""() => ({
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
            scrollHeight: document.documentElement.scrollHeight,
            clientHeight: document.documentElement.clientHeight
        })""")
        screenshot = page.screenshot(type="png", full_page=False, animations="disabled")
        if len(screenshot) > 8 * 1024 * 1024:
            raise ValueError("Screenshot exceeds 8 MiB")
        report = {
            "request_sha256": request["request_sha256"], "viewport": request["viewport"],
            "request": request,
            "browser_version": browser.version,
            "checks": checks, "dimensions": dimensions,
            "horizontal_overflow": dimensions["scrollWidth"] > dimensions["clientWidth"],
            "model_status": "not_configured",
            "scope": "Measured static output, not semantic correctness or code-diff proof.",
        }
        print(json.dumps({
            "screenshot": base64.b64encode(screenshot).decode("ascii"),
            "report": report,
            "log": "Static Chromium capture completed; scripts, network and service workers disabled.\n",
        }))
        browser.close()


if __name__ == "__main__":
    main()
