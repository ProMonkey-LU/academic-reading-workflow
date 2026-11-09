#!/usr/bin/env python3
"""Check local prerequisites for the personal academic skills without writing data."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from pathlib import Path


def report(level: str, message: str) -> None:
    print(f"{level:<5} {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", help="override OBSIDIAN_VAULT_PATH")
    parser.add_argument("--zotero-dir", help="override ZOTERO_DATA_DIR")
    args = parser.parse_args()

    errors = 0
    report("OK", f"Python {sys.version.split()[0]} ({sys.executable})")
    if sys.version_info < (3, 9):
        report("ERROR", "Python 3.9 or newer is required")
        errors += 1

    for executable in ("git", "rg"):
        path = shutil.which(executable)
        if path:
            report("OK", f"{executable}: {path}")
        else:
            level = "ERROR" if executable == "git" else "WARN"
            report(level, f"{executable} is not available on PATH")
            errors += executable == "git"

    for module, package, required in (
        ("yaml", "PyYAML", True),
        ("requests", "requests", True),
        ("fitz", "PyMuPDF", False),
    ):
        if importlib.util.find_spec(module):
            report("OK", f"Python package: {package}")
        else:
            level = "ERROR" if required else "WARN"
            report(level, f"Python package missing: {package}")
            errors += required

    vault_raw = args.vault or os.environ.get("OBSIDIAN_VAULT_PATH")
    if not vault_raw:
        report("ERROR", "OBSIDIAN_VAULT_PATH is not set")
        errors += 1
    else:
        vault = Path(vault_raw).expanduser()
        config = vault / "99_System" / "Config" / "research_interests.yaml"
        if vault.is_dir():
            report("OK", f"Obsidian vault: {vault.resolve()}")
        else:
            report("ERROR", f"Obsidian vault not found: {vault}")
            errors += 1
        if config.is_file():
            report("OK", f"research profile: {config}")
        else:
            report("ERROR", f"research profile not found: {config}")
            errors += 1

    zotero_raw = args.zotero_dir or os.environ.get("ZOTERO_DATA_DIR")
    zotero = Path(zotero_raw).expanduser() if zotero_raw else Path.home() / "Zotero"
    database = zotero / "zotero.sqlite"
    storage = zotero / "storage"
    if database.is_file() and storage.is_dir():
        report("OK", f"Zotero data: {zotero.resolve()}")
    else:
        report("WARN", f"Zotero SQLite fallback unavailable at: {zotero}")

    if os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        report("OK", "SEMANTIC_SCHOLAR_API_KEY is set")
    else:
        report("WARN", "SEMANTIC_SCHOLAR_API_KEY is not set; public limits will apply")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
