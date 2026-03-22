"""Centralised registration / unregistration of all Blender classes."""

from __future__ import annotations

import bpy

from .operators import (
    branch,
    commit,
    diagnostics,
    github,
    history,
    lfs,
    project,
    repos,
    restore,
    sync,
)
from .bpy_adapters import startup
from .properties import GitBlendWindowProps
from .properties import classes as property_classes
from .ui import dialogs, icons, lists, menus, panels

# All classes that need register/unregister, in dependency order.
# PropertyGroups first, then operators, then UI.
_CLASSES: list[type] = [
    *property_classes,
    *project.classes,
    *commit.classes,
    *history.classes,
    *branch.classes,
    *sync.classes,
    *lfs.classes,
    *github.classes,
    *repos.classes,
    *restore.classes,
    *diagnostics.classes,
    *lists.classes,
    *panels.classes,
    *menus.classes,
    *dialogs.classes,
]


def register() -> None:
    for cls in _CLASSES:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)

    # Register window-manager property group
    bpy.types.WindowManager.gitblend = bpy.props.PointerProperty(  # type: ignore[attr-defined]
        type=GitBlendWindowProps
    )

    # Add File menu item
    menus.register_menus()

    # Load custom icons
    icons.register_icons()

    # Restore session state on file load; also run once for the current file
    startup.register_handlers()
    # Only schedule if a file is already loaded — load_post covers future opens
    if getattr(bpy.data, "filepath", None):
        bpy.app.timers.register(startup._restore_state, first_interval=0.5)


def unregister() -> None:
    startup.unregister_handlers()
    icons.unregister_icons()
    menus.unregister_menus()

    # Remove window-manager property group
    if hasattr(bpy.types.WindowManager, "gitblend"):
        del bpy.types.WindowManager.gitblend  # type: ignore[attr-defined]

    for cls in reversed(_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
