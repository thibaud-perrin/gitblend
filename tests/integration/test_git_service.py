"""Integration tests for GitService against real git repositories."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitblend.domain.enums import FileStatus
from gitblend.domain.result import is_ok
from gitblend.infrastructure.file_system import FileSystem
from gitblend.infrastructure.subprocess_runner import SubprocessRunner
from gitblend.services.git_service import GitService


@pytest.fixture
def git(runner: SubprocessRunner, fs: FileSystem) -> GitService:
    return GitService(runner, fs)


@pytest.mark.integration
def test_init_creates_repo(git: GitService, tmp_path: Path) -> None:
    repo = tmp_path / "new_repo"
    repo.mkdir()
    result = git.init(repo)
    assert is_ok(result)
    assert (repo / ".git").exists()


@pytest.mark.integration
def test_is_repo_true_for_existing_repo(git: GitService, working_repo: Path) -> None:
    assert git.is_repo(working_repo)


@pytest.mark.integration
def test_is_repo_false_for_plain_dir(git: GitService, tmp_path: Path) -> None:
    assert not git.is_repo(tmp_path)


@pytest.mark.integration
def test_get_repo_root(git: GitService, working_repo: Path) -> None:
    result = git.get_repo_root(working_repo)
    assert is_ok(result)
    assert result.value == working_repo  # type: ignore[union-attr]


@pytest.mark.integration
def test_status_clean_repo(git: GitService, working_repo: Path) -> None:
    result = git.status(working_repo)
    assert is_ok(result)
    status = result.value  # type: ignore[union-attr]
    assert status.is_clean
    assert not status.is_detached


@pytest.mark.integration
def test_status_shows_new_file(git: GitService, working_repo: Path) -> None:
    (working_repo / "new_file.txt").write_text("hello")
    result = git.status(working_repo)
    assert is_ok(result)
    status = result.value  # type: ignore[union-attr]
    assert any(f.status == FileStatus.UNTRACKED for f in status.untracked)


@pytest.mark.integration
def test_stage_and_commit(git: GitService, working_repo: Path) -> None:
    (working_repo / "change.txt").write_text("new content")
    git.stage(working_repo, [Path("change.txt")])

    status = git.status(working_repo)
    assert is_ok(status)
    assert status.value.staged  # type: ignore[union-attr]

    result = git.commit(working_repo, "Add change.txt")
    assert is_ok(result)
    commit = result.value  # type: ignore[union-attr]
    assert "Add change.txt" in commit.message


@pytest.mark.integration
def test_log_returns_commits(git: GitService, working_repo: Path) -> None:
    result = git.log(working_repo, limit=10)
    assert is_ok(result)
    commits = result.value  # type: ignore[union-attr]
    assert len(commits) >= 1
    assert commits[0].author  # has author info


@pytest.mark.integration
def test_create_and_switch_branch(git: GitService, working_repo: Path) -> None:
    result = git.create_branch(working_repo, "feature/test")
    assert is_ok(result)

    switch_result = git.switch_branch(working_repo, "feature/test")
    assert is_ok(switch_result)

    status_result = git.status(working_repo)
    assert is_ok(status_result)
    assert status_result.value.branch == "feature/test"  # type: ignore[union-attr]


@pytest.mark.integration
def test_delete_branch(git: GitService, working_repo: Path) -> None:
    git.create_branch(working_repo, "to-delete")
    result = git.delete_branch(working_repo, "to-delete")
    assert is_ok(result)


@pytest.mark.integration
def test_checkout_file_reverts_change(git: GitService, working_repo: Path) -> None:
    target = working_repo / "README.md"
    original = target.read_text()
    target.write_text("modified content")

    result = git.checkout_file(working_repo, Path("README.md"))
    assert is_ok(result)
    assert target.read_text() == original


@pytest.mark.integration
def test_add_and_list_remotes(git: GitService, working_repo: Path, bare_repo: Path) -> None:
    result = git.add_remote(working_repo, "origin", str(bare_repo))
    assert is_ok(result)

    remotes_result = git.list_remotes(working_repo)
    assert is_ok(remotes_result)
    remotes = remotes_result.value  # type: ignore[union-attr]
    assert any(r.name == "origin" for r in remotes)


@pytest.mark.integration
def test_push_to_bare_remote(git: GitService, repo_with_remote: Path) -> None:
    # Make a new commit and push
    (repo_with_remote / "new.txt").write_text("content")
    git.stage_all(repo_with_remote)
    git.commit(repo_with_remote, "Add new.txt")

    result = git.push(repo_with_remote)
    assert is_ok(result)


@pytest.mark.integration
def test_create_tag(git: GitService, working_repo: Path) -> None:
    result = git.create_tag(working_repo, "v0.1.0", message="First release")
    assert is_ok(result)
