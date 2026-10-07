from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from .store import MissingJob, Store


def main() -> int:
    parser = argparse.ArgumentParser(prog="vessell-ambient")
    parser.add_argument("--database", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("status")
    commands.add_parser("verify")
    prune = commands.add_parser("prune")
    prune.add_argument("--days", type=int, required=True)
    prune.add_argument("--apply", action="store_true", help="Delete eligible terminal jobs")
    reset = commands.add_parser("reset")
    reset.add_argument("--confirm-path", required=True)
    args = parser.parse_args()
    try:
        if args.command != "init" and not args.database.is_file():
            raise ValueError("Database must already exist")
        store = Store(args.database)
        if args.command == "init":
            print(f"Initialized ambient database: {store.path}")
        elif args.command == "status":
            print(json.dumps(store.stats(), indent=2))
        elif args.command == "verify":
            cursor = None
            count = 0
            while batch := store.list_jobs(100, cursor):
                count += len(batch)
                cursor = batch[-1]["id"]
            print(f"Verified {count} durable workflow histories")
        elif args.command == "prune":
            count = store.prune(args.days, args.apply)
            print(f"{'Deleted' if args.apply else 'Would delete'} {count} terminal jobs; "
                  "their delivery keys/history are removed, so later replay can create new jobs.")
        else:
            store.reset(args.confirm_path)
            print("Reset terminal workflow history; delivery replay can create new jobs.")
        return 0
    except (ValueError, KeyError, MissingJob, OSError, sqlite3.Error) as error:
        print(f"AMBIENT FAILED: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
