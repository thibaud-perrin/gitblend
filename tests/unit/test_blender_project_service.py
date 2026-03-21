"""Tests for BlenderProjectService."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitblend.domain.enums import FileStatus, SyncState
from gitblend.domain.models import GitFile, RepoStatus
from gitblend.infrastructure.file_system import FileSystem
from gitblend.services.blender_project_service import BlenderProjectService


@pytest.fixture
def project_service(fs: FileSystem) -> BlenderProjectService:
    return BlenderProjectService(fs)


@pytest.mark.unit
def test_detect_project_root_finds_git_dir(
    project_service: BlenderProjectService,
    tmp_path: Path,
) -> None:
    git_dir = tmp_path / "project"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()
    sub = git_dir / "scenes"
    sub.mkdir()
    blend = sub / "main.blend"
    blend.write_bytes(b"")
    root = project_service.detect_project_root(blend)
    assert root == git_dir


@pytest.mark.unit
def test_detect_project_root_fallback_to_parent(
    project_service: BlenderProjectService,
    tmp_path: Path,
) -> None:
    blend = tmp_path / "project.blend"
    blend.write_bytes(b"")
    root = project_service.detect_project_root(blend)
    assert root == tmp_path


@pytest.mark.unit
def test_suggest_commit_message_clean(project_service: BlenderProjectService) -> None:
    status = RepoStatus(branch="main", sync_state=SyncState.SYNCED)
    msg = project_service.suggest_commit_message(status, "scene.blend")
    assert "scene.blend" in msg


@pytest.mark.unit
def test_suggest_commit_message_with_changes(project_service: BlenderProjectService) -> None:
    status = RepoStatus(
        branch="main",
        sync_state=SyncState.AHEAD,
        staged=[GitFile(path=Path("a.py"), status=FileStatus.STAGED_ADDED)],
        unstaged=[GitFile(path=Path("b.py"), status=FileStatus.MODIFIED)],
    )
    msg = project_service.suggest_commit_message(status, "main.blend")
    assert "main.blend" in msg
    assert "1 staged" in msg or "staged" in msg


@pytest.mark.unit
def test_check_file_sizes(
    project_service: BlenderProjectService,
    tmp_path: Path,
) -> None:
    small = tmp_path / "small.txt"
    small.write_bytes(b"x" * 100)
    large = tmp_path / "big.blend"
    large.write_bytes(b"x" * (101 * 1024 * 1024))

    large_files = project_service.check_file_sizes(tmp_path, limit_mb=100.0)
    assert any("big.blend" in str(p) for p, _ in large_files)
    assert not any("small.txt" in str(p) for p, _ in large_files)


@pytest.mark.unit
def test_is_blend_file_saved_returns_true(
    project_service: BlenderProjectService,
    tmp_path: Path,
) -> None:
    blend = tmp_path / "test.blend"
    blend.write_bytes(b"")
    assert project_service.is_blend_file_saved(blend)


@pytest.mark.unit
def test_is_blend_file_saved_returns_false_for_none(
    project_service: BlenderProjectService,
) -> None:
    assert not project_service.is_blend_file_saved(None)
