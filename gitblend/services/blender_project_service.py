"""Blender-project-specific business logic (no bpy dependency)."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..domain.models import BlenderProjectInfo, RepoStatus
from ..infrastructure.file_system import FileSystem

# Treat any directory containing a .blend file as a potential project root.
# Stop walking when a .git directory or filesystem root is reached.
_MAX_WALK_UP = 10


class BlenderProjectService:
    """Utilities for working with Blender project directories."""

    def __init__(self, fs: FileSystem) -> None:
        self._fs = fs

    def detect_project_root(self, blend_path: Path) -> Path:
        """Find the project root from a .blend file path.

        Walks up the tree looking for a .git directory. Falls back to the
        directory that contains the .blend file.
        """
        current = blend_path.parent
        for _ in range(_MAX_WALK_UP):
            if (current / ".git").exists():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        return blend_path.parent

    def suggest_commit_message(self, status: RepoStatus, blend_name: str) -> str:
        """Generate a commit message from the current repo status."""
        staged_count = len(status.staged)
        unstaged_count = len(status.unstaged)
        untracked_count = len(status.untracked)

        if staged_count == 0 and unstaged_count == 0 and untracked_count == 0:
            return f"Update {blend_name}"

        parts: list[str] = []
        if staged_count:
            parts.append(f"{staged_count} staged change{'s' if staged_count != 1 else ''}")
        if unstaged_count:
            parts.append(f"{unstaged_count} modification{'s' if unstaged_count != 1 else ''}")
        if untracked_count:
            parts.append(f"{untracked_count} new file{'s' if untracked_count != 1 else ''}")

        return f"Update {blend_name}: {', '.join(parts)}"

    def get_project_info(self, blend_path: Path) -> BlenderProjectInfo:
        """Return basic project info derivable from the filesystem alone.

        Texture/library discovery requires bpy and must be added in the
        operator layer when bpy is available.
        """
        project_dir = self.detect_project_root(blend_path)
        large_files = self.check_file_sizes(project_dir)
        return BlenderProjectInfo(
            blend_path=blend_path,
            project_dir=project_dir,
            large_files=[(str(p.relative_to(project_dir)), mb) for p, mb in large_files],
        )

    def check_file_sizes(
        self,
        project_dir: Path,
        limit_mb: float = 100.0,
    ) -> list[tuple[Path, float]]:
        """Return a list of (path, size_mb) for files exceeding limit_mb."""
        limit_bytes = limit_mb * 1024 * 1024
        large: list[tuple[Path, float]] = []
        try:
            for path in project_dir.rglob("*"):
                if ".git" in path.parts:
                    continue
                if not path.is_file():
                    continue
                try:
                    size = self._fs.size_bytes(path)
                    if size >= limit_bytes:
                        large.append((path, size / (1024 * 1024)))
                except OSError:
                    continue
        except Exception:
            pass
        return large

    def is_blend_file_saved(self, blend_path: Path | None) -> bool:
        """Return True if the blend_path points to an existing file on disk."""
        if blend_path is None or str(blend_path) == "":
            return False
        return self._fs.exists(blend_path)

    def get_sidecar_path(self, blend_path: Path) -> Path:
        """Return the git-tracked sidecar path for a working .blend file.

        Convention: ``project.blend`` (gitignored) ↔ ``project.git.blend`` (LFS-tracked).
        """
        return blend_path.with_name(blend_path.stem + ".git.blend")

    def sync_blend_to_sidecar(self, blend_path: Path) -> None:
        """Copy the working .blend to the git-tracked sidecar.

        Called before commit or stash so the sidecar reflects the current
        Blender state.
        """
        shutil.copy2(blend_path, self.get_sidecar_path(blend_path))

    def sync_sidecar_to_blend(self, blend_path: Path) -> None:
        """Copy the git-tracked sidecar back to the working .blend.

        Called after pull, checkout, or stash pop so Blender can reload the
        updated file.  No-op if the sidecar does not exist yet.
        """
        sidecar = self.get_sidecar_path(blend_path)
        if sidecar.exists():
            shutil.copy2(sidecar, blend_path)
