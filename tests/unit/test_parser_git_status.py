"""Tests for the git status --porcelain parser."""

from __future__ import annotations

import pytest

from gitblend.domain.enums import FileStatus
from gitblend.infrastructure.parser_git_status import parse_porcelain_v1, split_by_area


@pytest.mark.unit
@pytest.mark.parametrize(
    "line, expected_status",
    [
        (" M file.txt", FileStatus.MODIFIED),
        (" D file.txt", FileStatus.DELETED),
        ("M  file.txt", FileStatus.STAGED_MODIFIED),
        ("A  file.txt", FileStatus.STAGED_ADDED),
        ("D  file.txt", FileStatus.STAGED_DELETED),
        ("?? file.txt", FileStatus.UNTRACKED),
        ("UU file.txt", FileStatus.CONFLICTED),
        ("AA file.txt", FileStatus.CONFLICTED),
        ("MM file.txt", FileStatus.MODIFIED),
    ],
)
def test_parse_single_line(line: str, expected_status: FileStatus) -> None:
    files = parse_porcelain_v1(line)
    assert len(files) == 1
    assert files[0].status == expected_status


@pytest.mark.unit
def test_parse_empty_output() -> None:
    assert parse_porcelain_v1("") == []


@pytest.mark.unit
def test_parse_multiple_files() -> None:
    output = " M blender.blend\n?? new_texture.png\nA  script.py\n"
    files = parse_porcelain_v1(output)
    assert len(files) == 3


@pytest.mark.unit
def test_parse_renamed_file() -> None:
    output = "R  new_name.py -> old_name.py"
    files = parse_porcelain_v1(output)
    assert len(files) == 1
    assert files[0].status == FileStatus.STAGED_RENAMED


@pytest.mark.unit
def test_untracked_path() -> None:
    files = parse_porcelain_v1("?? some/nested/file.py")
    assert str(files[0].path) == "some/nested/file.py"


@pytest.mark.unit
def test_split_by_area() -> None:
    output = "A  staged.py\n M modified.txt\n?? untracked.blend\nUU conflict.blend\n"
    files = parse_porcelain_v1(output)
    staged, unstaged, untracked, conflicts = split_by_area(files)
    assert len(staged) == 1
    assert len(unstaged) == 1
    assert len(untracked) == 1
    assert len(conflicts) == 1
