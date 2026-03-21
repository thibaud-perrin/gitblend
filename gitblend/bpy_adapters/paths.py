"""Blender path utilities — wraps bpy.path."""

from __future__ import annotations

from pathlib import Path

import bpy


def to_absolute(path: str) -> Path:
    """Convert a Blender-relative path (//...) to an absolute Path."""
    return Path(bpy.path.abspath(path)).resolve()


def blend_to_relative(path: Path) -> str:
    """Convert an absolute path to a Blender-relative path (//...)."""
    return bpy.path.relpath(str(path))


def get_user_prefs_dir() -> Path:
    """Return the Blender user preferences directory."""
    return Path(bpy.utils.user_resource("CONFIG"))


def get_user_scripts_dir() -> Path:
    return Path(bpy.utils.user_resource("SCRIPTS"))
