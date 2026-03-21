"""Reusable dialog operators."""

from __future__ import annotations

import bpy


class GITBLEND_OT_confirm_destructive(bpy.types.Operator):
    """Generic confirmation dialog for destructive operations."""

    bl_idname = "gitblend.confirm_destructive"
    bl_label = "Confirm"
    bl_description = "Confirm a destructive operation"
    bl_options = {"INTERNAL"}

    message: bpy.props.StringProperty(name="Message", default="Are you sure?")  # type: ignore[valid-type]
    operator_idname: bpy.props.StringProperty(name="Operator", default="")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        if self.operator_idname:
            try:
                bpy.ops.from_string(self.operator_idname)()
            except Exception:
                pass
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.label(text=self.message, icon="ERROR")


classes = [GITBLEND_OT_confirm_destructive]
