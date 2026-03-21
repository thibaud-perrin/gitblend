"""Core git service — all git operations go through here."""

from __future__ import annotations

from pathlib import Path

from ..domain.enums import SyncState
from ..domain.errors import (
    BranchNotFoundError,
    GitBlendError,
    GitCommandError,
    MergeConflictError,
    RemoteNotFoundError,
    RepoNotInitializedError,
)
from ..domain.models import Branch, CommitInfo, GitRemote, RepoStatus
from ..domain.result import Err, Result, err, ok
from ..infrastructure.file_system import FileSystem
from ..infrastructure.parser_git_log import (
    GIT_LOG_FORMAT,
    parse_ahead_behind,
    parse_branch_list,
    parse_log,
    parse_remote_list,
)
from ..infrastructure.parser_git_status import parse_porcelain_v1, split_by_area
from ..infrastructure.subprocess_runner import SubprocessRunner


class GitService:
    """High-level git operations.

    All methods return Result[T, GitBlendError] — they never raise.
    """

    def __init__(self, runner: SubprocessRunner, fs: FileSystem) -> None:
        self._runner = runner
        self._fs = fs

    # ------------------------------------------------------------------ #
    # Repo management                                                      #
    # ------------------------------------------------------------------ #

    def init(self, path: Path) -> Result[Path, GitBlendError]:
        result = self._runner.run_git(["init", str(path)])
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(path)

    def is_repo(self, path: Path) -> bool:
        result = self._runner.run_git(
            ["rev-parse", "--is-inside-work-tree"],
            cwd=path,
        )
        return result.succeeded and result.stdout.strip() == "true"

    def get_repo_root(self, path: Path) -> Result[Path, GitBlendError]:
        result = self._runner.run_git(
            ["rev-parse", "--show-toplevel"],
            cwd=path,
        )
        if result.failed:
            return err(RepoNotInitializedError(str(path)))
        return ok(Path(result.stdout.strip()))

    # ------------------------------------------------------------------ #
    # Status                                                               #
    # ------------------------------------------------------------------ #

    def status(self, repo: Path) -> Result[RepoStatus, GitBlendError]:
        # Branch name
        branch_result = self._runner.run_git(
            ["symbolic-ref", "--short", "HEAD"],
            cwd=repo,
        )
        is_detached = branch_result.failed
        branch = branch_result.stdout.strip() if not is_detached else "HEAD"

        # Porcelain status
        status_result = self._runner.run_git(
            ["status", "--porcelain=v1"],
            cwd=repo,
        )
        if status_result.failed:
            return err(RepoNotInitializedError(str(repo)))

        files = parse_porcelain_v1(status_result.stdout)
        staged, unstaged, untracked, conflicts = split_by_area(files)

        # Ahead/behind
        ahead, behind = 0, 0
        sync_state = SyncState.NO_REMOTE
        ab_result = self._runner.run_git(
            ["rev-list", "--left-right", "--count", "HEAD...@{u}"],
            cwd=repo,
        )
        if ab_result.succeeded:
            ahead, behind = parse_ahead_behind(ab_result.stdout)
            if ahead > 0 and behind > 0:
                sync_state = SyncState.DIVERGED
            elif ahead > 0:
                sync_state = SyncState.AHEAD
            elif behind > 0:
                sync_state = SyncState.BEHIND
            else:
                sync_state = SyncState.SYNCED

        return ok(
            RepoStatus(
                branch=branch,
                sync_state=sync_state,
                staged=staged,
                unstaged=unstaged,
                untracked=untracked,
                conflicts=conflicts,
                is_detached=is_detached,
                ahead=ahead,
                behind=behind,
            )
        )

    # ------------------------------------------------------------------ #
    # Staging and committing                                               #
    # ------------------------------------------------------------------ #

    def stage(self, repo: Path, paths: list[Path]) -> Result[None, GitBlendError]:
        str_paths = [str(p) for p in paths]
        result = self._runner.run_git(["add", "--", *str_paths], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def stage_all(self, repo: Path) -> Result[None, GitBlendError]:
        result = self._runner.run_git(["add", "-A"], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def unstage(self, repo: Path, paths: list[Path]) -> Result[None, GitBlendError]:
        str_paths = [str(p) for p in paths]
        result = self._runner.run_git(["restore", "--staged", "--", *str_paths], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def commit(self, repo: Path, message: str) -> Result[CommitInfo, GitBlendError]:
        result = self._runner.run_git(["commit", "-m", message], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        # Fetch the commit we just made
        log_result = self.log(repo, limit=1)
        if isinstance(log_result, Err):
            return err(log_result.error)
        commits = log_result.value
        if not commits:
            return err(GitCommandError(["commit"], 0, "No commit created"))
        return ok(commits[0])

    # ------------------------------------------------------------------ #
    # History                                                              #
    # ------------------------------------------------------------------ #

    def log(
        self,
        repo: Path,
        limit: int = 50,
        branch: str | None = None,
    ) -> Result[list[CommitInfo], GitBlendError]:
        args = ["log", f"--format={GIT_LOG_FORMAT}", f"-n{limit}"]
        if branch:
            args.append(branch)
        result = self._runner.run_git(args, cwd=repo)
        if result.failed:
            # Empty repo has no commits
            if "does not have any commits" in result.stderr or result.returncode == 128:
                return ok([])
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(parse_log(result.stdout))

    def show_commit(self, repo: Path, hash: str) -> Result[CommitInfo, GitBlendError]:
        result = self._runner.run_git(
            ["show", f"--format={GIT_LOG_FORMAT}", "--no-patch", hash],
            cwd=repo,
        )
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        commits = parse_log(result.stdout)
        if not commits:
            return err(GitCommandError(["show"], 0, f"Commit {hash} not found"))
        return ok(commits[0])

    # ------------------------------------------------------------------ #
    # Branches                                                             #
    # ------------------------------------------------------------------ #

    def list_branches(self, repo: Path) -> Result[list[Branch], GitBlendError]:
        result = self._runner.run_git(["branch", "-a", "-vv"], cwd=repo)
        if result.failed:
            return ok([])  # Empty repo
        return ok(parse_branch_list(result.stdout))

    def create_branch(
        self,
        repo: Path,
        name: str,
        from_ref: str | None = None,
    ) -> Result[Branch, GitBlendError]:
        args = ["branch", name]
        if from_ref:
            args.append(from_ref)
        result = self._runner.run_git(args, cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        from ..domain.enums import BranchType
        return ok(Branch(name=name, type=BranchType.LOCAL, is_current=False))

    def switch_branch(self, repo: Path, name: str) -> Result[None, GitBlendError]:
        result = self._runner.run_git(["switch", name], cwd=repo)
        if result.failed:
            if "did not match" in result.stderr or "pathspec" in result.stderr:
                return err(BranchNotFoundError(name))
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def delete_branch(
        self,
        repo: Path,
        name: str,
        force: bool = False,
    ) -> Result[None, GitBlendError]:
        flag = "-D" if force else "-d"
        result = self._runner.run_git(["branch", flag, name], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def merge(self, repo: Path, branch: str) -> Result[None, GitBlendError]:
        result = self._runner.run_git(["merge", branch], cwd=repo)
        if result.failed:
            if "CONFLICT" in result.stdout or "Automatic merge failed" in result.stdout:
                # Collect conflict paths
                conflicts_result = self._runner.run_git(
                    ["diff", "--name-only", "--diff-filter=U"],
                    cwd=repo,
                )
                files = conflicts_result.stdout.strip().splitlines() if conflicts_result.succeeded else []
                return err(MergeConflictError(files))
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    # ------------------------------------------------------------------ #
    # Restore                                                              #
    # ------------------------------------------------------------------ #

    def checkout_file(
        self,
        repo: Path,
        path: Path,
        ref: str | None = None,
    ) -> Result[None, GitBlendError]:
        args = ["checkout"]
        if ref:
            args.append(ref)
        args.extend(["--", str(path)])
        result = self._runner.run_git(args, cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def checkout_ref(self, repo: Path, ref: str) -> Result[None, GitBlendError]:
        result = self._runner.run_git(["checkout", ref], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def revert_commit(self, repo: Path, hash: str) -> Result[None, GitBlendError]:
        result = self._runner.run_git(["revert", "--no-edit", hash], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    # ------------------------------------------------------------------ #
    # Remotes                                                              #
    # ------------------------------------------------------------------ #

    def list_remotes(self, repo: Path) -> Result[list[GitRemote], GitBlendError]:
        result = self._runner.run_git(["remote", "-v"], cwd=repo)
        if result.failed:
            return ok([])
        return ok(parse_remote_list(result.stdout))

    def add_remote(self, repo: Path, name: str, url: str) -> Result[None, GitBlendError]:
        result = self._runner.run_git(["remote", "add", name, url], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def set_remote_url(self, repo: Path, name: str, url: str) -> Result[None, GitBlendError]:
        result = self._runner.run_git(["remote", "set-url", name, url], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def fetch(self, repo: Path, remote: str = "origin") -> Result[None, GitBlendError]:
        result = self._runner.run_git(["fetch", remote], cwd=repo)
        if result.failed:
            if "Could not resolve host" in result.stderr or "Connection refused" in result.stderr:
                from ..domain.errors import NetworkError
                return err(NetworkError(result.stderr))
            if "Authentication" in result.stderr or "403" in result.stderr:
                from ..domain.errors import AuthError
                return err(AuthError(result.stderr))
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def pull(
        self,
        repo: Path,
        remote: str = "origin",
        branch: str | None = None,
    ) -> Result[None, GitBlendError]:
        args = ["pull", remote]
        if branch:
            args.append(branch)
        result = self._runner.run_git(args, cwd=repo)
        if result.failed:
            if "CONFLICT" in result.stdout:
                return err(MergeConflictError())
            if "Could not resolve host" in result.stderr:
                from ..domain.errors import NetworkError
                return err(NetworkError(result.stderr))
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def push(
        self,
        repo: Path,
        remote: str = "origin",
        branch: str | None = None,
        set_upstream: bool = False,
    ) -> Result[None, GitBlendError]:
        args = ["push"]
        if set_upstream:
            args.append("-u")
        args.append(remote)
        if branch:
            args.append(branch)
        result = self._runner.run_git(args, cwd=repo)
        if result.failed:
            if "has no upstream" in result.stderr or "no upstream" in result.stderr.lower():
                return err(RemoteNotFoundError(remote))
            if "rejected" in result.stderr:
                return err(GitCommandError(result.command, result.returncode, result.stderr))
            if "Could not resolve host" in result.stderr:
                from ..domain.errors import NetworkError
                return err(NetworkError(result.stderr))
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    # ------------------------------------------------------------------ #
    # Config                                                               #
    # ------------------------------------------------------------------ #

    def set_config(self, repo: Path, key: str, value: str) -> Result[None, GitBlendError]:
        result = self._runner.run_git(["config", key, value], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def get_config(self, repo: Path, key: str) -> Result[str, GitBlendError]:
        result = self._runner.run_git(["config", "--get", key], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(result.stdout.strip())

    def set_global_config(self, key: str, value: str) -> Result[None, GitBlendError]:
        result = self._runner.run_git(["config", "--global", key, value])
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def get_global_config(self, key: str) -> Result[str, GitBlendError]:
        result = self._runner.run_git(["config", "--global", "--get", key])
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(result.stdout.strip())

    # ------------------------------------------------------------------ #
    # Tags                                                                 #
    # ------------------------------------------------------------------ #

    def create_tag(
        self,
        repo: Path,
        tag: str,
        message: str = "",
        ref: str = "HEAD",
    ) -> Result[None, GitBlendError]:
        args = ["tag"]
        if message:
            args.extend(["-a", tag, "-m", message, ref])
        else:
            args.extend([tag, ref])
        result = self._runner.run_git(args, cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def push_tags(self, repo: Path, remote: str = "origin") -> Result[None, GitBlendError]:
        result = self._runner.run_git(["push", remote, "--tags"], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)
