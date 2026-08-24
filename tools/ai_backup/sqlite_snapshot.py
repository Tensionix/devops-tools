"""Create a consistent copy of a possibly live SQLite database."""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path


SQLITE_HEADER = b"SQLite format 3\x00"


def snapshot(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()

    with source.open("rb") as stream:
        header = stream.read(len(SQLITE_HEADER))
    if header != SQLITE_HEADER:
        shutil.copy2(source, destination)
        return

    source_uri = source.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(source_uri, uri=True, timeout=30.0) as live:
        with sqlite3.connect(destination, timeout=30.0) as copy:
            live.backup(copy)
            result = copy.execute("PRAGMA integrity_check").fetchone()
            if not result or str(result[0]).lower() != "ok":
                raise RuntimeError(f"SQLite integrity_check failed for {source}: {result}")
    shutil.copystat(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("snapshot")
    command.add_argument("--source", required=True, type=Path)
    command.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    snapshot(args.source, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
