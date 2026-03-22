"""Blender context helpers — wraps bpy.data, bpy.ops for blend file info."""

from __future__ import annotations

from pathlib import Path

import bpy


def get_blend_path() -> Path | None:
    """Return the absolute path of the currently open .blend file, or None."""
    filepath = getattr(bpy.data, "filepath", None)
    if not filepath:
        return None
    return Path(filepath)  # Blender provides absolute paths; avoid resolve() symlink issues on macOS


def get_blend_dir() -> Path | None:
    """Return the directory containing the open .blend file, or None."""
    path = get_blend_path()
    return path.parent if path else None


def is_saved() -> bool:
    """Return True if the current .blend file has been saved to disk."""
    return bool(getattr(bpy.data, "filepath", None))


def is_modified() -> bool:
    """Return True if the file has unsaved modifications."""
    return bool(getattr(bpy.data, "is_dirty", False))


def save_blend() -> None:
    """Save the current .blend file (no-op if not yet saved to disk)."""
    if getattr(bpy.data, "filepath", None):
        bpy.ops.wm.save_mainfile()


def get_addon_prefs() -> "bpy.types.AddonPreferences | None":
    """Return the gitblend addon preferences."""
    return bpy.context.preferences.addons.get("gitblend", None)
