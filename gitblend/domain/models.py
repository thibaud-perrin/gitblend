"""Domain data models for gitblend."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .enums import BranchType, FileStatus, SyncState


@dataclass
class GitFile:
    """A file tracked by git with its current status."""

    path: Path
    status: FileStatus
    old_path: Path | None = None  # set for renamed/copied files


@dataclass
class CommitInfo:
    """Information about a single git commit."""

    hash: str
    short_hash: str
    author: str
    email: str
    date: datetime
    message: str
    branches: list[str] = field(default_factory=list)


@dataclass
class Branch:
    """A git branch (local or remote)."""

    name: str
    type: BranchType
    is_current: bool = False
    upstream: str | None = None
    commit_hash: str | None = None


@dataclass
class RepoStatus:
    """Current status of a git repository."""

    branch: str
    sync_state: SyncState
    staged: list[GitFile] = field(default_factory=list)
    unstaged: list[GitFile] = field(default_factory=list)
    untracked: list[GitFile] = field(default_factory=list)
    conflicts: list[GitFile] = field(default_factory=list)
    is_detached: bool = False
    ahead: int = 0
    behind: int = 0

    @property
    def is_clean(self) -> bool:
        return not self.staged and not self.unstaged and not self.untracked

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)


@dataclass
class GitRemote:
    """A git remote."""

    name: str
    url: str
    fetch_url: str | None = None


@dataclass
class BlenderProjectInfo:
    """Information about a Blender project directory."""

    blend_path: Path
    project_dir: Path
    linked_libs: list[str] = field(default_factory=list)
    missing_textures: list[str] = field(default_factory=list)
    absolute_paths: list[str] = field(default_factory=list)
    large_files: list[tuple[str, float]] = field(default_factory=list)  # (path, size_mb)


@dataclass
class GitHubRepo:
    """A GitHub repository."""

    name: str
    full_name: str
    url: str
    clone_url: str
    ssh_url: str
    default_branch: str
    private: bool
    description: str = ""


@dataclass
class DeviceFlowData:
    """Data returned when starting a GitHub device flow."""

    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


@dataclass
class PullRequest:
    """A GitHub pull request."""

    number: int
    title: str
    url: str
    state: str  # "open" | "closed" | "merged"
    head: str
    base: str
    author: str
    body: str = ""


@dataclass
class Release:
    """A GitHub release."""

    tag: str
    name: str
    url: str
    published_at: str
    body: str = ""
    draft: bool = False
    prerelease: bool = False
