"""Git workspace manager for DevPilot Chapter 3.

Clones target repositories into isolated task workspaces,
creates task-specific branches, and provides controlled Git operations.
Never modifies the repository's main/default branch.

Lifecycle: ACTIVE -> AWAITING_QA -> AWAITING_REVIEW -> AWAITING_DELIVERY -> CLOSED
Cleanup only happens on explicit task closure or cancellation.
"""

import os
import stat
import shutil
from pathlib import Path
from typing import Optional

from git import Repo, GitCommandError

from app.core.config import get_settings
from app.core.logging import logger


# ── Workspace root ──────────────────────────────────────────────────────────

def get_workspace_root() -> Path:
    """Return absolute persistent workspace root from settings."""
    root = Path(get_settings().WORKSPACE_ROOT).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _workspace_path(task_id: str) -> Path:
    return get_workspace_root() / task_id


# ── Read-only helpers ───────────────────────────────────────────────────────

def get_workspace_path(task_id: str) -> Path:
    return _workspace_path(task_id)


def get_current_branch(workspace_path: Path) -> str:
    repo = Repo(str(workspace_path))
    return repo.active_branch.name


def get_diff(workspace_path: Path, base_branch: str = "main") -> str:
    """Return unified diff of active changes, or branch changes against base branch if clean."""
    try:
        repo = Repo(str(workspace_path), search_parent_directories=True)
    except Exception:
        return ""

    try:
        staged = repo.git.diff("--cached")
        unstaged = repo.git.diff()
        active_diff = (staged + "\n" + unstaged).strip()
        if active_diff:
            return active_diff
        try:
            branch_diff = repo.git.diff(f"{base_branch}...HEAD")
            if branch_diff.strip():
                return branch_diff.strip()
        except Exception:
            pass
        try:
            return repo.git.diff("HEAD~1").strip()
        except Exception:
            return ""
    except Exception:
        return ""


# ── Idempotent workspace preparation ───────────────────────────────────────

def prepare_task_workspace(
    clone_url: str,
    task_id: str,
    github_token: Optional[str] = None,
    default_branch: str = "main",
) -> Path:
    """Idempotent: return existing workspace if already a valid git repo; else clone fresh.

    - If workspace exists and `.git` is intact, check out the existing task branch and return.
    - If workspace is corrupted or absent, remove it and clone fresh.
    - Never silently deletes a healthy workspace.

    Returns:
        Absolute path to the workspace (persistent, survives restarts).

    Raises:
        RuntimeError: on clone or branch failure.
    """
    workspace = _workspace_path(task_id)
    branch_name = f"devpilot/task-{task_id}"

    if workspace.exists():
        # Validate it is a real git repo
        try:
            repo = Repo(str(workspace))
            # Try to check out the task branch (may already be on it)
            try:
                repo.git.checkout(branch_name)
                logger.info(f"[{task_id}] Reusing existing workspace at {workspace}")
            except GitCommandError:
                # Branch doesn't exist yet — create it now
                repo.git.checkout("-b", branch_name)
                logger.info(f"[{task_id}] Workspace exists; created branch {branch_name}")
            return workspace
        except Exception as exc:
            logger.warning(f"[{task_id}] Existing workspace is invalid ({exc}); re-cloning.")
            _force_remove(workspace)

    # Clone fresh
    workspace.parent.mkdir(parents=True, exist_ok=True)
    auth_url = _inject_token(clone_url, github_token)

    logger.info(f"[{task_id}] Cloning repository into {workspace}")
    try:
        repo = Repo.clone_from(auth_url, str(workspace), branch=default_branch)
        if repo.head.is_detached:
            repo.git.checkout(default_branch)
        repo.git.checkout("-b", branch_name)
        logger.info(f"[{task_id}] Clone done. Branch: {branch_name}. HEAD: {repo.head.commit.hexsha[:7]}")
        return workspace
    except GitCommandError as exc:
        raise RuntimeError(f"Repository clone failed: {exc}") from exc


# ── Legacy alias (keeps existing call-sites working) ───────────────────────

def clone_repository(
    clone_url: str,
    task_id: str,
    github_token: Optional[str] = None,
    default_branch: str = "main",
) -> Path:
    """Alias for prepare_task_workspace (used by node_clone in execution_service)."""
    return prepare_task_workspace(clone_url, task_id, github_token, default_branch)


# ── Branch helper ───────────────────────────────────────────────────────────

def create_task_branch(workspace_path: Path, task_id: str) -> str:
    """Check out devpilot/task-{task_id}; create it if it doesn't exist.

    Returns branch name. No-op if already on the correct branch.
    """
    branch_name = f"devpilot/task-{task_id}"
    try:
        repo = Repo(str(workspace_path))
        try:
            repo.git.checkout(branch_name)
        except GitCommandError:
            repo.git.checkout("-b", branch_name)
        logger.info(f"On branch {branch_name}")
        return branch_name
    except GitCommandError as exc:
        raise RuntimeError(f"Branch operation failed: {exc}") from exc


# ── Commit helper ───────────────────────────────────────────────────────────

def stage_and_commit(workspace_path: Path, message: str) -> str:
    """Stage all changes and commit. Returns full commit SHA.

    Raises:
        RuntimeError: if nothing to commit or commit fails.
    """
    repo = Repo(str(workspace_path))
    if not repo.is_dirty(untracked_files=True):
        raise RuntimeError("Nothing to commit — no changes detected.")

    repo.git.add("-A")
    commit = repo.index.commit(message)
    sha = commit.hexsha[:7]
    logger.info(f"Committed: {sha} — {message}")
    return commit.hexsha


# ── Safe explicit cleanup ────────────────────────────────────────────────────

def cleanup_task_workspace(task_id: str) -> None:
    """Explicitly remove a task workspace. Only call on CLOSED or CANCELLED.

    Security: target must be a direct child of workspace root (no traversal).

    Raises:
        ValueError: if the resolved path would escape the workspace root.
    """
    workspace_root = get_workspace_root()
    target = (workspace_root / task_id).resolve()

    # Security boundary check
    try:
        target.relative_to(workspace_root)
    except ValueError:
        raise ValueError(
            f"cleanup_task_workspace: '{task_id}' resolves outside workspace root — refusing."
        )

    if not target.exists():
        logger.info(f"[{task_id}] Workspace already absent, nothing to remove.")
        return

    _force_remove(target)
    logger.info(f"[{task_id}] Workspace removed: {target}")


# ── Deprecated shim (do NOT call in new code) ────────────────────────────────

def cleanup_workspace(task_id: str) -> None:
    """Deprecated: use cleanup_task_workspace() instead.

    This shim exists so old call-sites that were not yet updated don't break,
    but it performs NO action — workspaces are now preserved until explicit closure.
    """
    logger.warning(
        f"[{task_id}] cleanup_workspace() called but is now a no-op. "
        "Workspaces are preserved until explicit task closure."
    )


# ── Internal utilities ───────────────────────────────────────────────────────

def _inject_token(clone_url: str, github_token: Optional[str]) -> str:
    """Inject PAT into HTTPS URL. Never logged."""
    if github_token and "github.com" in clone_url:
        return clone_url.replace("https://", f"https://{github_token}@")
    return clone_url


def _handle_readonly(func, path, exc_info):
    """onerror / onexc handler: chmod then retry for Windows read-only files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass  # Best-effort; ignore if still fails


def _force_remove(path: Path) -> None:
    """Remove a directory tree, handling Windows read-only files and open handles."""
    import gc
    import time
    if path.exists():
        gc.collect()
        for attempt in range(3):
            try:
                try:
                    shutil.rmtree(path, onexc=_handle_readonly)
                except TypeError:
                    shutil.rmtree(path, onerror=_handle_readonly)
                if not path.exists():
                    break
            except Exception:
                pass
            gc.collect()
            time.sleep(0.1)
