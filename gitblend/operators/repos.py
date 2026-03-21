"""Operators: browse and clone GitHub repos tagged with the 'blender' topic."""

from __future__ import annotations

from pathlib import Path

import bpy

from ..bpy_adapters import jobs, reports

from ._services import get_git, get_github


class GITBLEND_OT_refresh_blender_repos(bpy.types.Operator):
    bl_idname = "gitblend.refresh_blender_repos"
    bl_label = "Refresh"
    bl_description = "Fetch GitHub repositories tagged with the 'blender' topic"

    def execute(self, context: bpy.types.Context) -> set[str]:
        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        username = props.github_username
        if not username:
            self.report({"WARNING"}, "Not connected to GitHub.")
            return {"CANCELLED"}

        props.blender_repos_loading = True
        github = get_github()

        def do_fetch():
            return github.list_blender_repos(username)

        def on_complete(result) -> None:
            try:
                wm_props = bpy.context.window_manager.gitblend  # type: ignore[attr-defined]
                wm_props.blender_repos_loading = False
                from ..domain.result import is_ok
                if not is_ok(result):
                    error = result.error  # type: ignore[union-attr]
                    reports.popup_message(error.message, title="Refresh Failed", icon="ERROR")
                    return
                repos = result.value  # type: ignore[union-attr]
                wm_props.blender_repos.clear()
                for repo in repos:
                    item = wm_props.blender_repos.add()
                    item.name = repo.name
                    item.full_name = repo.full_name
                    item.description = repo.description
                    item.clone_url = repo.clone_url
                    item.private = repo.private
                wm_props.blender_repos_index = 0
            except Exception:
                pass

        def on_error(exc: Exception) -> None:
            try:
                bpy.context.window_manager.gitblend.blender_repos_loading = False  # type: ignore[attr-defined]
            except Exception:
                pass
            reports.popup_message(str(exc), title="Refresh Failed", icon="ERROR")

        jobs.run_in_background(do_fetch, on_complete, on_error)
        return {"FINISHED"}


class GITBLEND_OT_clone_repo(bpy.types.Operator):
    bl_idname = "gitblend.clone_repo"
    bl_label = "Clone Selected Repo"
    bl_description = "Clone the selected repository to the chosen directory"

    _target_path: Path | None = None

    def execute(self, context: bpy.types.Context) -> set[str]:
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        if not props.blender_repos:
            self.report({"WARNING"}, "No repos loaded. Click Refresh first.")
            return {"CANCELLED"}

        idx = props.blender_repos_index
        if idx < 0 or idx >= len(props.blender_repos):
            self.report({"WARNING"}, "No repo selected.")
            return {"CANCELLED"}

        repo_item = props.blender_repos[idx]
        clone_url = repo_item.clone_url
        repo_name = repo_item.name

        target_dir = props.clone_target_dir.strip()
        if not target_dir:
            self.report({"WARNING"}, "Set a destination directory first.")
            return {"CANCELLED"}

        target_path = Path(target_dir) / repo_name
        self._target_path = target_path

        if target_path.exists():
            return context.window_manager.invoke_confirm(  # type: ignore[return-value]
                self,
                event=None,  # type: ignore[arg-type]
            )

        return self._do_clone(clone_url, target_path)

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        if not props.blender_repos:
            self.report({"WARNING"}, "No repos loaded. Click Refresh first.")
            return {"CANCELLED"}

        idx = props.blender_repos_index
        if idx < 0 or idx >= len(props.blender_repos):
            self.report({"WARNING"}, "No repo selected.")
            return {"CANCELLED"}

        repo_item = props.blender_repos[idx]
        clone_url = repo_item.clone_url
        repo_name = repo_item.name

        target_dir = props.clone_target_dir.strip()
        if not target_dir:
            self.report({"WARNING"}, "Set a destination directory first.")
            return {"CANCELLED"}

        target_path = Path(target_dir) / repo_name
        self._target_path = target_path

        if target_path.exists():
            return context.window_manager.invoke_confirm(self, event)  # type: ignore[return-value]

        return self._do_clone(clone_url, target_path)

    def _do_clone(self, clone_url: str, target_path: Path) -> set[str]:
        git = get_git()

        def do_clone():
            return git.clone(clone_url, target_path)

        def on_complete(result) -> None:
            from ..domain.result import is_ok
            if is_ok(result):
                path = result.value  # type: ignore[union-attr]
                reports.popup_message(
                    f"Cloned to {path}",
                    title="Clone Complete",
                    icon="CHECKMARK",
                )
            else:
                error = result.error  # type: ignore[union-attr]
                msg = error.message
                if error.detail:
                    msg = f"{msg}\n{error.detail}"
                reports.popup_message(msg, title="Clone Failed", icon="ERROR")

        def on_error(exc: Exception) -> None:
            reports.popup_message(str(exc), title="Clone Failed", icon="ERROR")

        jobs.run_in_background(do_clone, on_complete, on_error)
        return {"FINISHED"}


classes = [
    GITBLEND_OT_refresh_blender_repos,
    GITBLEND_OT_clone_repo,
]
