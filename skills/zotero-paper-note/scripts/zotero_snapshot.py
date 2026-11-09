#!/usr/bin/env python3
"""Create a consistent read-only snapshot of a local Zotero database."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path


def resolve_zotero_dir(value: str | None) -> Path:
    raw = value or os.environ.get("ZOTERO_DATA_DIR")
    if not raw:
        candidate = Path.home() / "Zotero"
        if candidate.is_dir():
            return candidate.resolve()
        raise ValueError("set ZOTERO_DATA_DIR or pass --zotero-dir")
    return Path(raw).expanduser().resolve()


def create_snapshot(zotero_dir: Path, output: str | None) -> Path:
    source = zotero_dir / "zotero.sqlite"
    storage = zotero_dir / "storage"
    if not source.is_file():
        raise FileNotFoundError(f"Zotero database not found: {source}")
    if not storage.is_dir():
        raise FileNotFoundError(f"Zotero storage directory not found: {storage}")

    if output:
        destination = Path(output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite: {destination}")
    else:
        workspace = Path(tempfile.mkdtemp(prefix="zotero-query-"))
        destination = workspace / "zotero.sqlite"

    source_wal = Path(f"{source}-wal")
    destination_wal = Path(f"{destination}-wal")
    for attempt in range(3):
        tracked = [path for path in (source, source_wal) if path.exists()]
        before = {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in tracked}
        shutil.copy2(source, destination)
        if source_wal.exists():
            shutil.copy2(source_wal, destination_wal)
        else:
            destination_wal.unlink(missing_ok=True)
        after = {
            path: (path.stat().st_size, path.stat().st_mtime_ns)
            for path in tracked
            if path.exists()
        }
        if before == after:
            try:
                with sqlite3.connect(destination) as snapshot_db:
                    result = snapshot_db.execute("PRAGMA quick_check").fetchone()
                if result and result[0] == "ok":
                    return destination
            except sqlite3.Error:
                pass
        destination.unlink(missing_ok=True)
        destination_wal.unlink(missing_ok=True)
        time.sleep(0.2 * (attempt + 1))

    raise sqlite3.OperationalError("could not create a stable Zotero snapshot after 3 attempts")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zotero-dir", help="Zotero data directory")
    parser.add_argument("--output", help="explicit snapshot path; must not exist")
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    args = parser.parse_args()

    try:
        zotero_dir = resolve_zotero_dir(args.zotero_dir)
        snapshot = create_snapshot(zotero_dir, args.output)
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.exit(1, f"error: {exc}\n")

    if args.json:
        print(json.dumps({
            "database": str(snapshot),
            "storage": str(zotero_dir / "storage"),
            "workspace": str(snapshot.parent),
        }))
    else:
        print(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
