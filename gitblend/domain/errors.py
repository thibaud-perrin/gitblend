"""Domain error hierarchy for gitblend.

All errors carry a kind (for UX routing), a user-facing message, optional
detail text for logs, and an optional suggestion for what the user should do.
"""

from __future__ import annotations

from .enums import ErrorKind


class GitBlendError(Exception):
    """Base class for all gitblend errors."""

    def __init__(
        self,
        message: str,
        kind: ErrorKind = ErrorKind.INTERNAL,
        detail: str = "",
        suggestion: str = "",
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.detail = detail
        self.suggestion = suggestion

    def __str__(self) -> str:
        parts = [self.message]
        if self.detail:
            parts.append(f"Detail: {self.detail}")
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return "\n".join(parts)


class RepoNotInitializedError(GitBlendError):
    def __init__(self, path: str = "") -> None:
        super().__init__(
            message=f"No git repository found{f' at {path}' if path else ''}.",
            kind=ErrorKind.REPO,
            suggestion="Use 'Init Repository' to create a git repo for this project.",
        )


class DirtyWorkingTreeError(GitBlendError):
    def __init__(self) -> None:
        super().__init__(
            message="Working tree has uncommitted changes.",
            kind=ErrorKind.REPO,
            suggestion="Commit or stash your changes before proceeding.",
        )


class DetachedHeadError(GitBlendError):
    def __init__(self) -> None:
        super().__init__(
            message="Repository is in detached HEAD state.",
            kind=ErrorKind.REPO,
            suggestion="Switch to a branch before committing or pushing.",
        )


class MergeConflictError(GitBlendError):
    def __init__(self, conflicted_files: list[str] | None = None) -> None:
        files = conflicted_files or []
        detail = f"Conflicting files: {', '.join(files)}" if files else ""
        super().__init__(
            message="Merge conflict detected.",
            kind=ErrorKind.REPO,
            detail=detail,
            suggestion="Resolve conflicts manually, then commit the result.",
        )
        self.conflicted_files = files


class AuthError(GitBlendError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(
            message="GitHub authentication failed.",
            kind=ErrorKind.AUTH,
            detail=detail,
            suggestion="Check your token in addon preferences or re-authenticate.",
        )


class NetworkError(GitBlendError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(
            message="Network request failed.",
            kind=ErrorKind.NETWORK,
            detail=detail,
            suggestion="Check your internet connection and try again.",
        )


class GitBinaryNotFoundError(GitBlendError):
    def __init__(self, git_bin: str = "git") -> None:
        super().__init__(
            message=f"Git binary not found: '{git_bin}'.",
            kind=ErrorKind.CONFIG,
            suggestion="Install git or set the correct path in addon preferences.",
        )


class LFSNotAvailableError(GitBlendError):
    def __init__(self) -> None:
        super().__init__(
            message="git-lfs is not installed or not available.",
            kind=ErrorKind.CONFIG,
            suggestion="Install git-lfs from https://git-lfs.com/ to use LFS features.",
        )


class FileTooLargeError(GitBlendError):
    def __init__(self, path: str, size_mb: float, limit_mb: float = 100.0) -> None:
        super().__init__(
            message=f"File '{path}' is {size_mb:.1f} MB, exceeding the {limit_mb:.0f} MB GitHub limit.",
            kind=ErrorKind.USER,
            suggestion="Track this file with git-lfs before pushing.",
        )
        self.path = path
        self.size_mb = size_mb


class NotBlenderProjectError(GitBlendError):
    def __init__(self) -> None:
        super().__init__(
            message="No .blend file is open or the file has not been saved.",
            kind=ErrorKind.USER,
            suggestion="Open and save a .blend file before using gitblend.",
        )


class GitCommandError(GitBlendError):
    def __init__(self, command: list[str], returncode: int, stderr: str) -> None:
        cmd_str = " ".join(command)
        super().__init__(
            message=f"Git command failed (exit {returncode}): {cmd_str}",
            kind=ErrorKind.REPO,
            detail=stderr.strip(),
        )
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


class RemoteNotFoundError(GitBlendError):
    def __init__(self, remote: str = "origin") -> None:
        super().__init__(
            message=f"Remote '{remote}' is not configured.",
            kind=ErrorKind.REPO,
            suggestion="Add a remote or connect to GitHub first.",
        )


class BranchNotFoundError(GitBlendError):
    def __init__(self, branch: str) -> None:
        super().__init__(
            message=f"Branch '{branch}' does not exist.",
            kind=ErrorKind.REPO,
        )
