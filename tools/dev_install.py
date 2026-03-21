#!/usr/bin/env python3
"""Install gitblend for development via a symlink into Blender's addons directory.

Creates a symlink:
  <blender_user_scripts>/addons/gitblend  →  <repo>/gitblend/gitblend

This lets you edit source files and reload the addon in Blender without
rebuilding the zip each time.

Usage:
    uv run python tools/dev_install.py
    uv run python tools/dev_install.py --blender /path/to/Blender.app
    uv run python tools/dev_install.py --uninstall
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path

ADDON_NAME = "gitblend"
REPO_ROOT = Path(__file__).parent.parent
SOURCE = REPO_ROOT / "gitblend"   # the package to symlink


def find_blender_addons_dir(blender_app: Path | None = None) -> Path:
    """Locate Blender's user addons directory.

    Search order:
      1. Explicitly provided --blender path
      2. Standard OS-specific user config locations
    """
    system = platform.system()

    if blender_app:
        # Try to find scripts/addons relative to the app
        candidates = list(blender_app.rglob("scripts/addons"))
        if candidates:
            return candidates[0]
        raise FileNotFoundError(f"Could not find scripts/addons inside {blender_app}")

    # Discover default Blender user config dirs
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "Blender"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        base = Path(appdata) / "Blender Foundation" / "Blender"
    else:
        # Linux / XDG
        xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        base = Path(xdg) / "blender"

    if not base.exists():
        raise FileNotFoundError(
            f"Blender config directory not found at {base}.\n"
            "Use --blender /path/to/Blender.app to specify the location."
        )

    # Find the most recent version directory
    version_dirs = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name[0].isdigit()],
        reverse=True,
    )
    if not version_dirs:
        raise FileNotFoundError(f"No Blender version found in {base}")

    addons_dir = version_dirs[0] / "scripts" / "addons"
    return addons_dir


def install(blender_app: Path | None = None) -> None:
    addons_dir = find_blender_addons_dir(blender_app)
    addons_dir.mkdir(parents=True, exist_ok=True)

    link = addons_dir / ADDON_NAME

    if link.exists() or link.is_symlink():
        if link.is_symlink():
            current_target = link.resolve()
            if current_target == SOURCE.resolve():
                print(f"Already installed: {link} → {SOURCE}")
                return
            print(f"Removing existing symlink: {link} → {link.resolve()}")
            link.unlink()
        else:
            raise FileExistsError(
                f"{link} exists and is not a symlink. Remove it manually before installing."
            )

    if platform.system() == "Windows":
        # Windows requires elevated privileges for symlinks; fall back to junction
        try:
            import subprocess
            subprocess.run(
                ["mklink", "/J", str(link), str(SOURCE)],
                shell=True,
                check=True,
            )
        except Exception as e:
            raise RuntimeError(
                "Could not create junction. Run as Administrator or enable Developer Mode."
            ) from e
    else:
        link.symlink_to(SOURCE.resolve())

    print(f"Installed: {link}")
    print(f"        → {SOURCE.resolve()}")
    print()
    print("Reload the addon in Blender: Edit → Preferences → Add-ons → gitblend → Reload")


def uninstall(blender_app: Path | None = None) -> None:
    addons_dir = find_blender_addons_dir(blender_app)
    link = addons_dir / ADDON_NAME

    if link.is_symlink():
        link.unlink()
        print(f"Removed: {link}")
    elif link.exists():
        print(f"{link} exists but is not a symlink — remove manually.")
    else:
        print(f"Not installed at {link}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--blender",
        metavar="PATH",
        type=Path,
        help="Path to Blender.app or Blender installation directory",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the development symlink",
    )
    args = parser.parse_args()

    try:
        if args.uninstall:
            uninstall(args.blender)
        else:
            install(args.blender)
    except (FileNotFoundError, FileExistsError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
