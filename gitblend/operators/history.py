"""Operators: view commit history, open commit on GitHub."""

from __future__ import annotations

import webbrowser

import bpy

from gitblend.bpy_adapters import context as ctx_adapter
from gitblend.domain.result import is_ok

from ._services import get_blender_project, get_git


class GITBLEND_OT_refresh_history(bpy.types.Operator):
    bl_idname = "gitblend.refresh_history"
    bl_label = "Refresh History"
    bl_description = "Reload the commit history list"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"FINISHED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = git.log(repo, limit=100)
        if not is_ok(result):
            return {"FINISHED"}

        commits = result.value  # type: ignore[union-attr]
        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        props.history.clear()
        for commit in commits:
            item = props.history.add()
            item.hash = commit.hash
            item.short_hash = commit.short_hash
            item.author = commit.author
            item.message = commit.message
            item.date = commit.date.strftime("%Y-%m-%d %H:%M")

        return {"FINISHED"}


class GITBLEND_OT_open_commit_github(bpy.types.Operator):
    bl_idname = "gitblend.open_commit_github"
    bl_label = "Open on GitHub"
    bl_description = "Open the selected commit on GitHub in the browser"

    commit_hash: bpy.props.StringProperty(name="Commit Hash", default="")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        # Get remote URL
        remotes_result = git.list_remotes(repo)
        if not is_ok(remotes_result):
            self.report({"WARNING"}, "No remote configured.")
            return {"CANCELLED"}

        remotes = remotes_result.value  # type: ignore[union-attr]
        if not remotes:
            self.report({"WARNING"}, "No remote configured.")
            return {"CANCELLED"}

        remote_url = remotes[0].url
        # Convert SSH to HTTPS if needed
        if remote_url.startswith("git@github.com:"):
            remote_url = remote_url.replace("git@github.com:", "https://github.com/", 1)
        remote_url = remote_url.rstrip(".git")

        hash_ = self.commit_hash or ""
        if hash_:
            url = f"{remote_url}/commit/{hash_}"
        else:
            url = remote_url
        webbrowser.open(url)
        return {"FINISHED"}


classes = [
    GITBLEND_OT_refresh_history,
    GITBLEND_OT_open_commit_github,
]
