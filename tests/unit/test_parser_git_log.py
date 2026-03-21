"""Tests for git log, branch, and remote parsers."""

from __future__ import annotations

import pytest

from gitblend.domain.enums import BranchType
from gitblend.infrastructure.parser_git_log import (
    parse_ahead_behind,
    parse_branch_list,
    parse_log,
    parse_remote_list,
)


@pytest.mark.unit
def test_parse_log_empty() -> None:
    assert parse_log("") == []


@pytest.mark.unit
def test_parse_log_single_commit() -> None:
    output = (
        "abc1234567890abcdef1234567890abcdef123456\n"
        "abc1234\n"
        "Alice\n"
        "alice@example.com\n"
        "2024-01-15T10:30:00+00:00\n"
        "Add scene assets\n"
        "---GITBLEND-COMMIT---\n"
    )
    commits = parse_log(output)
    assert len(commits) == 1
    assert commits[0].short_hash == "abc1234"
    assert commits[0].author == "Alice"
    assert commits[0].message == "Add scene assets"


@pytest.mark.unit
def test_parse_log_multiple_commits() -> None:
    block = (
        "aaa\nbbb\nAuthor\nemail@x.com\n2024-01-01T00:00:00+00:00\nMsg\n---GITBLEND-COMMIT---\n"
    )
    commits = parse_log(block * 3)
    assert len(commits) == 3


@pytest.mark.unit
def test_parse_branch_list_basic() -> None:
    output = (
        "* main                abc1234 [origin/main] Initial commit\n"
        "  feature/lfs         def5678 Add LFS setup\n"
        "  remotes/origin/main abc1234 Initial commit\n"
    )
    branches = parse_branch_list(output)
    local = [b for b in branches if b.type == BranchType.LOCAL]
    remote = [b for b in branches if b.type == BranchType.REMOTE]
    assert len(local) == 2
    assert len(remote) == 1
    main = next(b for b in local if b.name == "main")
    assert main.is_current
    assert main.upstream == "origin/main"


@pytest.mark.unit
def test_parse_remote_list() -> None:
    output = (
        "origin\thttps://github.com/user/repo.git (fetch)\n"
        "origin\thttps://github.com/user/repo.git (push)\n"
    )
    remotes = parse_remote_list(output)
    assert len(remotes) == 1
    assert remotes[0].name == "origin"


@pytest.mark.unit
def test_parse_ahead_behind() -> None:
    assert parse_ahead_behind("2\t3\n") == (2, 3)
    assert parse_ahead_behind("0\t0\n") == (0, 0)
    assert parse_ahead_behind("") == (0, 0)
