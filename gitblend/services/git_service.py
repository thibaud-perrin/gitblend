"""Core git service — all git operations go through here."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..domain.enums import ErrorKind, SyncState
from ..domain.errors import (
    BranchNotFoundError,
    DirtyWorkingTreeError,
    GitBlendError,
    GitCommandError,
    LFSNotAvailableError,
    MergeConflictError,
    RemoteNotFoundError,
    RepoNotInitializedError,
    StashConflictError,
)
from ..domain.models import Branch, CommitInfo, GitRemote, RepoStatus, StashEntry
from ..domain.result import Err, Result, err, ok
from ..infrastructure.file_system import FileSystem
from ..infrastructure.parser_git_log import (
    GIT_LOG_FORMAT,
    parse_ahead_behind,
    parse_branch_list,
    parse_log,
    parse_remote_list,
)
from ..infrastructure.parser_git_stash import parse_stash_list
from ..infrastructure.parser_git_status import parse_porcelain_v1, split_by_area
from ..infrastructure.subprocess_runner import SubprocessRunner


def _parse_overwritten_files(stderr: str) -> list[str]:
    """Extract file names from git's 'would be overwritten by merge' error."""
    files: list[str] = []
    in_list = False
    for line in stderr.splitlines():
        if "would be overwritten" in line:
            in_list = True
        elif in_list:
            stripped = line.strip()
            if stripped and not stripped.startswith("Please") and not stripped.startswith("Aborting"):
                files.append(stripped)
            else:
                break
    return files


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

    def clone(self, url: str, target_dir: Path, token: str | None = None) -> Result[Path, GitBlendError]:
        # Prevent git from hanging waiting for interactive credentials in a background thread
        env = {"GIT_TERMINAL_PROMPT": "0"}

        # Inject token into HTTPS URL so no credential helper is needed
        auth_url = url
        if token and url.startswith("https://github.com/"):
            auth_url = url.replace("https://", f"https://oauth2:{token}@", 1)

        result = self._runner.run_git(["clone", auth_url, str(target_dir)], env=env)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))

        # Strip the token from the stored remote URL — never persist it in .git/config
        if auth_url != url:
            self._runner.run_git(["remote", "set-url", "origin", url], cwd=target_dir)

        return ok(target_dir)

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
            if "filter-process" in status_result.stderr or "git-lfs" in status_result.stderr:
                # LFS not installed but required=true in gitconfig — repo IS valid,
                # we just can't enumerate dirty files. Return branch-only status.
                return ok(RepoStatus(
                    branch=branch,
                    sync_state=SyncState.NO_REMOTE,
                    staged=[],
                    unstaged=[],
                    untracked=[],
                    conflicts=[],
                    is_detached=is_detached,
                    ahead=0,
                    behind=0,
                ))
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
            if "filter-process" in result.stderr or "git-lfs" in result.stderr:
                return err(LFSNotAvailableError())
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def stage_all(self, repo: Path) -> Result[None, GitBlendError]:
        result = self._runner.run_git(["add", "-A"], cwd=repo)
        if result.failed:
            if "filter-process" in result.stderr or "git-lfs" in result.stderr:
                return err(LFSNotAvailableError())
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
            stderr = result.stderr.strip()
            if "identity" in stderr or "ident name" in stderr or "Please tell me who you are" in stderr:
                return err(GitBlendError(
                    message="Git user identity is not configured.",
                    kind=ErrorKind.CONFIG,
                    detail=stderr,
                    suggestion=(
                        "Run in a terminal:\n"
                        '  git config --global user.name "Your Name"\n'
                        '  git config --global user.email "you@example.com"'
                    ),
                ))
            if "cannot run gpg" in stderr or ("gpg" in stderr and "failed to sign" in stderr):
                return err(GitBlendError(
                    message="GPG commit signing is enabled but gpg is not available.",
                    kind=ErrorKind.CONFIG,
                    detail=stderr,
                    suggestion=(
                        "Either install GPG, or disable commit signing:\n"
                        "  git config --global commit.gpgsign false"
                    ),
                ))
            return err(GitCommandError(result.command, result.returncode, stderr))
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
            if "filter-process" in result.stderr or "git-lfs" in result.stderr:
                return err(LFSNotAvailableError())
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
        # --no-rebase forces merge mode, bypassing git rebase's strict "unstaged changes"
        # check which always fires for LFS-normalised files after stashing.
        # --no-autostash prevents git's rebase.autostash from creating a secondary stash.
        args = ["pull", "--no-rebase", "--no-autostash", remote]
        if branch:
            args.append(branch)
        result = self._runner.run_git(args, cwd=repo)
        if result.failed:
            if "cannot pull with rebase" in result.stderr or (
                "unstaged changes" in result.stderr and "rebase" in result.stderr
            ):
                return err(DirtyWorkingTreeError())
            if "would be overwritten" in result.stderr:
                files = _parse_overwritten_files(result.stderr)
                return err(DirtyWorkingTreeError(files))
            if "CONFLICT" in result.stdout:
                return err(MergeConflictError())
            if "filter-process" in result.stderr or "git-lfs" in result.stderr:
                return err(LFSNotAvailableError())
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
            if "filter-process" in result.stderr or "git-lfs" in result.stderr:
                return err(LFSNotAvailableError())
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

    # ------------------------------------------------------------------ #
    # Stash                                                                #
    # ------------------------------------------------------------------ #

    def stash_save(self, repo: Path, message: str = "") -> Result[None, GitBlendError]:
        """Stash current changes (``git stash push``).

        Two LFS-related problems are suppressed here:

        1. **Filter normalisation** — ``filter.lfs.process`` is pointed at a path that
           is guaranteed not to exist (a file inside the temp directory that is never
           created). Git tries to exec it, gets ENOENT, prints a non-fatal warning to
           stderr, and falls through to the legacy ``smudge``/``clean`` filters (both
           set to ``cat``). This is intentional: an empty string falls back to the
           global gitconfig value (``git-lfs``), and a real executable such as
           ``/usr/bin/false`` causes git to spawn it as a gitfilter2 IPC process which
           exits without completing the pkt-line handshake — git then reports
           "the remote end hung up unexpectedly" (exit 128), even with
           ``filter.lfs.required=false``.

        2. **Post-checkout hook** — after the stash commits are created, git runs an
           internal ``reset --hard HEAD`` which triggers the git-lfs ``post-checkout``
           hook. That hook attempts to fetch LFS objects from the remote server.
           Pointing ``core.hooksPath`` at an empty temporary directory prevents any
           hooks from running for the duration of the stash call. The temp directory
           is created and cleaned up automatically by ``tempfile.TemporaryDirectory``.

        Stash entries are local-only, so storing raw binaries instead of LFS pointers
        is safe.
        """
        with tempfile.TemporaryDirectory() as empty_hooks:
            lfs_noop = Path(empty_hooks) / "noop"  # path exists syntactically, file never created
            lfs_bypass = [
                "-c", "filter.lfs.required=false",
                "-c", f"filter.lfs.process={lfs_noop}",  # ENOENT → soft fallback to smudge/clean
                "-c", "filter.lfs.smudge=cat",
                "-c", "filter.lfs.clean=cat",
                "-c", f"core.hooksPath={empty_hooks}",
            ]
            args = lfs_bypass + ["stash", "push"]
            if message:
                args += ["-m", message]
            result = self._runner.run_git(args, cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def stash_list(self, repo: Path) -> Result[list[StashEntry], GitBlendError]:
        """List all stash entries."""
        result = self._runner.run_git(
            ["stash", "list", "--format=%gd\x1f%gs\x1f%ci"],
            cwd=repo,
        )
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(parse_stash_list(result.stdout))

    def stash_pop(self, repo: Path, ref: str = "stash@{0}") -> Result[None, GitBlendError]:
        """Apply and remove a stash entry."""
        result = self._runner.run_git(["stash", "pop", ref], cwd=repo)
        if result.failed:
            if "CONFLICT" in result.stdout or "conflict" in result.stderr.lower():
                return err(StashConflictError())
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def stash_drop(self, repo: Path, ref: str = "stash@{0}") -> Result[None, GitBlendError]:
        """Delete a stash entry without applying it."""
        result = self._runner.run_git(["stash", "drop", ref], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)
