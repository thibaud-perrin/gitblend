"""Shared pytest fixtures for gitblend tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from gitblend.infrastructure.file_system import FileSystem
from gitblend.infrastructure.subprocess_runner import SubprocessRunner


@pytest.fixture
def fs() -> FileSystem:
    return FileSystem()


@pytest.fixture
def runner() -> SubprocessRunner:
    return SubprocessRunner()


@pytest.fixture
def working_repo(tmp_path: Path, runner: SubprocessRunner) -> Path:
    """Initialise a real git repo with one initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    runner.run_git(["init", str(repo)])
    runner.run_git(["config", "user.email", "test@example.com"], cwd=repo)
    runner.run_git(["config", "user.name", "Test User"], cwd=repo)
    # Create an initial commit so the repo has a HEAD
    (repo / "README.md").write_text("# Test\n")
    runner.run_git(["add", "README.md"], cwd=repo)
    runner.run_git(["commit", "-m", "Initial commit"], cwd=repo)
    return repo


@pytest.fixture
def bare_repo(tmp_path: Path, runner: SubprocessRunner) -> Path:
    """Create a bare repo that acts as a remote."""
    bare = tmp_path / "remote.git"
    runner.run_git(["init", "--bare", str(bare)])
    return bare


@pytest.fixture
def repo_with_remote(working_repo: Path, bare_repo: Path, runner: SubprocessRunner) -> Path:
    """Working repo with a bare repo configured as 'origin'."""
    runner.run_git(["remote", "add", "origin", str(bare_repo)], cwd=working_repo)
    runner.run_git(["push", "-u", "origin", "HEAD"], cwd=working_repo)
    return working_repo
