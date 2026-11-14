"""Restricted filesystem tools for the Developer Agent (Chapter 3).

All tools validate paths against the task workspace boundary.
No operation can escape the workspace root via directory traversal.
Destructive operations (delete) have additional guards.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, List


class FilesystemSecurityError(Exception):
    """Raised when a path escapes the allowed workspace boundary."""


class FilesystemTools:
    """Sandboxed filesystem operations confined to a single task workspace."""

    def __init__(self, workspace_root: Path):
        # Resolve to absolute path to prevent symlink-based escapes
        self.workspace_root = workspace_root.resolve()

    # ── Path validation ────────────────────────────────────────────────────

    def _safe_path(self, relative_path: str) -> Path:
        """Resolve path and assert it is within workspace_root.

        Args:
            relative_path: Path string (relative or absolute).

        Returns:
            Resolved absolute Path guaranteed inside workspace_root.

        Raises:
            FilesystemSecurityError: if path traversal detected.
        """
        # Reject absolute paths outright (Unix /.. and Windows C:\.. or \etc)
        p = Path(relative_path)
        if p.is_absolute():
            raise FilesystemSecurityError(
                f"Absolute paths are not allowed: '{relative_path}'. "
                f"Use paths relative to the workspace root."
            )

        # Strip leading slashes/backslashes to force relative resolution
        clean = relative_path.lstrip("/\\")
        resolved = (self.workspace_root / clean).resolve()

        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            raise FilesystemSecurityError(
                f"Path '{relative_path}' escapes workspace boundary. "
                f"Access denied."
            )
        return resolved

    # ── Read operations ────────────────────────────────────────────────────

    def list_directory(self, path: str = "") -> Dict[str, Any]:
        """List contents of a directory within the workspace."""
        target = self._safe_path(path)
        if not target.exists():
            return {"error": f"Path does not exist: {path}"}
        if not target.is_dir():
            return {"error": f"Path is not a directory: {path}"}

        entries: List[Dict[str, Any]] = []
        for entry in sorted(target.iterdir()):
            entries.append({
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else None,
            })
        return {
            "path": str(target.relative_to(self.workspace_root)),
            "entries": entries,
        }

    def read_file(self, path: str) -> Dict[str, Any]:
        """Read a file's content. Max 500 KB to protect memory."""
        target = self._safe_path(path)
        if not target.exists():
            return {"error": f"File not found: {path}"}
        if not target.is_file():
            return {"error": f"Not a file: {path}"}

        size = target.stat().st_size
        if size > 500 * 1024:  # 500 KB cap
            return {"error": f"File too large ({size} bytes). Max 500 KB."}

        content = target.read_text(encoding="utf-8", errors="replace")
        return {
            "path": str(target.relative_to(self.workspace_root)),
            "content": content,
            "size": size,
        }

    # ── Write operations ───────────────────────────────────────────────────

    def create_file(self, path: str, content: str) -> Dict[str, Any]:
        """Create a new file. Fails if file already exists."""
        target = self._safe_path(path)
        if target.exists():
            return {"error": f"File already exists: {path}. Use edit_file to modify."}

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {
            "status": "created",
            "path": str(target.relative_to(self.workspace_root)),
            "size": target.stat().st_size,
        }

    def edit_file(self, path: str, content: str) -> Dict[str, Any]:
        """Overwrite an existing file with new content."""
        target = self._safe_path(path)
        if not target.exists():
            return {"error": f"File not found: {path}. Use create_file for new files."}
        if not target.is_file():
            return {"error": f"Not a file: {path}"}

        old_size = target.stat().st_size
        target.write_text(content, encoding="utf-8")
        new_size = target.stat().st_size
        return {
            "status": "edited",
            "path": str(target.relative_to(self.workspace_root)),
            "old_size": old_size,
            "new_size": new_size,
        }

    def upsert_file(self, path: str, content: str) -> Dict[str, Any]:
        """Create or overwrite file (create if missing, edit if exists)."""
        target = self._safe_path(path)
        exists = target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {
            "status": "created" if not exists else "edited",
            "path": str(target.relative_to(self.workspace_root)),
            "size": target.stat().st_size,
        }

    def delete_file(self, path: str, confirm: bool = False) -> Dict[str, Any]:
        """Delete a file. Requires confirm=True as a safety guard."""
        if not confirm:
            return {"error": "delete_file requires confirm=True explicitly."}

        target = self._safe_path(path)
        if not target.exists():
            return {"error": f"File not found: {path}"}
        if not target.is_file():
            return {"error": f"Not a file: {path}. Will not delete directories."}

        target.unlink()
        return {
            "status": "deleted",
            "path": str(target.relative_to(self.workspace_root)),
        }

    # ── Utility ────────────────────────────────────────────────────────────

    def file_exists(self, path: str) -> bool:
        try:
            return self._safe_path(path).is_file()
        except FilesystemSecurityError:
            return False
