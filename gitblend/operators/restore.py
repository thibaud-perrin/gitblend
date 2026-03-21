"""Operators: checkout ref, revert file, revert commit.

All destructive restore operations back up the .blend file first.
"""

from __future__ import annotations

import bpy

from ..bpy_adapters import context as ctx_adapter
from ..bpy_adapters import reports
from ..domain.errors import NotBlenderProjectError
from ..domain.result import is_ok

from ._services import get_blender_project, get_git, get_snapshot


class GITBLEND_OT_checkout_ref(bpy.types.Operator):
    bl_idname = "gitblend.checkout_ref"
    bl_label = "Checkout"
    bl_description = "Checkout a commit, branch, or tag (backs up current .blend first)"

    ref: bpy.props.StringProperty(name="Ref", default="")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            reports.report_error(self, NotBlenderProjectError())
            return {"CANCELLED"}

        if not self.ref:
            self.report({"WARNING"}, "No ref specified.")
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        snapshot = get_snapshot()
        repo = project.detect_project_root(blend_path)

        # Back up .blend before checkout
        prefs = context.preferences.addons.get("gitblend")
        should_backup = prefs is None or getattr(prefs.preferences, "backup_before_restore", True)
        if should_backup and blend_path and blend_path.exists():
            backup_result = snapshot.backup_blend(blend_path)
            if is_ok(backup_result):
                self.report({"INFO"}, f"Backup created: {backup_result.value.name}")  # type: ignore[union-attr]

        result = git.checkout_ref(repo, self.ref)
        if is_ok(result):
            self.report({"INFO"}, f"Checked out {self.ref}.")
            bpy.ops.gitblend.refresh_status()
            bpy.ops.gitblend.refresh_history()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_confirm(
            self,
            event,
            message=f"Checkout '{self.ref}'? A backup of your .blend will be created.",
        )


class GITBLEND_OT_checkout_file(bpy.types.Operator):
    bl_idname = "gitblend.checkout_file"
    bl_label = "Revert File"
    bl_description = "Restore a single file to its last committed state"

    file_path: bpy.props.StringProperty(name="File", default="")  # type: ignore[valid-type]
    ref: bpy.props.StringProperty(name="Ref", default="HEAD")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        from pathlib import Path
        result = git.checkout_file(repo, Path(self.file_path), self.ref)
        if is_ok(result):
            self.report({"INFO"}, f"File '{self.file_path}' reverted to {self.ref}.")
            bpy.ops.gitblend.refresh_status()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_confirm(
            self,
            event,
            message=f"Revert '{self.file_path}' to {self.ref}? Unsaved changes will be lost.",
        )


class GITBLEND_OT_revert_commit(bpy.types.Operator):
    bl_idname = "gitblend.revert_commit"
    bl_label = "Revert Commit"
    bl_description = "Create a new commit that undoes the selected commit"

    commit_hash: bpy.props.StringProperty(name="Commit Hash", default="")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.revert_commit(repo, self.commit_hash)
        if is_ok(result):
            self.report({"INFO"}, f"Commit {self.commit_hash[:7]} reverted.")
            bpy.ops.gitblend.refresh_status()
            bpy.ops.gitblend.refresh_history()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_confirm(
            self,
            event,
            message=f"Revert commit {self.commit_hash[:7]}? This creates a new 'undo' commit.",
        )


classes = [
    GITBLEND_OT_checkout_ref,
    GITBLEND_OT_checkout_file,
    GITBLEND_OT_revert_commit,
]
