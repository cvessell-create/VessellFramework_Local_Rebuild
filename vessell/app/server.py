# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""VessellFramework Claim Verifier web app.

A working application, not a demo: an interactive front end over the real
``vessell/verify.py`` doctrine — claim corroboration, hostile-spread
(planted-news) analysis, and ghost-job filtering. Standard library only;
no install step beyond Python 3.12+.

Launch it with::

    python -m vessell.app

then open http://127.0.0.1:8765/ in a browser.

JSON API (all POST, ``Content-Type: application/json``):

- ``/api/verify`` — ``{"claim": str, "sightings": [sighting, ...]}`` →
  ``VerificationResult.to_dict()``
- ``/api/planted-news`` — same payload →
  ``PlantedNewsReport.to_dict()``
- ``/api/ghost-job`` — ``{"postings": [posting, ...]}`` →
  ``GhostJobReport.to_dict()``

A sighting carries ``source_name`` (required), ``tier`` (one of
``SOURCE-ESTABLISHED``, ``FRAMEWORK SYNTHESIS``, ``WORKING HYPOTHESIS``,
``ILLUSTRATIVE`` — hyphens, spaces, or underscores all accepted),
``url``, ``seen_at``, ``published_at``, ``text``, ``root``, ``denies``,
``is_official_record``, ``note``. A posting carries ``title``,
``employer``, ``location``, ``description_text`` (all required) plus
``salary_text``, ``source``, ``listing_id``, ``claimed_posted``,
``first_seen``, ``url``.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from vessell.provenance import SourceStatus
from vessell.verify import (
    ClaimCheck,
    JobPosting,
    SourceSighting,
    analyze_planted_news,
    detect_ghost_job,
    verify_claim,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_PORT = 8765

def parse_tier(raw: object) -> SourceStatus:
    """Parse a source tier from loose user input; raises ValueError."""
    key = str(raw or "").strip().upper()
    key = key.replace("-", " ").replace("_", " ")
    key = " ".join(key.split())
    mapping = {
        "SOURCE ESTABLISHED": SourceStatus.SOURCE_ESTABLISHED,
        "ESTABLISHED": SourceStatus.SOURCE_ESTABLISHED,
        "FRAMEWORK SYNTHESIS": SourceStatus.FRAMEWORK_SYNTHESIS,
        "SYNTHESIS": SourceStatus.FRAMEWORK_SYNTHESIS,
        "WORKING HYPOTHESIS": SourceStatus.WORKING_HYPOTHESIS,
        "HYPOTHESIS": SourceStatus.WORKING_HYPOTHESIS,
        "ILLUSTRATIVE": SourceStatus.ILLUSTRATIVE,
    }
    if key in mapping:
        return mapping[key]
    raise ValueError(
        f"Unknown source tier: {raw!r}. Use SOURCE-ESTABLISHED, "
        "FRAMEWORK SYNTHESIS, WORKING HYPOTHESIS, or ILLUSTRATIVE."
    )


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def build_sighting(raw: dict[str, Any]) -> SourceSighting:
    """Build a SourceSighting from a JSON object; raises TypeError/ValueError."""
    if not isinstance(raw, dict):
        raise TypeError("Each sighting must be a JSON object.")
    source_name = str(raw.get("source_name") or "").strip()
    if not source_name:
        raise ValueError("Each sighting needs a source_name.")
    return SourceSighting(
        source_name=source_name,
        tier=parse_tier(raw.get("tier")),
        url=str(raw.get("url") or ""),
        seen_at=str(raw.get("seen_at") or ""),
        published_at=str(raw.get("published_at") or ""),
        text=str(raw.get("text") or ""),
        root=str(raw.get("root") or "") or None,
        denies=_as_bool(raw.get("denies")),
        is_official_record=_as_bool(raw.get("is_official_record")),
        note=str(raw.get("note") or ""),
    )


def build_claim_check(payload: dict[str, Any]) -> ClaimCheck:
    """Build a ClaimCheck from a JSON payload; raises TypeError/ValueError."""
    if not isinstance(payload, dict):
        raise TypeError("Request body must be a JSON object.")
    claim = str(payload.get("claim") or "").strip()
    if not claim:
        raise ValueError("Request needs a non-empty 'claim' string.")
    raw_sightings = payload.get("sightings") or []
    if not isinstance(raw_sightings, list):
        raise TypeError("'sightings' must be a JSON array.")
    return ClaimCheck(
        claim=claim,
        sightings=tuple(build_sighting(s) for s in raw_sightings),
    )


def build_posting(raw: dict[str, Any]) -> JobPosting:
    """Build a JobPosting from a JSON object; raises TypeError/ValueError."""
    if not isinstance(raw, dict):
        raise TypeError("Each posting must be a JSON object.")
    title = str(raw.get("title") or "").strip()
    employer = str(raw.get("employer") or "").strip()
    location = str(raw.get("location") or "").strip()
    description_text = str(raw.get("description_text") or "").strip()
    missing = [
        name
        for name, value in (
            ("title", title),
            ("employer", employer),
            ("location", location),
            ("description_text", description_text),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"Each posting needs: {', '.join(missing)}.")
    return JobPosting(
        title=title,
        employer=employer,
        location=location,
        description_text=description_text,
        salary_text=str(raw.get("salary_text") or ""),
        source=str(raw.get("source") or ""),
        listing_id=str(raw.get("listing_id") or ""),
        claimed_posted=str(raw.get("claimed_posted") or ""),
        first_seen=str(raw.get("first_seen") or ""),
        url=str(raw.get("url") or ""),
    )


def build_postings(payload: dict[str, Any]) -> list[JobPosting]:
    """Build a posting list from a JSON payload; raises TypeError/ValueError."""
    if not isinstance(payload, dict):
        raise TypeError("Request body must be a JSON object.")
    raw_postings = payload.get("postings")
    if not isinstance(raw_postings, list):
        raise TypeError("'postings' must be a JSON array.")
    if not raw_postings:
        raise ValueError("'postings' must be a non-empty JSON array.")
    return [build_posting(p) for p in raw_postings]


class VerifierHandler(BaseHTTPRequestHandler):
    """Serves the UI and the verification JSON API."""

    server_version = "VessellVerifier/1.0"

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self) -> None:
        if self.path in ("/", "/index.html"):
            target = STATIC_DIR / "index.html"
        else:
            target = (STATIC_DIR / self.path.lstrip("/")).resolve()
            try:
                target.relative_to(STATIC_DIR.resolve())
            except ValueError:
                self.send_error(403, "Forbidden")
                return
        if not target.is_file():
            self.send_error(404, "Not found")
            return
        content_type = "text/html; charset=utf-8" if target.suffix == ".html" else \
            "text/css; charset=utf-8" if target.suffix == ".css" else \
            "application/javascript; charset=utf-8" if target.suffix == ".js" else \
            "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self._serve_static()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            self._send_json({"error": f"Invalid JSON body: {error}"}, status=400)
            return
        try:
            if self.path == "/api/verify":
                result = verify_claim(build_claim_check(payload)).to_dict()
            elif self.path == "/api/planted-news":
                result = analyze_planted_news(build_claim_check(payload)).to_dict()
            elif self.path == "/api/ghost-job":
                result = detect_ghost_job(build_postings(payload)).to_dict()
            else:
                self._send_json({"error": f"Unknown endpoint: {self.path}"}, status=404)
                return
        except (ValueError, TypeError) as error:
            self._send_json({"error": str(error)}, status=400)
            return
        self._send_json(result)

    def log_message(self, fmt: str, *args: object) -> None:
        # Quieter than the default BaseHTTPRequestHandler logging.
        pass


def run_server(port: int = DEFAULT_PORT, open_browser: bool = True) -> ThreadingHTTPServer:
    """Start the verifier app; returns the server (caller owns shutdown)."""
    import webbrowser  # lazy: not needed for the API or the browser bundle

    server = ThreadingHTTPServer(("127.0.0.1", port), VerifierHandler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"VessellFramework Claim Verifier running at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    return server


def main() -> int:
    server = run_server()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
