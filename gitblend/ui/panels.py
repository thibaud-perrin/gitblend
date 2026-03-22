"""N-panel and sub-panels for gitblend in the 3D View sidebar."""

from __future__ import annotations

import bpy

_CATEGORY = "Git"
_SPACE = "VIEW_3D"
_REGION = "UI"


class GITBLEND_PT_main(bpy.types.Panel):
    """Main gitblend panel."""

    bl_label = "gitblend"
    bl_idname = "GITBLEND_PT_main"
    bl_space_type = _SPACE
    bl_region_type = _REGION
    bl_category = _CATEGORY

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        if not getattr(bpy.data, "filepath", None):
            layout.label(text="Open and save a .blend file", icon="ERROR")
            return

        # Repo state header
        row = layout.row()
        if props.branch:
            icon = "ERROR" if props.is_detached else "BOOKMARKS"
            row.label(text=props.branch, icon=icon)
        else:
            row.label(text="Not a git repo", icon="ERROR")
            row.operator("gitblend.refresh_status", text="", icon="FILE_REFRESH")
            row.operator("gitblend.init_repo", text="Init", icon="ADD")
            return

        # Sync state
        if props.ahead or props.behind:
            sub = layout.row()
            if props.ahead:
                sub.label(text=f"↑ {props.ahead} ahead")
            if props.behind:
                sub.label(text=f"↓ {props.behind} behind")

        # Quick actions
        row = layout.row(align=True)
        row.operator("gitblend.refresh_status", text="", icon="FILE_REFRESH")
        row.operator("gitblend.fetch", text="Fetch", icon="IMPORT")
        row.operator("gitblend.pull", text="Pull", icon="TRIA_DOWN")
        row.operator("gitblend.push", text="Push", icon="TRIA_UP")


class GITBLEND_PT_status(bpy.types.Panel):
    """Status and commit sub-panel."""

    bl_label = "Stage & Commit"
    bl_idname = "GITBLEND_PT_status"
    bl_space_type = _SPACE
    bl_region_type = _REGION
    bl_category = _CATEGORY
    bl_parent_id = "GITBLEND_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        if not props.branch:
            return

        # Counts
        col = layout.column(align=True)
        col.label(text=f"Staged: {props.staged_count}", icon="CHECKMARK")
        col.label(text=f"Modified: {props.unstaged_count}", icon="GREASEPENCIL")
        col.label(text=f"Untracked: {props.untracked_count}", icon="QUESTION")

        if props.has_conflicts:
            col.label(text="Conflicts detected!", icon="ERROR")

        layout.separator()

        # Stage actions
        row = layout.row(align=True)
        row.operator("gitblend.stage_all", text="Stage All", icon="ADD")
        row.operator("gitblend.unstage_all", text="Unstage All", icon="REMOVE")

        layout.separator()

        # Commit message
        layout.prop(props, "commit_message", text="")
        layout.operator("gitblend.commit", text="Commit", icon="FILE_TICK")


class GITBLEND_PT_stash(bpy.types.Panel):
    """Stash sub-panel — save and restore work in progress."""

    bl_label = "Stash"
    bl_idname = "GITBLEND_PT_stash"
    bl_space_type = _SPACE
    bl_region_type = _REGION
    bl_category = _CATEGORY
    bl_parent_id = "GITBLEND_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        # Save row
        row = layout.row(align=True)
        row.prop(props, "stash_message", text="", placeholder="Description (optional)")
        row.operator("gitblend.stash_save", text="Save Changes", icon="RECOVER_LAST")
        layout.operator("gitblend.stash_pull", text="Save & Pull", icon="TRIA_DOWN")

        # Stash list
        if props.stashes:
            layout.template_list(
                "GITBLEND_UL_stashes",
                "",
                props,
                "stashes",
                props,
                "stashes_index",
                rows=3,
            )
            if 0 <= props.stashes_index < len(props.stashes):
                selected = props.stashes[props.stashes_index]
                row = layout.row(align=True)
                pop_op = row.operator("gitblend.stash_pop", text="Restore", icon="LOOP_BACK")
                pop_op.stash_ref = selected.ref
                drop_op = row.operator("gitblend.stash_drop", text="Discard", icon="TRASH")
                drop_op.stash_ref = selected.ref
        else:
            layout.label(text="No saved changes.", icon="INFO")

        layout.operator("gitblend.refresh_stash", text="Refresh", icon="FILE_REFRESH")


class GITBLEND_PT_history(bpy.types.Panel):
    """Commit history sub-panel."""

    bl_label = "History"
    bl_idname = "GITBLEND_PT_history"
    bl_space_type = _SPACE
    bl_region_type = _REGION
    bl_category = _CATEGORY
    bl_parent_id = "GITBLEND_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        row = layout.row()
        row.operator("gitblend.refresh_history", text="Refresh", icon="FILE_REFRESH")

        if props.history:
            layout.template_list(
                "GITBLEND_UL_commits",
                "",
                props,
                "history",
                props,
                "history_index",
                rows=5,
            )
            if 0 <= props.history_index < len(props.history):
                commit = props.history[props.history_index]
                col = layout.column(align=True)
                col.label(text=f"Hash: {commit.short_hash}")
                col.label(text=f"Author: {commit.author}")
                col.label(text=f"Date: {commit.date}")
                col.label(text=commit.message)
                row = layout.row(align=True)
                op = row.operator("gitblend.checkout_ref", text="Checkout", icon="RECOVER_LAST")
                op.ref = commit.hash
                op2 = row.operator("gitblend.open_commit_github", text="", icon="URL")
                op2.commit_hash = commit.hash
                op3 = row.operator("gitblend.revert_commit", text="Revert", icon="LOOP_BACK")
                op3.commit_hash = commit.hash
        else:
            layout.label(text="No commits yet.", icon="INFO")


class GITBLEND_PT_branches(bpy.types.Panel):
    """Branches sub-panel."""

    bl_label = "Branches"
    bl_idname = "GITBLEND_PT_branches"
    bl_space_type = _SPACE
    bl_region_type = _REGION
    bl_category = _CATEGORY
    bl_parent_id = "GITBLEND_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        row = layout.row()
        row.operator("gitblend.refresh_branches", text="Refresh", icon="FILE_REFRESH")

        if props.branches:
            layout.template_list(
                "GITBLEND_UL_branches",
                "",
                props,
                "branches",
                props,
                "branches_index",
                rows=4,
            )
            if 0 <= props.branches_index < len(props.branches):
                selected = props.branches[props.branches_index]
                is_detached = selected.name == "HEAD (detached)"
                row = layout.row()
                row.enabled = not selected.is_current and not is_detached
                if not is_detached:
                    if selected.is_remote:
                        local_name = selected.name.split("/", 1)[1]
                        label = f"Checkout '{local_name}' (from {selected.name})"
                    else:
                        local_name = selected.name
                        label = f"Switch to '{selected.name}'"
                    op = row.operator("gitblend.switch_branch", text=label, icon="BOOKMARKS")
                    op.branch_name = local_name
                else:
                    row.label(text="HEAD (detached) — cannot switch")
        else:
            layout.label(text="Click Refresh to load branches.", icon="INFO")

        layout.separator()
        row = layout.row(align=True)
        row.operator("gitblend.create_branch", text="New Branch", icon="ADD")
        row.operator("gitblend.merge_branch", text="Merge", icon="AUTOMERGE_ON")


class GITBLEND_PT_github(bpy.types.Panel):
    """GitHub integration sub-panel."""

    bl_label = "GitHub"
    bl_idname = "GITBLEND_PT_github"
    bl_space_type = _SPACE
    bl_region_type = _REGION
    bl_category = _CATEGORY
    bl_parent_id = "GITBLEND_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        if props.github_authenticated:
            row = layout.row()
            row.label(text=f"Connected as {props.github_username}", icon="CHECKMARK")
            row.operator("gitblend.github_logout", text="", icon="X")

            layout.separator()
            layout.operator("gitblend.create_remote_repo", text="Create Remote Repo", icon="ADD")
            layout.operator("gitblend.create_pr", text="Create Pull Request", icon="NLA_PUSHDOWN")
            layout.operator("gitblend.create_release", text="Create Release", icon="PACKAGE")

            layout.separator()
            layout.operator("gitblend.open_github", text="Open on GitHub", icon="URL")
        else:
            layout.label(text="Not connected to GitHub", icon="ERROR")
            layout.separator()
            layout.operator("gitblend.auth_pat", text="Connect with Token", icon="KEY_HLT")
            layout.operator("gitblend.start_device_flow", text="Connect via Browser", icon="URL")


class GITBLEND_PT_diagnostics(bpy.types.Panel):
    """Project diagnostics sub-panel."""

    bl_label = "Project Health"
    bl_idname = "GITBLEND_PT_diagnostics"
    bl_space_type = _SPACE
    bl_region_type = _REGION
    bl_category = _CATEGORY
    bl_parent_id = "GITBLEND_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        layout.operator("gitblend.audit_project", text="Run Audit", icon="VIEWZOOM")
        layout.separator()

        col = layout.column(align=True)
        icon_ok = "CHECKMARK"
        icon_warn = "ERROR"
        col.label(
            text=".gitignore: " + ("OK" if props.diag_has_gitignore else "Missing"),
            icon=icon_ok if props.diag_has_gitignore else icon_warn,
        )
        col.label(
            text=".gitattributes: " + ("OK" if props.diag_has_gitattributes else "Missing"),
            icon=icon_ok if props.diag_has_gitattributes else icon_warn,
        )
        if props.diag_large_file_count:
            col.label(
                text=f"{props.diag_large_file_count} files exceed 100 MB!",
                icon=icon_warn,
            )

        layout.separator()
        row = layout.row(align=True)
        row.operator("gitblend.write_gitignore", text=".gitignore", icon="FILE_TEXT")
        row.operator("gitblend.write_gitattributes", text=".gitattributes", icon="FILE_TEXT")
        layout.operator("gitblend.setup_lfs_blender", text="Setup LFS", icon="MOD_PARTICLE_INSTANCE")


class GITBLEND_PT_blender_repos(bpy.types.Panel):
    """My Blender Projects — browse and clone GitHub repos tagged 'blender'."""

    bl_label = "My Blender Projects"
    bl_idname = "GITBLEND_PT_blender_repos"
    bl_space_type = _SPACE
    bl_region_type = _REGION
    bl_category = _CATEGORY
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        if not props.github_authenticated:
            layout.label(text="Connect to GitHub to see your Blender repos", icon="ERROR")
            layout.operator("gitblend.auth_pat", text="Connect with Token", icon="KEY_HLT")
            layout.operator("gitblend.start_device_flow", text="Connect via Browser", icon="URL")
            return

        row = layout.row(align=True)
        if props.blender_repos_loading:
            row.label(text="Loading...", icon="TIME")
        else:
            row.operator("gitblend.refresh_blender_repos", text="Refresh", icon="FILE_REFRESH")

        if props.blender_repos:
            layout.template_list(
                "GITBLEND_UL_repos",
                "",
                props,
                "blender_repos",
                props,
                "blender_repos_index",
                rows=6,
            )
        else:
            layout.label(text="No repos found. Click Refresh.", icon="INFO")

        layout.separator()
        layout.prop(props, "clone_target_dir")

        has_selection = bool(props.blender_repos) and 0 <= props.blender_repos_index < len(props.blender_repos)
        has_dir = bool(props.clone_target_dir.strip())
        row = layout.row()
        row.enabled = has_selection and has_dir
        row.operator("gitblend.clone_repo", text="Clone Selected Repo", icon="IMPORT")


classes = [
    GITBLEND_PT_main,
    GITBLEND_PT_status,
    GITBLEND_PT_stash,
    GITBLEND_PT_history,
    GITBLEND_PT_branches,
    GITBLEND_PT_github,
    GITBLEND_PT_diagnostics,
    GITBLEND_PT_blender_repos,
]
