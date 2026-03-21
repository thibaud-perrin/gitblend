"""Blender context helpers — wraps bpy.data, bpy.ops for blend file info."""

from __future__ import annotations

from pathlib import Path

import bpy


def get_blend_path() -> Path | None:
    """Return the absolute path of the currently open .blend file, or None."""
    filepath = bpy.data.filepath
    if not filepath:
        return None
    return Path(filepath).resolve()


def get_blend_dir() -> Path | None:
    """Return the directory containing the open .blend file, or None."""
    path = get_blend_path()
    return path.parent if path else None


def is_saved() -> bool:
    """Return True if the current .blend file has been saved to disk."""
    return bool(bpy.data.filepath)


def is_modified() -> bool:
    """Return True if the file has unsaved modifications."""
    return bpy.data.is_dirty


def save_blend() -> None:
    """Save the current .blend file (no-op if not yet saved to disk)."""
    if bpy.data.filepath:
        bpy.ops.wm.save_mainfile()


def get_addon_prefs() -> "bpy.types.AddonPreferences | None":
    """Return the gitblend addon preferences."""
    return bpy.context.preferences.addons.get("gitblend", None)
