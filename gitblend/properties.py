"""Blender PropertyGroup definitions for gitblend.

These are registered on bpy.types.WindowManager so they persist
for the lifetime of a Blender session without touching scene data.
"""

from __future__ import annotations

import bpy


class GitBlendCommitItem(bpy.types.PropertyGroup):
    """Represents one commit in the history CollectionProperty."""

    hash: bpy.props.StringProperty()  # type: ignore[valid-type]
    short_hash: bpy.props.StringProperty()  # type: ignore[valid-type]
    author: bpy.props.StringProperty()  # type: ignore[valid-type]
    message: bpy.props.StringProperty()  # type: ignore[valid-type]
    date: bpy.props.StringProperty()  # type: ignore[valid-type]


class GitBlendBranchItem(bpy.types.PropertyGroup):
    """Represents one branch in the branches CollectionProperty."""

    name: bpy.props.StringProperty()  # type: ignore[valid-type]
    is_current: bpy.props.BoolProperty()  # type: ignore[valid-type]
    upstream: bpy.props.StringProperty()  # type: ignore[valid-type]


class GitBlendRepoItem(bpy.types.PropertyGroup):
    """Represents one GitHub repo in the blender_repos CollectionProperty."""

    name: bpy.props.StringProperty()  # type: ignore[valid-type]
    full_name: bpy.props.StringProperty()  # type: ignore[valid-type]
    description: bpy.props.StringProperty()  # type: ignore[valid-type]
    clone_url: bpy.props.StringProperty()  # type: ignore[valid-type]
    private: bpy.props.BoolProperty()  # type: ignore[valid-type]


class GitBlendWindowProps(bpy.types.PropertyGroup):
    """Main gitblend state — registered on WindowManager."""

    # Repo state
    branch: bpy.props.StringProperty(name="Current Branch", default="")  # type: ignore[valid-type]
    sync_state: bpy.props.StringProperty(name="Sync State", default="NO_REMOTE")  # type: ignore[valid-type]
    is_dirty: bpy.props.BoolProperty(name="Has Changes", default=False)  # type: ignore[valid-type]
    has_conflicts: bpy.props.BoolProperty(name="Has Conflicts", default=False)  # type: ignore[valid-type]
    is_detached: bpy.props.BoolProperty(name="Detached HEAD", default=False)  # type: ignore[valid-type]
    staged_count: bpy.props.IntProperty(name="Staged", default=0)  # type: ignore[valid-type]
    unstaged_count: bpy.props.IntProperty(name="Modified", default=0)  # type: ignore[valid-type]
    untracked_count: bpy.props.IntProperty(name="Untracked", default=0)  # type: ignore[valid-type]
    ahead: bpy.props.IntProperty(name="Ahead", default=0)  # type: ignore[valid-type]
    behind: bpy.props.IntProperty(name="Behind", default=0)  # type: ignore[valid-type]

    # Commit
    commit_message: bpy.props.StringProperty(name="Commit Message", default="")  # type: ignore[valid-type]
    new_branch_name: bpy.props.StringProperty(name="New Branch Name", default="")  # type: ignore[valid-type]

    # History
    history: bpy.props.CollectionProperty(type=GitBlendCommitItem)  # type: ignore[valid-type]
    history_index: bpy.props.IntProperty(name="History Index", default=0)  # type: ignore[valid-type]

    # Branches
    branches: bpy.props.CollectionProperty(type=GitBlendBranchItem)  # type: ignore[valid-type]
    branches_index: bpy.props.IntProperty(name="Branches Index", default=0)  # type: ignore[valid-type]

    # GitHub
    github_authenticated: bpy.props.BoolProperty(name="GitHub Authenticated", default=False)  # type: ignore[valid-type]
    github_username: bpy.props.StringProperty(name="GitHub Username", default="")  # type: ignore[valid-type]
    remote_repo_url: bpy.props.StringProperty(name="Remote Repo URL", default="")  # type: ignore[valid-type]

    # Device flow temporary state
    device_flow_code: bpy.props.StringProperty(name="Device Code", default="")  # type: ignore[valid-type]
    device_flow_uri: bpy.props.StringProperty(name="Verification URI", default="")  # type: ignore[valid-type]
    device_flow_device_code: bpy.props.StringProperty(name="Device Code (internal)", default="")  # type: ignore[valid-type]

    # My Blender Projects
    blender_repos: bpy.props.CollectionProperty(type=GitBlendRepoItem)  # type: ignore[valid-type]
    blender_repos_index: bpy.props.IntProperty(default=0)  # type: ignore[valid-type]
    blender_repos_loading: bpy.props.BoolProperty(default=False)  # type: ignore[valid-type]
    clone_target_dir: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Clone into",
        description="Parent directory — repo will be cloned into a subfolder here",
        subtype="DIR_PATH",
        default="",
    )

    # Diagnostics
    diag_has_gitignore: bpy.props.BoolProperty(default=False)  # type: ignore[valid-type]
    diag_has_gitattributes: bpy.props.BoolProperty(default=False)  # type: ignore[valid-type]
    diag_large_file_count: bpy.props.IntProperty(default=0)  # type: ignore[valid-type]
    diag_warning_count: bpy.props.IntProperty(default=0)  # type: ignore[valid-type]


class GitBlendPreferences(bpy.types.AddonPreferences):
    """Addon-level preferences accessible via Edit > Preferences > Add-ons."""

    bl_idname = "gitblend"

    git_binary: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Git Binary",
        description="Path to the git executable (leave blank to use system git)",
        default="",
        subtype="FILE_PATH",
    )
    lfs_enabled: bpy.props.BoolProperty(  # type: ignore[valid-type]
        name="Enable LFS support",
        description="Show LFS-related UI and check for git-lfs on startup",
        default=True,
    )
    auto_save_before_commit: bpy.props.BoolProperty(  # type: ignore[valid-type]
        name="Auto-save before commit",
        description="Automatically save the .blend file before committing",
        default=True,
    )
    backup_before_restore: bpy.props.BoolProperty(  # type: ignore[valid-type]
        name="Backup before restore",
        description="Create a .blend backup before any checkout or revert operation",
        default=True,
    )

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.prop(self, "git_binary")
        layout.prop(self, "lfs_enabled")
        layout.separator()
        layout.prop(self, "auto_save_before_commit")
        layout.prop(self, "backup_before_restore")


classes = [
    GitBlendCommitItem,
    GitBlendBranchItem,
    GitBlendRepoItem,
    GitBlendWindowProps,
    GitBlendPreferences,
]
