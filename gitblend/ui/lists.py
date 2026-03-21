"""UIList classes for commit history, files, and branches."""

from __future__ import annotations

import bpy


class GITBLEND_UL_commits(bpy.types.UIList):
    """Commit history list."""

    bl_idname = "GITBLEND_UL_commits"

    def draw_item(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
        data: bpy.types.AnyType,
        item: bpy.types.AnyType,
        icon: int,
        active_data: bpy.types.AnyType,
        active_propname: str,
        index: int = 0,
        flt_flag: int = 0,
    ) -> None:
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text=item.short_hash, icon="DECORATE_KEYFRAME")
            row.label(text=item.message)
            row.label(text=item.date)
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text=item.short_hash)


class GITBLEND_UL_branches(bpy.types.UIList):
    """Branch list."""

    bl_idname = "GITBLEND_UL_branches"

    def draw_item(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
        data: bpy.types.AnyType,
        item: bpy.types.AnyType,
        icon: int,
        active_data: bpy.types.AnyType,
        active_propname: str,
        index: int = 0,
        flt_flag: int = 0,
    ) -> None:
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            icon_name = "LAYER_ACTIVE" if item.is_current else "LAYER_USED"
            row.label(text=item.name, icon=icon_name)


classes = [
    GITBLEND_UL_commits,
    GITBLEND_UL_branches,
]
