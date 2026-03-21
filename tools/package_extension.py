#!/usr/bin/env python3
"""Build the gitblend Blender extension zip.

Creates dist/gitblend-<version>.zip with blender_manifest.toml at the zip root,
which is the structure required by Blender 4.2+ extensions.

Usage:
    uv run python tools/package_extension.py
    # → dist/gitblend-0.1.0.zip
"""

from __future__ import annotations

import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "gitblend"   # the package directory (contains blender_manifest.toml)
DIST = ROOT / "dist"

# Directories and files to exclude from the zip
EXCLUDE_DIRS = {"__pycache__", ".git", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".blend1", ".blend2"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db", ".gitkeep"}


def build() -> Path:
    manifest_path = SOURCE / "blender_manifest.toml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"blender_manifest.toml not found at {manifest_path}")

    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    version = manifest["version"]
    addon_id = manifest["id"]
    out = DIST / f"{addon_id}-{version}.zip"

    DIST.mkdir(parents=True, exist_ok=True)

    file_count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(SOURCE.rglob("*")):
            if path.is_dir():
                continue
            # Skip excluded directories anywhere in the path
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            # Skip excluded file extensions
            if path.suffix in EXCLUDE_SUFFIXES:
                continue
            # Skip excluded file names
            if path.name in EXCLUDE_NAMES:
                continue
            # Arc name = path relative to SOURCE (so manifest is at zip root)
            arc_name = path.relative_to(SOURCE)
            zf.write(path, arc_name)
            file_count += 1

    print(f"Built {out.name}  ({file_count} files)")
    print(f"→ {out}")
    return out


if __name__ == "__main__":
    build()
