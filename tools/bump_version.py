#!/usr/bin/env python3
"""Bump version across all project files.

Reads the version from blender_manifest.toml (single source of truth),
increments it according to semantic versioning, and updates all files
that contain version information.

Files updated:
- gitblend/blender_manifest.toml (string: "X.Y.Z")
- pyproject.toml (string: "X.Y.Z")
- gitblend/__init__.py (tuple: (X, Y, Z) in bl_info)

Usage:
    uv run python tools/bump_version.py patch        # 0.1.0 → 0.1.1
    uv run python tools/bump_version.py minor        # 0.1.0 → 0.2.0
    uv run python tools/bump_version.py major        # 0.1.0 → 1.0.0
    uv run python tools/bump_version.py patch --tag  # Also create git tag
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).parent.parent
MANIFEST_PATH = ROOT / "gitblend" / "blender_manifest.toml"
PYPROJECT_PATH = ROOT / "pyproject.toml"
INIT_PATH = ROOT / "gitblend" / "__init__.py"


@dataclass
class Version:
    """Semantic version."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version_str: str) -> Version:
        """Parse version string like '1.2.3'."""
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str.strip())
        if not match:
            raise ValueError(f"Invalid version format: {version_str!r}")
        return cls(int(match[1]), int(match[2]), int(match[3]))

    def bump(self, part: Literal["major", "minor", "patch"]) -> Version:
        """Return new version with the specified part incremented."""
        if part == "major":
            return Version(self.major + 1, 0, 0)
        elif part == "minor":
            return Version(self.major, self.minor + 1, 0)
        elif part == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        else:
            raise ValueError(f"Invalid version part: {part!r}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def to_tuple(self) -> tuple[int, int, int]:
        """Return version as tuple (X, Y, Z)."""
        return (self.major, self.minor, self.patch)


def read_current_version() -> Version:
    """Read current version from blender_manifest.toml."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    manifest = tomllib.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    version_str = manifest.get("version")
    if not version_str:
        raise ValueError("No 'version' field in blender_manifest.toml")

    return Version.parse(version_str)


def update_manifest(new_version: Version) -> None:
    """Update version in blender_manifest.toml."""
    content = MANIFEST_PATH.read_text(encoding="utf-8")
    old_pattern = re.compile(r'^version\s*=\s*"[^"]*"', re.MULTILINE)
    new_line = f'version = "{new_version}"'
    updated = old_pattern.sub(new_line, content)

    if updated == content:
        raise RuntimeError("Failed to update blender_manifest.toml (pattern not found)")

    MANIFEST_PATH.write_text(updated, encoding="utf-8")
    print(f"✓ Updated {MANIFEST_PATH.relative_to(ROOT)}")


def update_pyproject(new_version: Version) -> None:
    """Update version in pyproject.toml."""
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    old_pattern = re.compile(r'^version\s*=\s*"[^"]*"', re.MULTILINE)
    new_line = f'version = "{new_version}"'
    updated = old_pattern.sub(new_line, content)

    if updated == content:
        raise RuntimeError("Failed to update pyproject.toml (pattern not found)")

    PYPROJECT_PATH.write_text(updated, encoding="utf-8")
    print(f"✓ Updated {PYPROJECT_PATH.relative_to(ROOT)}")


def update_init(new_version: Version) -> None:
    """Update version tuple in gitblend/__init__.py bl_info."""
    content = INIT_PATH.read_text(encoding="utf-8")
    # Match the version tuple in bl_info
    old_pattern = re.compile(r'"version":\s*\(\d+,\s*\d+,\s*\d+\)')
    new_line = f'"version": {new_version.to_tuple()}'
    updated = old_pattern.sub(new_line, content)

    if updated == content:
        raise RuntimeError("Failed to update __init__.py (pattern not found)")

    INIT_PATH.write_text(updated, encoding="utf-8")
    print(f"✓ Updated {INIT_PATH.relative_to(ROOT)}")


def create_git_tag(version: Version, push: bool = False) -> None:
    """Create and optionally push a git tag."""
    tag_name = f"v{version}"

    # Check if tag already exists
    result = subprocess.run(
        ["git", "tag", "-l", tag_name],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    if result.stdout.strip():
        print(f"⚠ Tag {tag_name} already exists")
        return

    # Create tag
    subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", f"Release {version}"],
        cwd=ROOT,
        check=True,
    )
    print(f"✓ Created git tag: {tag_name}")

    if push:
        subprocess.run(["git", "push", "origin", tag_name], cwd=ROOT, check=True)
        print(f"✓ Pushed tag {tag_name} to origin")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump version across all project files")
    parser.add_argument(
        "part",
        choices=["major", "minor", "patch"],
        help="Version part to bump",
    )
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Create git tag after bumping version",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push git tag to origin (implies --tag)",
    )
    args = parser.parse_args()

    # Read current version
    try:
        current = read_current_version()
    except Exception as e:
        print(f"Error reading current version: {e}", file=sys.stderr)
        sys.exit(1)

    # Calculate new version
    new = current.bump(args.part)

    print(f"Bumping version: {current} → {new}")
    print()

    # Update all files
    try:
        update_manifest(new)
        update_pyproject(new)
        update_init(new)
    except Exception as e:
        print(f"\n❌ Error updating files: {e}", file=sys.stderr)
        print("Some files may be in an inconsistent state. Please check git diff.")
        sys.exit(1)

    print()
    print(f"✅ Version bumped to {new}")

    # Create git tag if requested
    if args.tag or args.push:
        print()
        try:
            create_git_tag(new, push=args.push)
        except subprocess.CalledProcessError as e:
            print(f"\n⚠ Failed to create/push git tag: {e}", file=sys.stderr)
            print("Version files were updated successfully.")
            sys.exit(1)

    # Show next steps
    print()
    print("Next steps:")
    print(f"  git add {MANIFEST_PATH.relative_to(ROOT)} {PYPROJECT_PATH.relative_to(ROOT)} {INIT_PATH.relative_to(ROOT)}")
    print(f'  git commit -m "chore: bump version to {new}"')
    if not (args.tag or args.push):
        print(f"  git tag -a v{new} -m 'Release {new}'")
        print(f"  git push origin v{new}")


if __name__ == "__main__":
    main()
