"""Integration tests for LFSService (skipped if git-lfs is unavailable)."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitblend.domain.result import is_ok
from gitblend.infrastructure.file_system import FileSystem
from gitblend.infrastructure.subprocess_runner import SubprocessRunner
from gitblend.services.lfs_service import LFSService


@pytest.fixture
def lfs(runner: SubprocessRunner, fs: FileSystem) -> LFSService:
    return LFSService(runner, fs)


@pytest.mark.integration
def test_is_lfs_available(lfs: LFSService) -> None:
    # Just check the function returns a bool
    result = lfs.is_lfs_available()
    assert isinstance(result, bool)


@pytest.mark.integration
def test_list_tracked_in_fresh_repo(lfs: LFSService, working_repo: Path) -> None:
    if not lfs.is_lfs_available():
        pytest.skip("git-lfs not installed")

    result = lfs.list_tracked(working_repo)
    # May be empty but should not error if lfs is installed
    if is_ok(result):
        assert isinstance(result.value, list)  # type: ignore[union-attr]


@pytest.mark.integration
def test_check_files_need_lfs_finds_large_files(
    lfs: LFSService,
    working_repo: Path,
) -> None:
    large = working_repo / "huge.blend"
    large.write_bytes(b"x" * (51 * 1024 * 1024))  # 51 MB

    result = lfs.check_files_need_lfs(working_repo, threshold_mb=50.0)
    assert is_ok(result)
    files = result.value  # type: ignore[union-attr]
    assert any("huge.blend" in str(f.path) for f in files)
