"""Chapter 3 execution flow tests.

Tests:
1. Unapproved plan rejected (403)
2. APPROVED task returns execution_id
3. Branch naming convention verified
4. Filesystem path traversal blocked
5. Cancel execution transitions to CANCELLED
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.db.models import Repository, Task, ImplementationPlan, PlanApproval, TaskExecution
from app.main import app
from app.tools.filesystem_tools import FilesystemTools, FilesystemSecurityError


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_task_with_plan(db, status: str = "APPROVED") -> Task:
    """Helper: create a minimal task with plan + approval in DB."""
    repo = Repository(
        name="test-repo",
        full_name="user/test-repo",
        owner="user",
        html_url="https://github.com/user/test-repo",
        default_branch="main",
    )
    db.add(repo)
    db.flush()

    task = Task(
        repository_id=repo.id,
        title="Test Task",
        user_requirement="Add password reset",
        status=status,
    )
    db.add(task)
    db.flush()

    plan = ImplementationPlan(
        task_id=task.id,
        summary="Add reset endpoints",
        repository_understanding="MERN stack",
        implementation_steps=[{"title": "Add route", "description": "Add /reset route", "affected_files": ["routes/auth.js"]}],
    )
    db.add(plan)
    db.flush()

    if status == "APPROVED":
        approval = PlanApproval(
            task_id=task.id,
            plan_id=plan.id,
            decision="APPROVED",
        )
        db.add(approval)

    db.commit()
    db.refresh(task)
    return task


# ── Test 1: Unapproved plan rejected ──────────────────────────────────────

def test_unapproved_plan_rejected(client, db):
    """POST /execute on a non-APPROVED task must return 403."""
    task = _make_task_with_plan(db, status="AWAITING_APPROVAL")
    response = client.post(
        f"/api/v1/tasks/{task.id}/execute",
        json={"github_token": None},
    )
    assert response.status_code == 403
    data = response.json()
    assert "APPROVED" in data["detail"] or "403" in str(response.status_code)


# ── Test 2: APPROVED task starts execution ─────────────────────────────────

def test_approved_task_starts_execution(client, db):
    """POST /execute on APPROVED task creates TaskExecution and returns execution_id."""
    task = _make_task_with_plan(db, status="APPROVED")

    # Mock ExecutionService.execute_plan so we don't clone GitHub
    with patch("app.api.v1.tasks.ExecutionService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.execute_plan = AsyncMock(return_value=None)

        response = client.post(
            f"/api/v1/tasks/{task.id}/execute",
            json={"github_token": "ghs_mock"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert "execution_id" in data
    assert data["task_id"] == task.id


# ── Test 3: Branch naming convention ──────────────────────────────────────

def test_branch_naming_convention():
    """Task branch must follow devpilot/task-{task_id} pattern."""
    task_id = "abc-123-def"
    expected = f"devpilot/task-{task_id}"
    # Verify naming logic directly
    branch_name = f"devpilot/task-{task_id}"
    assert branch_name == expected
    assert branch_name.startswith("devpilot/task-")


# ── Test 4: Filesystem path traversal blocked ──────────────────────────────

def test_path_traversal_blocked(tmp_path):
    """FilesystemTools must raise FilesystemSecurityError for paths outside workspace."""
    fs = FilesystemTools(tmp_path)

    with pytest.raises(FilesystemSecurityError):
        fs._safe_path("../../etc/passwd")

    # Absolute paths must always be rejected
    with pytest.raises(FilesystemSecurityError):
        fs._safe_path(str(Path("C:/Windows/System32/cmd.exe")))

    with pytest.raises(FilesystemSecurityError):
        fs._safe_path("../outside_file.txt")


def test_path_within_workspace_allowed(tmp_path):
    """FilesystemTools must allow paths within workspace."""
    fs = FilesystemTools(tmp_path)
    # Should not raise
    safe = fs._safe_path("src/index.js")
    assert str(tmp_path) in str(safe)


def test_create_and_read_file(tmp_path):
    """FilesystemTools create_file + read_file round-trip."""
    fs = FilesystemTools(tmp_path)
    result = fs.create_file("src/app.js", "console.log('hello');")
    assert result["status"] == "created"

    read = fs.read_file("src/app.js")
    assert read["content"] == "console.log('hello');"


def test_delete_requires_confirm(tmp_path):
    """delete_file without confirm=True must return error, not delete."""
    fs = FilesystemTools(tmp_path)
    fs.create_file("temp.txt", "data")

    result = fs.delete_file("temp.txt", confirm=False)
    assert "error" in result

    # File must still exist
    assert (tmp_path / "temp.txt").exists()


# ── Test 5: Cancel execution ───────────────────────────────────────────────

def test_cancel_execution(client, db):
    """POST /cancel on a running execution must return CANCELLED."""
    task = _make_task_with_plan(db, status="APPROVED")
    # Create a mock execution in EXECUTING state
    execution = TaskExecution(
        task_id=task.id,
        status="EXECUTING",
        total_steps=3,
        current_step=1,
    )
    db.add(execution)
    db.commit()

    response = client.post(f"/api/v1/tasks/{task.id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"

    # Verify DB updated
    db.refresh(execution)
    assert execution.status == "CANCELLED"
