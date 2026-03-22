"""Parser for git stash list output."""

from __future__ import annotations

from ..domain.models import StashEntry

_SEP = "\x1f"


def parse_stash_list(output: str) -> list[StashEntry]:
    """Parse output of ``git stash list --format=%gd%x1f%gs%x1f%ci``.

    Each line is: ``stash@{N}<SEP>subject<SEP>ISO-date``
    """
    entries: list[StashEntry] = []
    for i, line in enumerate(output.splitlines()):
        line = line.strip()
        if not line:
            continue
        parts = line.split(_SEP, 2)
        if len(parts) < 3:
            continue
        ref, subject, date_str = parts
        # Extract branch from "WIP on <branch>: …" or "On <branch>: …"
        branch = ""
        lower = subject.lower()
        if lower.startswith("wip on ") or lower.startswith("on "):
            colon = subject.find(":")
            if colon != -1:
                prefix = subject[:colon]
                branch = prefix.split(" on ", 1)[-1].strip()
        # Truncate ISO date to "YYYY-MM-DD HH:MM"
        date = date_str.strip()[:16]
        entries.append(StashEntry(
            ref=ref.strip(),
            index=i,
            branch=branch,
            message=subject.strip(),
            date=date,
        ))
    return entries
