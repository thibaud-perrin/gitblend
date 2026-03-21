"""Snapshot / backup service for .blend files.

Creates safety copies before destructive operations (checkout, revert, reset).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..domain.errors import GitBlendError, GitCommandError
from ..domain.result import Result, err, ok
from ..infrastructure.file_system import FileSystem

_BACKUP_DIR = ".gitblend-backups"


class SnapshotService:
    """Manages timestamped backups of .blend files."""

    def __init__(self, fs: FileSystem) -> None:
        self._fs = fs

    def backup_blend(self, blend_path: Path) -> Result[Path, GitBlendError]:
        """Copy the current .blend file to a dated backup directory.

        Backup path: <project_root>/.gitblend-backups/<filename>.<timestamp>.blend

        Returns the path of the created backup.
        """
        if not self._fs.exists(blend_path):
            return err(GitCommandError([], 1, f"File not found: {blend_path}"))

        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_dir = blend_path.parent / _BACKUP_DIR
        stem = blend_path.stem
        suffix = blend_path.suffix
        backup_path = backup_dir / f"{stem}.{timestamp}{suffix}"

        try:
            self._fs.create_dir(backup_dir)
            self._fs.copy(blend_path, backup_path)
        except OSError as e:
            return err(GitCommandError([], 1, str(e)))

        return ok(backup_path)

    def list_backups(self, blend_path: Path) -> list[Path]:
        """Return all backups for the given .blend file, newest first."""
        backup_dir = blend_path.parent / _BACKUP_DIR
        if not self._fs.is_dir(backup_dir):
            return []

        stem = blend_path.stem
        suffix = blend_path.suffix
        pattern = f"{stem}.*{suffix}"
        backups = sorted(
            backup_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return backups

    def restore_backup(
        self,
        backup_path: Path,
        blend_path: Path,
    ) -> Result[None, GitBlendError]:
        """Restore a backup over the current .blend file.

        Creates a backup of the current file before overwriting.
        """
        if not self._fs.exists(backup_path):
            return err(GitCommandError([], 1, f"Backup not found: {backup_path}"))

        # Safety: back up the current file first
        if self._fs.exists(blend_path):
            pre_backup = self.backup_blend(blend_path)
            if isinstance(pre_backup, type(err(None))):
                return pre_backup  # type: ignore[return-value]

        try:
            self._fs.copy(backup_path, blend_path)
        except OSError as e:
            return err(GitCommandError([], 1, str(e)))

        return ok(None)

    def cleanup_old_backups(
        self,
        blend_path: Path,
        keep: int = 10,
    ) -> Result[int, GitBlendError]:
        """Remove old backups, keeping the N most recent. Returns count deleted."""
        backups = self.list_backups(blend_path)
        to_delete = backups[keep:]
        deleted = 0
        for path in to_delete:
            try:
                path.unlink()
                deleted += 1
            except OSError:
                pass
        return ok(deleted)
