# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""VessellFramework Claim Verifier web app.

A working application, not a demo: an interactive front end over the real
``vessell/verify.py`` doctrine — claim corroboration, hostile-spread
(planted-news) analysis, and ghost-job filtering. Standard library only;
from a checkout with Python 3.13+.

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
import logging
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from vessell.provenance import SourceStatus
from vessell.verify import (
    ClaimCheck,
    JobPosting,
    SourceSighting,
    analyze_planted_news,
    detect_ghost_job,
    group_postings_by_role,
    verify_claim,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_PORT = 8765
MAX_BODY_BYTES = 64 * 1024
MAX_ENTRIES = 100
logger = logging.getLogger(__name__)

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
    if isinstance(value, str):
        key = value.strip().lower()
        if key in {"1", "true", "yes", "y"}:
            return True
        if key in {"0", "false", "no", "n"}:
            return False
    raise ValueError("Boolean fields require true/false or an explicit yes/no value.")


def _text(raw: dict[str, Any], name: str, maximum: int, *, required: bool = False) -> str:
    value = raw.get(name, "")
    if not isinstance(value, str):
        raise TypeError(f"'{name}' must be a string.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"'{name}' must be non-empty.")
    if len(value) > maximum:
        raise ValueError(f"'{name}' exceeds {maximum} characters.")
    return value


def _check_fields(raw: dict[str, Any], allowed: set[str]) -> None:
    unknown = raw.keys() - allowed
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(sorted(unknown))}.")


def _date_text(raw: dict[str, Any], name: str, *, posting: bool = False) -> str:
    value = _text(raw, name, 64)
    if value:
        try:
            if posting:
                date.fromisoformat(value[:10])
            else:
                datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"'{name}' must be an ISO date or timestamp.") from error
    return value


def build_sighting(raw: dict[str, Any]) -> SourceSighting:
    """Build a SourceSighting from a JSON object; raises TypeError/ValueError."""
    if not isinstance(raw, dict):
        raise TypeError("Each sighting must be a JSON object.")
    _check_fields(raw, {
        "source_name", "tier", "url", "seen_at", "published_at", "text", "root",
        "denies", "is_official_record", "note", "event_clock",
    })
    source_name = _text(raw, "source_name", 200, required=True)
    return SourceSighting(
        source_name=source_name,
        tier=parse_tier(raw.get("tier")),
        url=_text(raw, "url", 2048),
        seen_at=_date_text(raw, "seen_at"),
        published_at=_date_text(raw, "published_at"),
        text=_text(raw, "text", 10_000),
        root=_text(raw, "root", 200) or None,
        denies=_as_bool(raw.get("denies", False)),
        is_official_record=_as_bool(raw.get("is_official_record", False)),
        note=_text(raw, "note", 2000),
        event_clock=_text(raw, "event_clock", 80) or None,
    )


def build_claim_check(payload: dict[str, Any]) -> ClaimCheck:
    """Build a ClaimCheck from a JSON payload; raises TypeError/ValueError."""
    if not isinstance(payload, dict):
        raise TypeError("Request body must be a JSON object.")
    _check_fields(payload, {"claim", "sightings"})
    claim = _text(payload, "claim", 2000, required=True)
    raw_sightings = payload.get("sightings", [])
    if not isinstance(raw_sightings, list):
        raise TypeError("'sightings' must be a JSON array.")
    if len(raw_sightings) > MAX_ENTRIES:
        raise ValueError(f"'sightings' exceeds {MAX_ENTRIES} entries.")
    return ClaimCheck(
        claim=claim,
        sightings=tuple(build_sighting(s) for s in raw_sightings),
    )


def build_posting(raw: dict[str, Any]) -> JobPosting:
    """Build a JobPosting from a JSON object; raises TypeError/ValueError."""
    if not isinstance(raw, dict):
        raise TypeError("Each posting must be a JSON object.")
    _check_fields(raw, {
        "title", "employer", "location", "description_text", "salary_text", "source",
        "listing_id", "claimed_posted", "first_seen", "url",
    })
    title = _text(raw, "title", 300)
    employer = _text(raw, "employer", 300)
    location = _text(raw, "location", 300)
    description_text = _text(raw, "description_text", 10_000)
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
        salary_text=_text(raw, "salary_text", 500),
        source=_text(raw, "source", 200),
        listing_id=_text(raw, "listing_id", 300),
        claimed_posted=_date_text(raw, "claimed_posted", posting=True),
        first_seen=_date_text(raw, "first_seen", posting=True),
        url=_text(raw, "url", 2048),
    )


def build_postings(payload: dict[str, Any]) -> list[JobPosting]:
    """Build a posting list from a JSON payload; raises TypeError/ValueError."""
    if not isinstance(payload, dict):
        raise TypeError("Request body must be a JSON object.")
    _check_fields(payload, {"postings"})
    raw_postings = payload.get("postings")
    if not isinstance(raw_postings, list):
        raise TypeError("'postings' must be a JSON array.")
    if not raw_postings:
        raise ValueError("'postings' must be a non-empty JSON array.")
    if len(raw_postings) > MAX_ENTRIES:
        raise ValueError(f"'postings' exceeds {MAX_ENTRIES} entries.")
    return [build_posting(p) for p in raw_postings]


class VerifierHandler(BaseHTTPRequestHandler):
    """Serves the UI and the verification JSON API."""

    server_version = "VessellVerifier/1.0"

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        )
        super().end_headers()

    def _local_request(self) -> bool:
        hosts = self.headers.get_all("Host", [])
        origin = self.headers.get("Origin")
        try:
            host = urlsplit(f"//{hosts[0]}") if len(hosts) == 1 else None
            valid = (
                host is not None
                and host.hostname in {"127.0.0.1", "localhost"}
                and host.port == self.connection.getsockname()[1]
                and host.username is None
                and host.password is None
                and not host.path
                and not host.query
                and not host.fragment
            )
        except ValueError:
            valid = False
        if not valid or (origin is not None and origin != f"http://{hosts[0]}"):
            self._send_json({"error": "Only same-origin loopback requests are accepted."}, 403)
            return False
        return True

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
        if self._local_request():
            self._serve_static()

    def do_POST(self) -> None:
        if not self._local_request():
            return
        if self.path not in {"/api/verify", "/api/planted-news", "/api/ghost-job"}:
            self._send_json({"error": "Unknown endpoint."}, 404)
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json({"error": "Content-Type must be application/json."}, 415)
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
            self._send_json({"error": "One Content-Length is required; transfer encoding is unsupported."}, 400)
            return
        try:
            if not lengths[0].isascii() or not lengths[0].isdigit():
                raise ValueError
            length = int(lengths[0])
        except ValueError:
            self._send_json({"error": "Invalid Content-Length."}, 400)
            return
        if length > MAX_BODY_BYTES:
            self._send_json({"error": f"Body exceeds {MAX_BODY_BYTES} bytes."}, 413)
            return
        self.connection.settimeout(10)
        try:
            raw_body = self.rfile.read(length)
        except TimeoutError:
            self._send_json({"error": "Request body timed out."}, 408)
            return
        if len(raw_body) != length:
            self._send_json({"error": "Incomplete request body."}, 400)
            return
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
                postings = build_postings(payload)
                if len(group_postings_by_role(postings)) != 1:
                    raise ValueError("Compare postings for one employer/title/location per request.")
                result = detect_ghost_job(postings).to_dict()
            else:
                self._send_json({"error": f"Unknown endpoint: {self.path}"}, status=404)
                return
        except (ValueError, TypeError) as error:
            self._send_json({"error": str(error)}, status=400)
            return
        result.update({
            "source_access": "NOT_PERFORMED",
            "note": "Only supplied records were analyzed; URLs were not fetched or authenticated.",
            "release_status": "ANALYSIS_ONLY_NOT_RELEASED",
        })
        self._send_json(result)

    def log_message(self, fmt: str, *args: object) -> None:
        logger.info("%s", fmt % args)


def run_server(port: int = DEFAULT_PORT, open_browser: bool = True) -> ThreadingHTTPServer:
    """Start the verifier app; returns the server (caller owns shutdown)."""
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
