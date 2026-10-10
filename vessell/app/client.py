# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Programmatic client for the Claim Verifier web app. Standard library only.

Two ways to drive the app from Python::

    # 1. In-process: a loopback HTTP server runs in a background thread.
    from vessell.app.client import launch

    with launch() as client:
        report = client.verify(
            claim="M4.2 earthquake near Wauna, WA",
            sightings=[
                {"source_name": "USGS", "tier": "SOURCE-ESTABLISHED",
                 "is_official_record": True},
                {"source_name": "KOMO", "tier": "SOURCE-ESTABLISHED"},
            ],
        )
        print(report["verdict"])  # VERIFIED

    # 2. Against a running server (e.g. started with ``python -m vessell.app``):
    from vessell.app.client import VerifierClient

    client = VerifierClient("http://127.0.0.1:8765")
    report = client.ghost_job(postings=[...])

Sightings and postings are plain dicts in the API shape documented in
``vessell/app/server.py``. Every method returns the decoded JSON report
dict; API errors raise :class:`VerifierError`.
"""

from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .server import VerifierHandler


class VerifierError(Exception):
    """The verifier API rejected the request (bad input or unknown endpoint)."""


class VerifierClient:
    """Thin JSON client for a running Claim Verifier server."""

    def __init__(self, base_url: str = "http://127.0.0.1:8765") -> None:
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                decoded: Any = json.loads(response.read().decode("utf-8"))
                if not isinstance(decoded, dict):
                    raise VerifierError(f"{path}: unexpected non-object response")
                return decoded
        except HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8"))
                message = detail.get("error", error.reason) if isinstance(detail, dict) else error.reason
            except (ValueError, UnicodeDecodeError):
                message = error.reason
            raise VerifierError(f"{path} -> HTTP {error.code}: {message}") from error

    def verify(self, claim: str, sightings: list[dict[str, Any]]) -> dict[str, Any]:
        """Corroboration verdict for one claim; see VerificationResult.to_dict()."""
        return self._post("/api/verify", {"claim": claim, "sightings": sightings})

    def planted_news(
        self, claim: str, sightings: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Hostile-spread analysis; see PlantedNewsReport.to_dict()."""
        return self._post("/api/planted-news", {"claim": claim, "sightings": sightings})

    def ghost_job(self, postings: list[dict[str, Any]]) -> dict[str, Any]:
        """Ghost-job verdict for one role's postings; see GhostJobReport.to_dict()."""
        return self._post("/api/ghost-job", {"postings": postings})


class _LaunchedApp:
    """Context manager: runs the verifier server in a background thread."""

    def __init__(self, port: int = 0) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", port), VerifierHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self.client = VerifierClient(
            f"http://127.0.0.1:{self._server.server_port}"
        )

    @property
    def url(self) -> str:
        return self.client.base_url + "/"

    def __enter__(self) -> VerifierClient:
        self._thread.start()
        return self.client

    def __exit__(self, *exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def launch(port: int = 0) -> _LaunchedApp:
    """Start the Claim Verifier in-process and return a context manager.

    ``port=0`` picks a free ephemeral port. Use as::

        with launch() as client:
            client.verify(...)
    """
    return _LaunchedApp(port)
