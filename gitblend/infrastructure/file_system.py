"""Filesystem abstraction for gitblend.

Wraps all file I/O so services can be tested with mock implementations.
"""

from __future__ import annotations

import shutil
from pathlib import Path


class FileSystem:
    """Real filesystem implementation."""

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()

    def size_bytes(self, path: Path) -> int:
        return path.stat().st_size

    def copy(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def create_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def list_files(self, path: Path, pattern: str = "**/*") -> list[Path]:
        return [p for p in path.glob(pattern) if p.is_file()]

    def find_blend_root(self, blend_path: Path) -> Path:
        """Find the project root from a .blend file path.

        Walks up the directory tree looking for a .git directory.
        Falls back to the .blend file's parent directory.
        """
        current = blend_path.parent
        while True:
            if (current / ".git").exists():
                return current
            parent = current.parent
            if parent == current:
                # Reached filesystem root — fall back to blend file's directory
                return blend_path.parent
            current = parent

    def delete(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
