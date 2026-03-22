"""Operators: stage files, unstage, commit."""

from __future__ import annotations

import bpy

from ..bpy_adapters import context as ctx_adapter
from ..bpy_adapters import reports
from ..domain.errors import NotBlenderProjectError
from ..domain.result import is_ok

from ._services import get_blender_project, get_git


class GITBLEND_OT_stage_all(bpy.types.Operator):
    bl_idname = "gitblend.stage_all"
    bl_label = "Stage All"
    bl_description = "Stage all changes (git add -A)"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            reports.report_error(self, NotBlenderProjectError())
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.stage_all(repo)
        if is_ok(result):
            self.report({"INFO"}, "All changes staged.")
            bpy.ops.gitblend.refresh_status()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}


class GITBLEND_OT_unstage_all(bpy.types.Operator):
    bl_idname = "gitblend.unstage_all"
    bl_label = "Unstage All"
    bl_description = "Unstage all staged changes"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        # unstage all = git restore --staged .
        r2 = git._runner.run_git(["restore", "--staged", "."], cwd=repo)
        if r2.failed:
            self.report({"WARNING"}, "Could not unstage all files.")
            return {"CANCELLED"}

        bpy.ops.gitblend.refresh_status()
        return {"FINISHED"}


class GITBLEND_OT_commit(bpy.types.Operator):
    bl_idname = "gitblend.commit"
    bl_label = "Commit"
    bl_description = "Commit staged changes with the current commit message"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            reports.report_error(self, NotBlenderProjectError())
            return {"CANCELLED"}

        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        message = props.commit_message.strip()
        if not message:
            self.report({"WARNING"}, "Commit message cannot be empty.")
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        # Save Blender's in-memory state then sync the sidecar so the commit
        # captures the current scene content.
        prefs = context.preferences.addons.get("gitblend")
        if prefs and getattr(prefs.preferences, "auto_save_before_commit", True):
            if ctx_adapter.is_saved():
                ctx_adapter.save_blend()
        if blend_path.exists():
            project.sync_blend_to_sidecar(blend_path)

        result = git.commit(repo, message)
        if is_ok(result):
            commit = result.value  # type: ignore[union-attr]
            self.report({"INFO"}, f"Committed: {commit.short_hash} — {commit.message}")
            props.commit_message = ""
            bpy.ops.gitblend.refresh_status()
            bpy.ops.gitblend.refresh_history()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        # Show confirmation dialog if there are staged changes
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        layout.label(text="Commit message:")
        layout.prop(props, "commit_message", text="")


classes = [
    GITBLEND_OT_stage_all,
    GITBLEND_OT_unstage_all,
    GITBLEND_OT_commit,
]
