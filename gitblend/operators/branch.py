"""Operators: create, switch, delete, merge branches."""

from __future__ import annotations

import bpy

from gitblend.bpy_adapters import context as ctx_adapter
from gitblend.bpy_adapters import reports
from gitblend.domain.errors import NotBlenderProjectError
from gitblend.domain.result import is_ok

from ._services import get_blender_project, get_git


class GITBLEND_OT_create_branch(bpy.types.Operator):
    bl_idname = "gitblend.create_branch"
    bl_label = "Create Branch"
    bl_description = "Create a new git branch"

    branch_name: bpy.props.StringProperty(name="Branch Name", default="")  # type: ignore[valid-type]
    switch_after: bpy.props.BoolProperty(name="Switch to new branch", default=True)  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            reports.report_error(self, NotBlenderProjectError())
            return {"CANCELLED"}

        name = self.branch_name.strip()
        if not name:
            props = context.window_manager.gitblend  # type: ignore[attr-defined]
            name = props.new_branch_name.strip()
        if not name:
            self.report({"WARNING"}, "Branch name cannot be empty.")
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.create_branch(repo, name)
        if not is_ok(result):
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}

        if self.switch_after:
            switch_result = git.switch_branch(repo, name)
            if not is_ok(switch_result):
                reports.report_error(self, switch_result.error)  # type: ignore[union-attr]
                return {"CANCELLED"}

        self.report({"INFO"}, f"Branch '{name}' created.")
        bpy.ops.gitblend.refresh_status()
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.prop(self, "branch_name")
        layout.prop(self, "switch_after")


class GITBLEND_OT_switch_branch(bpy.types.Operator):
    bl_idname = "gitblend.switch_branch"
    bl_label = "Switch Branch"
    bl_description = "Switch to a different branch"

    branch_name: bpy.props.StringProperty(name="Branch Name", default="")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        name = self.branch_name
        if not name:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.switch_branch(repo, name)
        if is_ok(result):
            self.report({"INFO"}, f"Switched to branch '{name}'.")
            bpy.ops.gitblend.refresh_status()
            bpy.ops.gitblend.refresh_history()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}


class GITBLEND_OT_delete_branch(bpy.types.Operator):
    bl_idname = "gitblend.delete_branch"
    bl_label = "Delete Branch"
    bl_description = "Delete a git branch"

    branch_name: bpy.props.StringProperty(name="Branch Name", default="")  # type: ignore[valid-type]
    force: bpy.props.BoolProperty(name="Force delete", default=False)  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.delete_branch(repo, self.branch_name, force=self.force)
        if is_ok(result):
            self.report({"INFO"}, f"Branch '{self.branch_name}' deleted.")
            bpy.ops.gitblend.refresh_status()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_confirm(
            self,
            event,
            message=f"Delete branch '{self.branch_name}'?",
        )


class GITBLEND_OT_merge_branch(bpy.types.Operator):
    bl_idname = "gitblend.merge_branch"
    bl_label = "Merge Branch"
    bl_description = "Merge another branch into the current branch"

    branch_name: bpy.props.StringProperty(name="Branch to merge", default="")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.merge(repo, self.branch_name)
        if is_ok(result):
            self.report({"INFO"}, f"Merged '{self.branch_name}'.")
            bpy.ops.gitblend.refresh_status()
            bpy.ops.gitblend.refresh_history()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.prop(self, "branch_name")


classes = [
    GITBLEND_OT_create_branch,
    GITBLEND_OT_switch_branch,
    GITBLEND_OT_delete_branch,
    GITBLEND_OT_merge_branch,
]
