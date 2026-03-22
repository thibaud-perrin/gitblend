"""Operators: stash management."""

from __future__ import annotations

import bpy

from ..bpy_adapters import context as ctx_adapter
from ..bpy_adapters import reports
from ..domain.result import is_ok

from ._services import get_blender_project, get_git


class GITBLEND_OT_refresh_stash(bpy.types.Operator):
    bl_idname = "gitblend.refresh_stash"
    bl_label = "Refresh Stash"
    bl_description = "Reload the stash list"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"FINISHED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.stash_list(repo)
        if not is_ok(result):
            return {"FINISHED"}

        stashes = result.value  # type: ignore[union-attr]
        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        props.stashes.clear()
        for entry in stashes:
            item = props.stashes.add()
            item.ref = entry.ref
            item.branch = entry.branch
            item.message = entry.message
            item.date = entry.date

        return {"FINISHED"}


class GITBLEND_OT_stash_save(bpy.types.Operator):
    bl_idname = "gitblend.stash_save"
    bl_label = "Save Changes"
    bl_description = "Save current changes so you can pull or switch branches safely"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        # Flush Blender's in-memory state to disk then sync the sidecar so the
        # stash captures the current scene content.
        ctx_adapter.save_blend()

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        if blend_path.exists():
            project.sync_blend_to_sidecar(blend_path)

        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        message = props.stash_message.strip()

        result = git.stash_save(repo, message)
        if is_ok(result):
            props.stash_message = ""
            self.report({"INFO"}, "Changes saved to stash.")
            bpy.ops.gitblend.refresh_stash()
            bpy.ops.gitblend.refresh_status()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}

        return {"FINISHED"}


class GITBLEND_OT_stash_pop(bpy.types.Operator):
    bl_idname = "gitblend.stash_pop"
    bl_label = "Restore"
    bl_description = "Apply this saved state and remove it from the stash list"

    stash_ref: bpy.props.StringProperty(default="stash@{0}")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.stash_pop(repo, self.stash_ref)
        if is_ok(result):
            self.report({"INFO"}, f"Restored {self.stash_ref}.")
            bpy.ops.gitblend.refresh_stash()
            bpy.ops.gitblend.refresh_status()
            # Sync the restored sidecar back to the working .blend then reload.
            project.sync_sidecar_to_blend(blend_path)
            bpy.ops.wm.revert_mainfile()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}

        return {"FINISHED"}


class GITBLEND_OT_stash_drop(bpy.types.Operator):
    bl_idname = "gitblend.stash_drop"
    bl_label = "Discard"
    bl_description = "Permanently delete this saved state (cannot be undone)"

    stash_ref: bpy.props.StringProperty(default="stash@{0}")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.stash_drop(repo, self.stash_ref)
        if is_ok(result):
            self.report({"INFO"}, f"Discarded {self.stash_ref}.")
            bpy.ops.gitblend.refresh_stash()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}

        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_confirm(
            self, event, message=f"Permanently discard {self.stash_ref}? This cannot be undone."
        )


class GITBLEND_OT_stash_pull(bpy.types.Operator):
    bl_idname = "gitblend.stash_pull"
    bl_label = "Save & Pull"
    bl_description = "Save your changes to stash, pull from remote, then reload the file"

    remote: bpy.props.StringProperty(name="Remote", default="origin")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        # Flush Blender's state then sync the sidecar before stashing.
        ctx_adapter.save_blend()

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        if blend_path.exists():
            project.sync_blend_to_sidecar(blend_path)

        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        message = props.stash_message.strip()

        # Stash — runs synchronously, so Blender's event loop cannot write back
        # the in-memory version between stash and pull.
        stash_result = git.stash_save(repo, message)
        if not is_ok(stash_result):
            reports.report_error(self, stash_result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}

        # Pull immediately while working tree is HEAD.
        pull_result = git.pull(repo, self.remote)
        if not is_ok(pull_result):
            reports.report_error(self, pull_result.error)  # type: ignore[union-attr]
            bpy.ops.gitblend.refresh_stash()
            return {"CANCELLED"}

        props.stash_message = ""
        self.report({"INFO"}, "Changes saved, pull complete. Restore from stash when ready.")
        bpy.ops.gitblend.refresh_stash()
        bpy.ops.gitblend.refresh_history()
        # Sync the pulled sidecar to the working .blend then reload.
        project.sync_sidecar_to_blend(blend_path)
        bpy.ops.wm.revert_mainfile()
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_confirm(
            self, event, message="Save changes to stash, pull from remote, then reload?"
        )


classes = [
    GITBLEND_OT_refresh_stash,
    GITBLEND_OT_stash_save,
    GITBLEND_OT_stash_pull,
    GITBLEND_OT_stash_pop,
    GITBLEND_OT_stash_drop,
]
