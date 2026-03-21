"""Parsers for `git log`, `git branch`, and `git remote` output."""

from __future__ import annotations

from datetime import datetime, timezone

from gitblend.domain.enums import BranchType
from gitblend.domain.models import Branch, CommitInfo, GitRemote

# Separator used between commit records
_COMMIT_SEP = "---GITBLEND-COMMIT---"

# git log format that produces deterministic, parseable output
GIT_LOG_FORMAT = f"%H%n%h%n%an%n%ae%n%aI%n%s%n{_COMMIT_SEP}"


def parse_log(output: str) -> list[CommitInfo]:
    """Parse `git log --format=GIT_LOG_FORMAT` output.

    Returns a list of CommitInfo objects in log order (newest first).
    """
    commits: list[CommitInfo] = []
    if not output.strip():
        return commits

    blocks = output.split(_COMMIT_SEP)
    for block in blocks:
        lines = [ln for ln in block.strip().splitlines() if ln.strip()]
        if len(lines) < 5:
            continue
        hash_ = lines[0].strip()
        short_hash = lines[1].strip()
        author = lines[2].strip()
        email = lines[3].strip()
        date_str = lines[4].strip()
        message = lines[5].strip() if len(lines) > 5 else ""

        try:
            date = datetime.fromisoformat(date_str)
        except ValueError:
            date = datetime.now(tz=timezone.utc)

        commits.append(
            CommitInfo(
                hash=hash_,
                short_hash=short_hash,
                author=author,
                email=email,
                date=date,
                message=message,
            )
        )

    return commits


def parse_branch_list(output: str) -> list[Branch]:
    """Parse `git branch -a -vv` output into Branch objects.

    Each line looks like:
      * main                abc1234 [origin/main] Commit message
        feature/foo         def5678 Commit message
        remotes/origin/main abc1234 Commit message
    """
    branches: list[Branch] = []
    for line in output.splitlines():
        if not line.strip():
            continue

        is_current = line.startswith("*")
        stripped = line.lstrip("* ").lstrip()

        # Detect detached HEAD
        if stripped.startswith("(HEAD detached"):
            branches.append(
                Branch(
                    name="HEAD (detached)",
                    type=BranchType.DETACHED,
                    is_current=is_current,
                )
            )
            continue

        parts = stripped.split()
        if not parts:
            continue

        name = parts[0]
        commit_hash = parts[1] if len(parts) > 1 else None

        # Remote branch
        if name.startswith("remotes/"):
            remote_name = name[len("remotes/"):]
            # Skip HEAD pointers
            if remote_name.endswith("/HEAD"):
                continue
            branches.append(
                Branch(
                    name=remote_name,
                    type=BranchType.REMOTE,
                    is_current=False,
                    commit_hash=commit_hash,
                )
            )
            continue

        # Parse upstream from [origin/branch: ahead N, behind M]
        upstream: str | None = None
        rest = " ".join(parts[2:])
        if "[" in rest and "]" in rest:
            bracket_content = rest[rest.index("[") + 1: rest.index("]")]
            upstream_part = bracket_content.split(":")[0].strip()
            upstream = upstream_part if upstream_part else None

        branches.append(
            Branch(
                name=name,
                type=BranchType.LOCAL,
                is_current=is_current,
                upstream=upstream,
                commit_hash=commit_hash,
            )
        )

    return branches


def parse_remote_list(output: str) -> list[GitRemote]:
    """Parse `git remote -v` output into GitRemote objects.

    Each line looks like:
      origin  https://github.com/user/repo.git (fetch)
      origin  https://github.com/user/repo.git (push)
    """
    seen: dict[str, GitRemote] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        name, url, kind = parts[0], parts[1], parts[2].strip("()")
        if name not in seen:
            seen[name] = GitRemote(name=name, url=url)
        if kind == "fetch":
            seen[name] = GitRemote(name=name, url=seen[name].url, fetch_url=url)

    return list(seen.values())


def parse_ahead_behind(output: str) -> tuple[int, int]:
    """Parse `git rev-list --left-right --count HEAD...@{u}` output.

    Returns (ahead, behind) counts.
    """
    parts = output.strip().split()
    if len(parts) >= 2:
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            pass
    return 0, 0
