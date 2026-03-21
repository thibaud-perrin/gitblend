"""Project diagnostics and portability audit."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..domain.errors import GitBlendError, GitCommandError
from ..domain.result import Result, err, ok
from ..infrastructure.file_system import FileSystem
from ..services.lfs_service import BLENDER_LFS_PATTERNS, LFSService

# GitHub's hard limit for individual files
GITHUB_FILE_LIMIT_MB = 100.0
# Soft warning threshold
LARGE_FILE_THRESHOLD_MB = 50.0


@dataclass
class DiagnosticsReport:
    """Full portability audit of a Blender project."""

    absolute_paths: list[str] = field(default_factory=list)
    missing_textures: list[str] = field(default_factory=list)
    missing_linked_libs: list[str] = field(default_factory=list)
    large_files: list[tuple[str, float]] = field(default_factory=list)
    files_exceeding_github_limit: list[tuple[str, float]] = field(default_factory=list)
    has_gitignore: bool = False
    has_gitattributes: bool = False
    lfs_tracked_patterns: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return (
            not self.absolute_paths
            and not self.missing_textures
            and not self.missing_linked_libs
            and not self.files_exceeding_github_limit
        )

    @property
    def warning_count(self) -> int:
        return (
            len(self.absolute_paths)
            + len(self.missing_textures)
            + len(self.missing_linked_libs)
            + len(self.files_exceeding_github_limit)
        )


class DiagnosticsService:
    """Audits a Blender project for portability and git hygiene."""

    def __init__(self, fs: FileSystem, lfs: LFSService) -> None:
        self._fs = fs
        self._lfs = lfs

    def audit_project(
        self,
        repo: Path,
        blend_path: Path,
    ) -> Result[DiagnosticsReport, GitBlendError]:
        """Run a full portability audit.

        Note: texture/library detection requires bpy and must be done
        from the operator layer. This method audits file system concerns.
        """
        report = DiagnosticsReport()

        # Check gitignore and gitattributes
        report.has_gitignore = self._fs.exists(repo / ".gitignore")
        report.has_gitattributes = self._fs.exists(repo / ".gitattributes")

        # LFS tracked patterns
        if self._lfs.is_lfs_available():
            lfs_result = self._lfs.list_tracked(repo)
            if isinstance(lfs_result, type(ok([]))):
                report.lfs_tracked_patterns = lfs_result.value  # type: ignore[union-attr]

        # Scan for large files
        try:
            for path in repo.rglob("*"):
                if ".git" in path.parts:
                    continue
                if not path.is_file():
                    continue
                try:
                    size_bytes = self._fs.size_bytes(path)
                    size_mb = size_bytes / (1024 * 1024)
                    rel_str = str(path.relative_to(repo))
                    if size_mb >= GITHUB_FILE_LIMIT_MB:
                        report.files_exceeding_github_limit.append((rel_str, size_mb))
                    elif size_mb >= LARGE_FILE_THRESHOLD_MB:
                        report.large_files.append((rel_str, size_mb))
                except OSError:
                    continue
        except Exception as e:
            return err(GitCommandError([], 1, str(e)))

        return ok(report)

    def generate_gitignore(self) -> str:
        """Return a Blender-appropriate .gitignore file content."""
        return """\
# gitblend — Blender project .gitignore

# Blender autosave and backup files
*.blend1
*.blend2
*.blend@*

# Blender render output (add exceptions if you commit renders)
# render/

# Python cache
__pycache__/
*.py[co]
*.pyo

# OS metadata
.DS_Store
Thumbs.db
desktop.ini

# Editor temporaries
*.swp
*.swo
*~

# Blender temp files
/tmp/
"""

    def generate_gitattributes(self, patterns: list[str] | None = None) -> str:
        """Return a .gitattributes file content with LFS tracking rules."""
        pats = patterns or BLENDER_LFS_PATTERNS
        lines = [
            "# gitblend — git LFS tracking for Blender binary assets",
            "",
        ]
        for pat in pats:
            lines.append(f"{pat} filter=lfs diff=lfs merge=lfs -text")
        lines.append("")
        return "\n".join(lines)

    def write_gitignore(self, repo: Path) -> Result[None, GitBlendError]:
        """Write a .gitignore file to the repo root."""
        try:
            self._fs.write_text(repo / ".gitignore", self.generate_gitignore())
            return ok(None)
        except OSError as e:
            return err(GitCommandError([], 1, str(e)))

    def write_gitattributes(
        self,
        repo: Path,
        patterns: list[str] | None = None,
    ) -> Result[None, GitBlendError]:
        """Write a .gitattributes file to the repo root."""
        try:
            self._fs.write_text(
                repo / ".gitattributes",
                self.generate_gitattributes(patterns),
            )
            return ok(None)
        except OSError as e:
            return err(GitCommandError([], 1, str(e)))
