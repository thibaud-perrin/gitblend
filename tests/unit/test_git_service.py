"""Unit tests for GitService error detection (mocked subprocess runner)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gitblend.domain.errors import LFSNotAvailableError
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
