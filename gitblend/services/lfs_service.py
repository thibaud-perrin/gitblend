"""Git LFS management service."""

from __future__ import annotations

from pathlib import Path

from gitblend.domain.errors import GitBlendError, GitCommandError, LFSNotAvailableError
from gitblend.domain.models import GitFile
from gitblend.domain.result import Result, err, ok
from gitblend.infrastructure.file_system import FileSystem
from gitblend.infrastructure.subprocess_runner import SubprocessRunner

# Default LFS patterns for Blender projects
BLENDER_LFS_PATTERNS: list[str] = [
    "*.blend",
    "*.fbx",
    "*.usd",
    "*.usdc",
    "*.usda",
    "*.usdz",
    "*.abc",
    "*.exr",
    "*.hdr",
    "*.tif",
    "*.tiff",
    "*.psd",
    "*.mp4",
    "*.mov",
    "*.avi",
    "*.obj",
    "*.ply",
    "*.stl",
    "*.bvh",
    "*.vdb",
]


class LFSService:
    """Git LFS operations.

    All methods return Result[T, GitBlendError].
    """

    def __init__(self, runner: SubprocessRunner, fs: FileSystem) -> None:
        self._runner = runner
        self._fs = fs

    def is_lfs_available(self) -> bool:
        """Return True if git-lfs is installed and accessible."""
        result = self._runner.run(["git", "lfs", "version"])
        return result.succeeded

    def install(self, repo: Path) -> Result[None, GitBlendError]:
        """Run `git lfs install` in the given repo."""
        if not self.is_lfs_available():
            return err(LFSNotAvailableError())
        result = self._runner.run_git(["lfs", "install"], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def track(self, repo: Path, patterns: list[str]) -> Result[None, GitBlendError]:
        """Track file patterns with git-lfs.

        Calls `git lfs track <pattern>` for each pattern. The resulting
        .gitattributes must be committed to take effect.
        """
        if not self.is_lfs_available():
            return err(LFSNotAvailableError())
        for pattern in patterns:
            result = self._runner.run_git(["lfs", "track", pattern], cwd=repo)
            if result.failed:
                return err(GitCommandError(result.command, result.returncode, result.stderr))
        return ok(None)

    def setup_for_blender(self, repo: Path) -> Result[list[str], GitBlendError]:
        """Install LFS and track all standard Blender binary patterns.

        Returns the list of patterns that were tracked.
        """
        install_result = self.install(repo)
        if isinstance(install_result, type(err(None))):
            return install_result  # type: ignore[return-value]

        track_result = self.track(repo, BLENDER_LFS_PATTERNS)
        if isinstance(track_result, type(err(None))):
            return track_result  # type: ignore[return-value]

        return ok(BLENDER_LFS_PATTERNS)

    def list_tracked(self, repo: Path) -> Result[list[str], GitBlendError]:
        """Return the list of patterns currently tracked by git-lfs."""
        if not self.is_lfs_available():
            return err(LFSNotAvailableError())
        result = self._runner.run_git(["lfs", "track"], cwd=repo)
        if result.failed:
            return err(GitCommandError(result.command, result.returncode, result.stderr))
        patterns: list[str] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Listing tracked patterns"):
                continue
            if line.startswith("*"):
                # Format: "    *.blend (.gitattributes)"
                pattern = line.lstrip("* ").split("(")[0].strip()
                if pattern:
                    patterns.append(pattern)
        return ok(patterns)

    def check_files_need_lfs(
        self,
        repo: Path,
        threshold_mb: float = 50.0,
    ) -> Result[list[GitFile], GitBlendError]:
        """Find large files not tracked by LFS that should be.

        Returns GitFile objects for files exceeding threshold_mb.
        """
        from gitblend.domain.enums import FileStatus
        threshold_bytes = int(threshold_mb * 1024 * 1024)
        large_files: list[GitFile] = []

        try:
            # Walk repo directory, skip .git
            for path in repo.rglob("*"):
                if ".git" in path.parts:
                    continue
                if not path.is_file():
                    continue
                try:
                    size = self._fs.size_bytes(path)
                    if size >= threshold_bytes:
                        rel = path.relative_to(repo)
                        large_files.append(GitFile(path=rel, status=FileStatus.UNTRACKED))
                except OSError:
                    continue
        except Exception as e:
            return err(GitCommandError([], 1, str(e)))

        return ok(large_files)
