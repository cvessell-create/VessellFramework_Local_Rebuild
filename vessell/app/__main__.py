# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Entry point: ``python -m vessell.app`` launches the Claim Verifier web app."""

from .server import main

if __name__ == "__main__":
    raise SystemExit(main())
