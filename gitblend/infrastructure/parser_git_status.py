"""Parser for `git status --porcelain=v1` output."""

from __future__ import annotations

from pathlib import Path

from ..domain.enums import FileStatus
from ..domain.models import GitFile

# XY code → (index_status, working_status)
# X = index (staged), Y = working tree
_XY_TO_STATUS: dict[str, FileStatus] = {
    # Staged
    "A ": FileStatus.STAGED_ADDED,
    "M ": FileStatus.STAGED_MODIFIED,
    "D ": FileStatus.STAGED_DELETED,
    "R ": FileStatus.STAGED_RENAMED,
    "C ": FileStatus.STAGED_RENAMED,  # copied — treat as rename for display
    # Unstaged (index=space, working=modified/deleted)
    " M": FileStatus.MODIFIED,
    " D": FileStatus.DELETED,
    # Both staged and unstaged modifications
    "MM": FileStatus.MODIFIED,
    "AM": FileStatus.MODIFIED,
    "RM": FileStatus.MODIFIED,
    "AD": FileStatus.DELETED,
    "MD": FileStatus.DELETED,
    # Untracked
    "??": FileStatus.UNTRACKED,
    # Ignored
    "!!": FileStatus.IGNORED,
    # Conflict markers
    "DD": FileStatus.CONFLICTED,
    "AU": FileStatus.CONFLICTED,
    "UD": FileStatus.CONFLICTED,
    "UA": FileStatus.CONFLICTED,
    "DU": FileStatus.CONFLICTED,
    "AA": FileStatus.CONFLICTED,
    "UU": FileStatus.CONFLICTED,
}

_STAGED_STATUSES = {
    FileStatus.STAGED_ADDED,
    FileStatus.STAGED_MODIFIED,
    FileStatus.STAGED_DELETED,
    FileStatus.STAGED_RENAMED,
}

_UNSTAGED_STATUSES = {
    FileStatus.MODIFIED,
    FileStatus.DELETED,
    FileStatus.RENAMED,
}


def parse_porcelain_v1(output: str) -> list[GitFile]:
    """Parse `git status --porcelain=v1` output into GitFile objects.

    Args:
        output: Raw stdout from `git status --porcelain=v1 -z` or newline-separated.

    Returns:
        List of GitFile objects, one per changed file.
    """
    files: list[GitFile] = []
    lines = [line for line in output.splitlines() if line]

    i = 0
    while i < len(lines):
        line = lines[i]
        if len(line) < 3:
            i += 1
            continue

        xy = line[:2]
        path_part = line[3:]

        # Renamed lines have "old -> new" or use NUL separation; handle arrow form
        old_path: Path | None = None
        if xy[0] in ("R", "C") or xy[1] in ("R", "C"):
            if " -> " in path_part:
                parts = path_part.split(" -> ", 1)
                old_path = Path(parts[0])
                path_part = parts[1]

        status = _XY_TO_STATUS.get(xy, FileStatus.MODIFIED)
        files.append(GitFile(path=Path(path_part), status=status, old_path=old_path))
        i += 1

    return files


def split_by_area(files: list[GitFile]) -> tuple[list[GitFile], list[GitFile], list[GitFile], list[GitFile]]:
    """Split a flat file list into staged, unstaged, untracked, conflicts."""
    staged = [f for f in files if f.status in _STAGED_STATUSES]
    conflicts = [f for f in files if f.status == FileStatus.CONFLICTED]
    untracked = [f for f in files if f.status == FileStatus.UNTRACKED]
    unstaged = [
        f for f in files
        if f.status not in _STAGED_STATUSES
        and f.status != FileStatus.UNTRACKED
        and f.status != FileStatus.IGNORED
        and f.status != FileStatus.CONFLICTED
    ]
    return staged, unstaged, untracked, conflicts
