"""File menu additions for gitblend."""

from __future__ import annotations

import bpy


class GITBLEND_MT_file_menu(bpy.types.Menu):
    """Git submenu in the File menu."""

    bl_idname = "GITBLEND_MT_file_menu"
    bl_label = "Git"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.operator("gitblend.refresh_status", text="Refresh Status", icon="FILE_REFRESH")
        layout.separator()
        layout.operator("gitblend.stage_all", text="Stage All", icon="ADD")
        layout.operator("gitblend.commit", text="Commit…", icon="FILE_TICK")
        layout.separator()
        layout.operator("gitblend.pull", text="Pull", icon="TRIA_DOWN")
        layout.operator("gitblend.push", text="Push", icon="TRIA_UP")
        layout.separator()
        layout.operator("gitblend.audit_project", text="Audit Project…", icon="VIEWZOOM")
        layout.separator()
        layout.operator("gitblend.open_github", text="Open on GitHub", icon="URL")


def _file_menu_draw(self: bpy.types.Menu, context: bpy.types.Context) -> None:
    self.layout.menu("GITBLEND_MT_file_menu", icon="BOOKMARKS")


def register_menus() -> None:
    bpy.types.TOPBAR_MT_file.append(_file_menu_draw)


def unregister_menus() -> None:
    bpy.types.TOPBAR_MT_file.remove(_file_menu_draw)


classes = [GITBLEND_MT_file_menu]
