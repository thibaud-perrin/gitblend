"""Centralised git subprocess execution.

All git calls in gitblend go through SubprocessRunner. This isolates
subprocess usage to one place and makes testing easy via dependency injection.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..domain.errors import GitBinaryNotFoundError


def _augmented_env() -> dict[str, str]:
    """Return os.environ with Homebrew and common tool paths prepended.

    Blender on macOS strips the shell PATH, so git-lfs and similar tools
    installed via Homebrew are not findable by child processes spawned by git.
    """
    env = os.environ.copy()
    if platform.system() == "Darwin":
        extra = [
            "/opt/homebrew/bin",   # Apple Silicon Homebrew
            "/opt/homebrew/sbin",
            "/usr/local/bin",      # Intel Homebrew / MacPorts
            "/usr/local/sbin",
        ]
        current = env.get("PATH", "")
        existing = [p for p in current.split(":") if p not in extra]
        env["PATH"] = ":".join(extra + existing)
    return env


@dataclass
class RunResult:
    """Result of a subprocess invocation."""

    stdout: str
    stderr: str
    returncode: int
    command: list[str]

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0

    @property
    def failed(self) -> bool:
        return self.returncode != 0


class SubprocessRunner:
    """Runs git commands via subprocess.

    Args:
        git_bin: Path or name of the git binary (default: "git").
        cwd: Default working directory for commands.
    """

    def __init__(self, git_bin: str = "git", cwd: Path | None = None) -> None:
        self._git_bin = git_bin
        self._cwd = cwd

    def run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        check: bool = False,
        input: str | None = None,
        env: dict[str, str] | None = None,
    ) -> RunResult:
        """Run an arbitrary command and return its result.

        Args:
            args: Command + arguments list.
            cwd: Working directory (overrides instance default).
            check: If True, raises CalledProcessError on non-zero exit.
            input: Optional stdin text.
            env: Environment variables (merged with current env if None).
        """
        working_dir = cwd or self._cwd
        full_env = _augmented_env()
        if env is not None:
            full_env.update(env)
        try:
            proc = subprocess.run(
                args,
                cwd=working_dir,
                capture_output=True,
                text=True,
                input=input,
                env=full_env,
                check=check,
            )
            return RunResult(
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
                command=args,
            )
        except subprocess.CalledProcessError as e:
            return RunResult(
                stdout=e.stdout or "",
                stderr=e.stderr or "",
                returncode=e.returncode,
                command=args,
            )
        except FileNotFoundError:
            raise GitBinaryNotFoundError(args[0]) from None

    def run_git(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        check: bool = False,
        input: str | None = None,
        env: dict[str, str] | None = None,
    ) -> RunResult:
        """Run a git subcommand.

        Args:
            args: Git subcommand + arguments (e.g. ["status", "--porcelain"]).
            cwd: Working directory (overrides instance default).
            check: If True, raises on non-zero exit.
            input: Optional stdin text.
            env: Extra environment variables merged into the current environment.
        """
        git_bin = self._resolve_git_bin()
        return self.run([git_bin, *args], cwd=cwd, check=check, input=input, env=env)

    def _resolve_git_bin(self) -> str:
        resolved = shutil.which(self._git_bin)
        if resolved is None:
            raise GitBinaryNotFoundError(self._git_bin)
        return resolved

    def with_cwd(self, cwd: Path) -> "SubprocessRunner":
        """Return a new runner scoped to the given directory."""
        return SubprocessRunner(git_bin=self._git_bin, cwd=cwd)
