"""Workspace lifecycle tests — Chapter 3 persistence.

Tests:
1. workspace survives successful execution (AWAITING_QA)
2. workspace survives failed execution (FAILED)
3. workspace path in DB survives session rebuild (backend restart simulation)
4. Chapter 4 can read Developer Agent's changes from workspace
5. Chapter 5 commit SHA matches DB record
6. explicit closure triggers cleanup (CLOSED)
7. cleanup cannot delete paths outside workspace root
"""

import os
import shutil
import stat
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from git import Repo


# ── helpers ──────────────────────────────────────────────────────────────────

FAKE_TASK_ID = "test-lifecycle-0000-0000-0000-000000000001"
FAKE_BRANCH = f"devpilot/task-{FAKE_TASK_ID}"


def _make_workspace(root: Path, task_id: str = FAKE_TASK_ID) -> Path:
    """Create a minimal git repo inside root/task_id."""
    ws = root / task_id
    ws.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(ws))
    # git requires at least one commit for many operations
    (ws / "README.md").write_text("DevPilot test workspace")
    repo.index.add(["README.md"])
    repo.index.commit("init")
    repo.git.checkout("-b", f"devpilot/task-{task_id}")
    repo.close()
    return ws


# ── 1. Workspace survives successful execution ───────────────────────────────

def test_workspace_survives_successful_execution(tmp_path, monkeypatch):
    """After AWAITING_QA, the workspace directory and .git must still exist."""
    from app.services import git_service

    monkeypatch.setattr(git_service, "get_workspace_root", lambda: tmp_path)
    ws = _make_workspace(tmp_path)

    # Simulate execution completing with AWAITING_QA — no cleanup
    # (cleanup_workspace is now a no-op; cleanup_task_workspace is only called on close)
    git_service.cleanup_workspace(FAKE_TASK_ID)  # should be no-op

    assert ws.exists(), "Workspace was deleted — lifecycle bug!"
    assert (ws / ".git").exists(), ".git was deleted!"


# ── 2. Workspace survives failed execution ───────────────────────────────────

def test_workspace_survives_failed_execution(tmp_path, monkeypatch):
    """FAILED status must NOT trigger workspace deletion."""
    from app.services import git_service

    monkeypatch.setattr(git_service, "get_workspace_root", lambda: tmp_path)
    ws = _make_workspace(tmp_path)

    # Old code called cleanup_workspace on FAILED — verify new shim is a no-op
    git_service.cleanup_workspace(FAKE_TASK_ID)
    assert ws.exists(), "Workspace deleted on FAILED — recovery impossible!"
    assert (ws / ".git").exists()


# ── 3. Workspace path in DB survives session rebuild ─────────────────────────

def test_workspace_path_persists_across_restart(tmp_path, monkeypatch):
    """DB workspace_path must resolve to a real directory after a session rebuild."""
    from app.services import git_service

    monkeypatch.setattr(git_service, "get_workspace_root", lambda: tmp_path)
    ws = _make_workspace(tmp_path)

    # Simulate what the DB stores
    stored_path = str(ws)

    # Simulate backend restart: rebuild path from DB string
    recovered = Path(stored_path)
    assert recovered.exists(), "Workspace path stored in DB no longer valid after restart"
    assert (recovered / ".git").is_dir(), ".git not found in recovered path"


# ── 4. Chapter 4 can access Developer Agent's changes ───────────────────────

def test_chapter_4_can_access_chapter_3_workspace(tmp_path, monkeypatch):
    """Ch4 QA agent reads modified files from the persistent task workspace."""
    from app.services import git_service

    monkeypatch.setattr(git_service, "get_workspace_root", lambda: tmp_path)
    ws = _make_workspace(tmp_path)

    # Simulate Developer Agent writing a file
    impl_file = ws / "src" / "auth.py"
    impl_file.parent.mkdir(parents=True, exist_ok=True)
    impl_file.write_text("def reset_password(): pass\n")
    repo = Repo(str(ws))
    repo.git.add("-A")
    repo.index.commit("feat(devpilot): implement task")

    # Ch4 would do: ws = get_workspace_path(task_id)
    ch4_ws = git_service.get_workspace_path(FAKE_TASK_ID)
    assert ch4_ws.exists()
    assert (ch4_ws / "src" / "auth.py").read_text() == "def reset_password(): pass\n"
    assert Repo(str(ch4_ws)).active_branch.name == FAKE_BRANCH


# ── 5. Chapter 5 commit SHA matches DB record ────────────────────────────────

def test_chapter_5_commit_sha_matches_db(tmp_path, monkeypatch):
    """Ch5 reads commit SHA from workspace and it matches what was stored in DB."""
    from app.services import git_service

    monkeypatch.setattr(git_service, "get_workspace_root", lambda: tmp_path)
    ws = _make_workspace(tmp_path)

    repo = Repo(str(ws))
    (ws / "feature.py").write_text("# feature\n")
    repo.git.add("-A")
    commit = repo.index.commit("feat: add feature")
    db_stored_sha = commit.hexsha  # what _persist_results stores

    # Ch5 reads the workspace and verifies
    ch5_ws = git_service.get_workspace_path(FAKE_TASK_ID)
    ch5_repo = Repo(str(ch5_ws))
    assert ch5_repo.head.commit.hexsha == db_stored_sha


# ── 6. Explicit closure triggers cleanup ─────────────────────────────────────

def test_explicit_closure_triggers_cleanup(tmp_path, monkeypatch):
    """POST /close must remove workspace directory and nothing else."""
    from app.services import git_service

    monkeypatch.setattr(git_service, "get_workspace_root", lambda: tmp_path)
    ws = _make_workspace(tmp_path)
    sibling = tmp_path / "unrelated-workspace"
    sibling.mkdir()

    assert ws.exists()
    git_service.cleanup_task_workspace(FAKE_TASK_ID)
    assert not ws.exists(), "Workspace not removed after explicit close"
    assert sibling.exists(), "Sibling workspace was incorrectly deleted!"


# ── 7. Cleanup cannot escape workspace root ──────────────────────────────────

def test_cleanup_cannot_escape_workspace_root(tmp_path, monkeypatch):
    """Path traversal in task_id must raise ValueError, never delete outside root."""
    from app.services import git_service

    monkeypatch.setattr(git_service, "get_workspace_root", lambda: tmp_path)

    # Craft a task_id that attempts directory traversal
    malicious_ids = [
        "../../../Windows/System32",
        "../../etc/passwd",
        f"../{FAKE_TASK_ID}/../../../",
    ]
    for bad_id in malicious_ids:
        with pytest.raises(ValueError, match="outside workspace root"):
            git_service.cleanup_task_workspace(bad_id)

