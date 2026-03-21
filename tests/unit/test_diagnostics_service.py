"""Tests for DiagnosticsService."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitblend.infrastructure.file_system import FileSystem
from gitblend.infrastructure.subprocess_runner import SubprocessRunner
from gitblend.services.diagnostics_service import DiagnosticsService
from gitblend.services.lfs_service import LFSService


@pytest.fixture
def diag_service(fs: FileSystem, runner: SubprocessRunner) -> DiagnosticsService:
    lfs = LFSService(runner, fs)
    return DiagnosticsService(fs, lfs)


@pytest.mark.unit
def test_generate_gitignore_contains_blend1(diag_service: DiagnosticsService) -> None:
    content = diag_service.generate_gitignore()
    assert "*.blend1" in content
    assert "*.blend2" in content
    assert ".DS_Store" in content


@pytest.mark.unit
def test_generate_gitattributes_contains_blend(diag_service: DiagnosticsService) -> None:
    content = diag_service.generate_gitattributes()
    assert "*.blend" in content
    assert "filter=lfs" in content


@pytest.mark.unit
def test_generate_gitattributes_custom_patterns(diag_service: DiagnosticsService) -> None:
    content = diag_service.generate_gitattributes(["*.custom"])
    assert "*.custom" in content
    assert "*.blend" not in content


@pytest.mark.unit
def test_write_gitignore(diag_service: DiagnosticsService, tmp_path: Path) -> None:
    result = diag_service.write_gitignore(tmp_path)
    from gitblend.domain.result import is_ok
    assert is_ok(result)
    assert (tmp_path / ".gitignore").exists()


@pytest.mark.unit
def test_write_gitattributes(diag_service: DiagnosticsService, tmp_path: Path) -> None:
    from gitblend.domain.result import is_ok
    result = diag_service.write_gitattributes(tmp_path)
    assert is_ok(result)
    assert (tmp_path / ".gitattributes").exists()


@pytest.mark.unit
def test_audit_detects_large_files(diag_service: DiagnosticsService, tmp_path: Path) -> None:
    # Create a file larger than 100 MB threshold
    large_file = tmp_path / "huge.blend"
    large_file.write_bytes(b"x" * (101 * 1024 * 1024))  # 101 MB

    from gitblend.domain.result import is_ok
    result = diag_service.audit_project(tmp_path, tmp_path / "test.blend")
    assert is_ok(result)
    report = result.value  # type: ignore[union-attr]
    assert len(report.files_exceeding_github_limit) >= 1
