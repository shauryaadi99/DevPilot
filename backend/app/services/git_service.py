"""Git workspace manager for DevPilot Chapter 3.

Clones target repositories into isolated task workspaces,
creates task-specific branches, and provides controlled Git operations.
Never modifies the repository's main/default branch.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import subprocess

import git
from git import Repo, GitCommandError

from app.core.logging import logger

# Root directory for all task workspaces
WORKSPACE_ROOT = Path(tempfile.gettempdir()) / "devpilot_workspaces"


def _workspace_path(task_id: str) -> Path:
    return WORKSPACE_ROOT / task_id


def clone_repository(
    clone_url: str,
    task_id: str,
    github_token: Optional[str] = None,
    default_branch: str = "main",
) -> Path:
    """Clone repo into isolated workspace. Returns workspace path.

    Args:
        clone_url: HTTPS clone URL.
        task_id: DevPilot task UUID (used as workspace directory name).
        github_token: PAT for private repos; injected into URL, not stored.
        default_branch: Default branch to checkout after clone.

    Returns:
        Absolute path to the cloned workspace.

    Raises:
        RuntimeError: on clone failure.
    """
    workspace = _workspace_path(task_id)

    if workspace.exists():
        logger.warning(f"Workspace already exists for task {task_id}, removing.")
        shutil.rmtree(workspace, ignore_errors=True)

    workspace.parent.mkdir(parents=True, exist_ok=True)

    # Inject token into URL for private repo access (never logged)
    auth_url = clone_url
    if github_token and "github.com" in clone_url:
        auth_url = clone_url.replace("https://", f"https://{github_token}@")

    logger.info(f"Cloning repository for task {task_id} into {workspace}")
    try:
        repo = Repo.clone_from(auth_url, str(workspace), branch=default_branch)
        # Verify we're not on a detached HEAD
        if repo.head.is_detached:
            repo.git.checkout(default_branch)
        logger.info(f"Clone successful. HEAD: {repo.head.commit.hexsha[:7]}")
        return workspace
    except GitCommandError as exc:
        raise RuntimeError(f"Repository clone failed: {exc}") from exc


def create_task_branch(workspace_path: Path, task_id: str) -> str:
    """Create and checkout devpilot/task-{task_id} branch.

    Returns:
        Branch name created.

    Raises:
        RuntimeError: on branch creation failure.
    """
    branch_name = f"devpilot/task-{task_id}"
    try:
        repo = Repo(str(workspace_path))
        repo.git.checkout("-b", branch_name)
        logger.info(f"Created branch {branch_name}")
        return branch_name
    except GitCommandError as exc:
        raise RuntimeError(f"Branch creation failed: {exc}") from exc


def get_current_branch(workspace_path: Path) -> str:
    repo = Repo(str(workspace_path))
    return repo.active_branch.name


def get_diff(workspace_path: Path) -> str:
    """Return unified diff of all staged + unstaged changes."""
    repo = Repo(str(workspace_path))
    staged = repo.git.diff("--cached")
    unstaged = repo.git.diff()
    return (staged + "\n" + unstaged).strip()


def stage_and_commit(workspace_path: Path, message: str) -> str:
    """Stage all changes and commit. Returns commit SHA.

    Raises:
        RuntimeError: if nothing to commit or commit fails.
    """
    repo = Repo(str(workspace_path))
    if not repo.is_dirty(untracked_files=True):
        raise RuntimeError("Nothing to commit — no changes detected.")

    repo.git.add("-A")
    commit = repo.index.commit(message)
    sha = commit.hexsha[:7]
    logger.info(f"Committed changes: {sha} — {message}")
    return commit.hexsha


def cleanup_workspace(task_id: str) -> None:
    """Remove task workspace directory. Called on completion or failure."""
    workspace = _workspace_path(task_id)
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
        logger.info(f"Cleaned up workspace for task {task_id}")


def get_workspace_path(task_id: str) -> Path:
    return _workspace_path(task_id)

