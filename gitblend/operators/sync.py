"""Operators: fetch, pull, push."""

from __future__ import annotations

import bpy

from ..bpy_adapters import context as ctx_adapter
from ..bpy_adapters import jobs, reports
from ..domain.errors import NotBlenderProjectError
from ..domain.result import is_ok

from ._services import get_blender_project, get_git


class GITBLEND_OT_fetch(bpy.types.Operator):
    bl_idname = "gitblend.fetch"
    bl_label = "Fetch"
    bl_description = "Fetch from remote (non-blocking)"

    remote: bpy.props.StringProperty(name="Remote", default="origin")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            reports.report_error(self, NotBlenderProjectError())
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)
        remote = self.remote

        def do_fetch() -> bool:
            result = git.fetch(repo, remote)
            return is_ok(result)

        def on_done(success: bool) -> None:
            if success:
                bpy.ops.gitblend.refresh_status()

        def on_err(exc: Exception) -> None:
            pass

        jobs.run_in_background(do_fetch, on_done, on_err)
        self.report({"INFO"}, f"Fetching from {remote}…")
        return {"FINISHED"}


class GITBLEND_OT_pull(bpy.types.Operator):
    bl_idname = "gitblend.pull"
    bl_label = "Pull"
    bl_description = "Pull from remote"

    remote: bpy.props.StringProperty(name="Remote", default="origin")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.pull(repo, self.remote)
        if is_ok(result):
            self.report({"INFO"}, "Pull complete.")
            bpy.ops.gitblend.refresh_status()
            bpy.ops.gitblend.refresh_history()
            # Sync the pulled sidecar to the working .blend then reload.
            project.sync_sidecar_to_blend(blend_path)
            bpy.ops.wm.revert_mainfile()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_confirm(
            self, event, message="Pull from remote? Unsaved changes may be affected."
        )


class GITBLEND_OT_push(bpy.types.Operator):
    bl_idname = "gitblend.push"
    bl_label = "Push"
    bl_description = "Push to remote"

    remote: bpy.props.StringProperty(name="Remote", default="origin")  # type: ignore[valid-type]
    set_upstream: bpy.props.BoolProperty(name="Set upstream", default=False)  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        def do_push() -> bool:
            result = git.push(repo, self.remote, set_upstream=self.set_upstream)
            return is_ok(result)

        def on_done(success: bool) -> None:
            if success:
                bpy.ops.gitblend.refresh_status()

        def on_err(exc: Exception) -> None:
            pass

        jobs.run_in_background(do_push, on_done, on_err)
        self.report({"INFO"}, "Pushing…")
        return {"FINISHED"}


classes = [
    GITBLEND_OT_fetch,
    GITBLEND_OT_pull,
    GITBLEND_OT_push,
]
