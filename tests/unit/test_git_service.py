"""Unit tests for GitService error detection (mocked subprocess runner)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gitblend.domain.errors import DirtyWorkingTreeError, LFSNotAvailableError, StashConflictError
from gitblend.domain.models import StashEntry
from gitblend.domain.result import is_ok
from gitblend.infrastructure.file_system import FileSystem
from gitblend.infrastructure.subprocess_runner import RunResult
from gitblend.services.git_service import GitService

_LFS_STDERR = (
    "git-lfs filter-process: git-lfs: command not found\n"
    "fatal: the remote end hung up unexpectedly"
)


def _make_git(stderr: str, returncode: int = 128) -> GitService:
    runner = MagicMock()
    runner.run_git.return_value = RunResult(
        stdout="", stderr=stderr, returncode=returncode, command=["git"]
    )
    return GitService(runner, FileSystem())


@pytest.mark.unit
def test_fetch_returns_lfs_error_when_lfs_missing() -> None:
    git = _make_git(_LFS_STDERR)
    result = git.fetch(Path("/repo"))
    assert not is_ok(result)
    assert isinstance(result.error, LFSNotAvailableError)  # type: ignore[union-attr]


@pytest.mark.unit
def test_pull_returns_lfs_error_when_lfs_missing() -> None:
    git = _make_git(_LFS_STDERR)
    result = git.pull(Path("/repo"))
    assert not is_ok(result)
    assert isinstance(result.error, LFSNotAvailableError)  # type: ignore[union-attr]


@pytest.mark.unit
def test_push_returns_lfs_error_when_lfs_missing() -> None:
    git = _make_git(_LFS_STDERR)
    result = git.push(Path("/repo"))
    assert not is_ok(result)
    assert isinstance(result.error, LFSNotAvailableError)  # type: ignore[union-attr]


@pytest.mark.unit
def test_stage_all_returns_lfs_error_when_lfs_missing() -> None:
    git = _make_git(_LFS_STDERR)
    result = git.stage_all(Path("/repo"))
    assert not is_ok(result)
    assert isinstance(result.error, LFSNotAvailableError)  # type: ignore[union-attr]


@pytest.mark.unit
def test_status_returns_branch_when_lfs_missing() -> None:
    """git status fails due to missing LFS, but the branch is still returned."""
    from unittest.mock import MagicMock
    runner = MagicMock()
    runner.run_git.side_effect = [
        RunResult(stdout="main", stderr="", returncode=0, command=["git", "symbolic-ref"]),
        RunResult(stdout="", stderr=_LFS_STDERR, returncode=128, command=["git", "status"]),
    ]
    from gitblend.infrastructure.file_system import FileSystem
    git = GitService(runner, FileSystem())
    result = git.status(Path("/repo"))
    assert is_ok(result)
    assert result.value.branch == "main"  # type: ignore[union-attr]
    assert result.value.staged == []  # type: ignore[union-attr]


_STASH_OUTPUT = (
    "stash@{0}\x1fWIP on main: abc1234 Add scene\x1f2026-03-22 10:30:00 +0100\n"
    "stash@{1}\x1fOn main: texture work\x1f2026-03-21 15:45:00 +0100"
)


@pytest.mark.unit
def test_stash_list_parses_entries() -> None:
    runner = MagicMock()
    runner.run_git.return_value = RunResult(
        stdout=_STASH_OUTPUT, stderr="", returncode=0, command=["git", "stash", "list"]
    )
    git = GitService(runner, FileSystem())
    result = git.stash_list(Path("/repo"))
    assert is_ok(result)
    entries = result.value  # type: ignore[union-attr]
    assert len(entries) == 2
    assert entries[0].ref == "stash@{0}"
    assert entries[0].branch == "main"
    assert entries[0].index == 0
    assert entries[1].ref == "stash@{1}"
    assert entries[1].message == "On main: texture work"


@pytest.mark.unit
def test_stash_save_succeeds() -> None:
    runner = MagicMock()
    runner.run_git.return_value = RunResult(
        stdout="Saved working directory and index state WIP on main",
        stderr="", returncode=0, command=["git", "stash", "push"]
    )
    git = GitService(runner, FileSystem())
    result = git.stash_save(Path("/repo"), "texture work")
    assert is_ok(result)
    call_args = runner.run_git.call_args_list[0][0][0]
    assert "stash" in call_args
    assert "push" in call_args
    assert "texture work" in call_args
    # LFS process filter must be bypassed to prevent index normalisation.
    assert "filter.lfs.required=false" in call_args
    assert any(a.startswith("filter.lfs.process=") for a in call_args)


@pytest.mark.unit
def test_stash_pop_returns_conflict_error() -> None:
    runner = MagicMock()
    runner.run_git.return_value = RunResult(
        stdout="CONFLICT (content): Merge conflict in appartement.blend",
        stderr="", returncode=1, command=["git", "stash", "pop"]
    )
    git = GitService(runner, FileSystem())
    result = git.stash_pop(Path("/repo"), "stash@{0}")
    assert not is_ok(result)
    assert isinstance(result.error, StashConflictError)  # type: ignore[union-attr]


@pytest.mark.unit
def test_pull_fails_when_working_tree_dirty() -> None:
    runner = MagicMock()
    runner.run_git.return_value = RunResult(
        stdout="",
        stderr=(
            "error: Your local changes to the following files would be overwritten by merge:\n"
            "\tappartement.blend\n"
            "Please commit your changes or stash them before you merge.\n"
            "Aborting"
        ),
        returncode=1,
        command=["git", "pull", "--no-rebase", "--no-autostash", "origin"],
    )
    git = GitService(runner, FileSystem())
    result = git.pull(Path("/repo"))
    assert not is_ok(result)
    assert isinstance(result.error, DirtyWorkingTreeError)  # type: ignore[union-attr]
