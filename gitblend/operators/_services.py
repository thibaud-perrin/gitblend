"""Shared service singletons for all operators.

Initialised once and reused across operators to avoid creating new
SubprocessRunner / FileSystem instances per-call.
"""

from __future__ import annotations

from gitblend.infrastructure.auth_store import AuthStore
from gitblend.infrastructure.file_system import FileSystem
from gitblend.infrastructure.subprocess_runner import SubprocessRunner
from gitblend.services.blender_project_service import BlenderProjectService
from gitblend.services.diagnostics_service import DiagnosticsService
from gitblend.services.git_service import GitService
from gitblend.services.github_service import GitHubService
from gitblend.services.lfs_service import LFSService
from gitblend.services.snapshot_service import SnapshotService


def _git_bin() -> str:
    """Get the configured git binary path from addon preferences."""
    try:
        import bpy
        prefs = bpy.context.preferences.addons.get("gitblend")
        if prefs and hasattr(prefs.preferences, "git_binary"):
            return prefs.preferences.git_binary or "git"
    except Exception:
        pass
    return "git"


# These are module-level singletons — re-created if preferences change.
_runner: SubprocessRunner | None = None
_fs: FileSystem | None = None
_auth: AuthStore | None = None
_git: GitService | None = None
_github: GitHubService | None = None
_lfs: LFSService | None = None
_diagnostics: DiagnosticsService | None = None
_snapshot: SnapshotService | None = None
_blender_project: BlenderProjectService | None = None


def get_runner() -> SubprocessRunner:
    global _runner
    if _runner is None:
        _runner = SubprocessRunner(git_bin=_git_bin())
    return _runner


def get_fs() -> FileSystem:
    global _fs
    if _fs is None:
        _fs = FileSystem()
    return _fs


def get_auth() -> AuthStore:
    global _auth
    if _auth is None:
        _auth = AuthStore()
    return _auth


def get_git() -> GitService:
    global _git
    if _git is None:
        _git = GitService(get_runner(), get_fs())
    return _git


def get_github() -> GitHubService:
    global _github
    if _github is None:
        _github = GitHubService(get_auth())
    return _github


def get_lfs() -> LFSService:
    global _lfs
    if _lfs is None:
        _lfs = LFSService(get_runner(), get_fs())
    return _lfs


def get_diagnostics() -> DiagnosticsService:
    global _diagnostics
    if _diagnostics is None:
        _diagnostics = DiagnosticsService(get_fs(), get_lfs())
    return _diagnostics


def get_snapshot() -> SnapshotService:
    global _snapshot
    if _snapshot is None:
        _snapshot = SnapshotService(get_fs())
    return _snapshot


def get_blender_project() -> BlenderProjectService:
    global _blender_project
    if _blender_project is None:
        _blender_project = BlenderProjectService(get_fs())
    return _blender_project


def invalidate() -> None:
    """Force re-creation of all singletons (call after prefs change)."""
    global _runner, _fs, _auth, _git, _github, _lfs, _diagnostics, _snapshot, _blender_project
    _runner = _fs = _auth = _git = _github = _lfs = _diagnostics = _snapshot = _blender_project = None
