"""Operators: init repo, refresh status."""

from __future__ import annotations

import bpy

from gitblend.bpy_adapters import context as ctx_adapter
from gitblend.bpy_adapters import reports
from gitblend.domain.errors import NotBlenderProjectError
from gitblend.domain.result import is_ok

from ._services import get_blender_project, get_git


class GITBLEND_OT_init_repo(bpy.types.Operator):
    bl_idname = "gitblend.init_repo"
    bl_label = "Init Repository"
    bl_description = "Initialise a git repository in the current Blender project directory"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            reports.report_error(self, NotBlenderProjectError())
            return {"CANCELLED"}

        project = get_blender_project()
        repo_path = project.detect_project_root(blend_path)

        git = get_git()
        if git.is_repo(repo_path):
            self.report({"INFO"}, f"Already a git repository: {repo_path}")
            return {"FINISHED"}

        result = git.init(repo_path)
        if is_ok(result):
            self.report({"INFO"}, f"Repository initialised: {repo_path}")
            # Refresh cached status
            bpy.ops.gitblend.refresh_status()
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}

        return {"FINISHED"}


class GITBLEND_OT_refresh_status(bpy.types.Operator):
    bl_idname = "gitblend.refresh_status"
    bl_label = "Refresh Status"
    bl_description = "Refresh the git status display"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"FINISHED"}

        git = get_git()
        project = get_blender_project()
        repo_path = project.detect_project_root(blend_path)

        if not git.is_repo(repo_path):
            return {"FINISHED"}

        result = git.status(repo_path)
        if not is_ok(result):
            return {"FINISHED"}

        status = result.value  # type: ignore[union-attr]
        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        props.branch = status.branch
        props.is_dirty = not status.is_clean
        props.has_conflicts = status.has_conflicts
        props.is_detached = status.is_detached
        props.staged_count = len(status.staged)
        props.unstaged_count = len(status.unstaged)
        props.untracked_count = len(status.untracked)
        props.ahead = status.ahead
        props.behind = status.behind
        props.sync_state = status.sync_state.name

        return {"FINISHED"}


classes = [
    GITBLEND_OT_init_repo,
    GITBLEND_OT_refresh_status,
]
