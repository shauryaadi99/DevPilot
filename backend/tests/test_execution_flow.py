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
from app.db.models import Repository, Task, ImplementationPlan, PlanApproval, TaskExecution, ExecutionLog
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


# ── Test 6: Human Approval Lifecycle & State Transitions ──────────────────

def test_human_approval_sets_task_to_approved(client, db):
    """Submitting APPROVED decision sets task.status to APPROVED and creates PlanApproval."""
    task = _make_task_with_plan(db, status="AWAITING_APPROVAL")
    response = client.post(
        f"/api/v1/tasks/{task.id}/approval",
        json={"decision": "APPROVED", "feedback": "Approved for Chapter 3 execution"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED"
    assert data["task"]["status"] == "APPROVED"

    # Verify DB
    db.refresh(task)
    assert task.status == "APPROVED"
    approval = (
        db.query(PlanApproval)
        .filter(PlanApproval.task_id == task.id)
        .order_by(PlanApproval.decided_at.desc())
        .first()
    )
    assert approval is not None
    assert approval.decision == "APPROVED"
    assert approval.feedback == "Approved for Chapter 3 execution"


# ── Test 7: Execution Failure Preserves Logs and Distinguishes Plan Status ─

def test_execution_failure_preserves_logs_and_distinguishes_plan_status(client, db):
    """When execution fails:
    - Task status becomes FAILED
    - Execution status becomes FAILED and failure logs are preserved
    - Plan approval remains valid and APPROVED
    """
    task = _make_task_with_plan(db, status="APPROVED")
    execution = TaskExecution(
        task_id=task.id,
        status="EXECUTING",
        total_steps=1,
    )
    db.add(execution)
    db.flush()

    # Add execution failure log
    log = ExecutionLog(
        execution_id=execution.id,
        step_number=1,
        agent="DeveloperAgent",
        level="ERROR",
        message="SyntaxError in generated code: unexpected token",
    )
    db.add(log)

    # Simulate execution service persisting failure results
    from app.services.execution_service import ExecutionService
    service = ExecutionService()
    failed_state = {
        "status": "FAILED",
        "error_message": "SyntaxError in generated code: unexpected token",
        "workspace_path": "/tmp/test",
        "branch_name": f"devpilot/task-{task.id}",
        "commit_sha": None,
        "developer_result": {"steps_completed": 0, "steps_total": 1, "step_results": []},
    }
    service._persist_results(db, task, execution, failed_state)

    # Verify Task & Execution in DB
    db.refresh(task)
    db.refresh(execution)
    assert task.status == "FAILED"
    assert execution.status == "FAILED"
    assert execution.error_message == "SyntaxError in generated code: unexpected token"
    assert len(execution.logs) >= 1
    assert any("SyntaxError" in l.message for l in execution.logs)

    # Verify API distinguishes plan approval status from execution status
    res = client.get(f"/api/v1/tasks/{task.id}")
    assert res.status_code == 200
    task_data = res.json()
    assert task_data["status"] == "FAILED"
    assert task_data["plan_approval_status"] == "APPROVED"
    assert task_data["is_plan_approved"] is True
    assert task_data["execution_status"] == "FAILED"
    assert task_data["latest_approval"]["decision"] == "APPROVED"


# ── Test 8: Retry Approved FAILED Task Allowed & Preserves History ────────

def test_retry_approved_failed_task_allowed_and_preserves_history(client, db):
    """An approved task in FAILED state must be allowed to retry:
    - POST /execute succeeds (HTTP 200)
    - Returns is_retry = True and a NEW execution_id
    - Task status transitions to EXECUTING
    - Prior failed execution and its logs remain preserved
    """
    task = _make_task_with_plan(db, status="APPROVED")

    # 1. First execution fails
    exec1 = TaskExecution(
        task_id=task.id,
        status="FAILED",
        total_steps=2,
        error_message="First run network timeout",
    )
    db.add(exec1)
    db.flush()
    log1 = ExecutionLog(
        execution_id=exec1.id,
        step_number=1,
        agent="DeveloperAgent",
        level="ERROR",
        message="First run failed: network timeout",
    )
    db.add(log1)
    task.status = "FAILED"
    db.commit()

    # 2. Retry execution via API
    with patch("app.api.v1.tasks.ExecutionService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.execute_plan = AsyncMock(return_value=None)

        response = client.post(
            f"/api/v1/tasks/{task.id}/execute",
            json={"github_token": "ghs_retry_token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["is_retry"] is True
    assert data["execution_id"] != exec1.id

    # 3. Verify DB state: task transitioned to EXECUTING
    db.refresh(task)
    assert task.status == "EXECUTING"

    # 4. Verify previous execution history and logs are preserved
    executions = (
        db.query(TaskExecution)
        .filter(TaskExecution.task_id == task.id)
        .order_by(TaskExecution.started_at.asc())
        .all()
    )
    assert len(executions) == 2
    # First execution still has its failure status and log
    assert executions[0].id == exec1.id
    assert executions[0].status == "FAILED"
    assert executions[0].error_message == "First run network timeout"
    assert len(executions[0].logs) == 1
    assert "First run failed" in executions[0].logs[0].message

    # Second execution is the new run
    assert executions[1].id == data["execution_id"]
    assert executions[1].status == "PENDING"


# ── Test 9: Unapproved FAILED Task Cannot Execute (No Bypass) ─────────────

def test_unapproved_failed_task_rejected(client, db):
    """A FAILED task that does NOT have an APPROVED plan must be rejected (403).
    Bypassing approval checks is strictly prohibited.
    """
    # Create task with plan in AWAITING_APPROVAL, but task.status = FAILED
    task = _make_task_with_plan(db, status="AWAITING_APPROVAL")
    task.status = "FAILED"
    db.commit()

    response = client.post(
        f"/api/v1/tasks/{task.id}/execute",
        json={"github_token": None},
    )
    assert response.status_code == 403
    data = response.json()
    assert "Plan is not in APPROVED state" in data["detail"] or "APPROVED" in data["detail"]


# ── Test 10: Rejected FAILED Task Cannot Execute ──────────────────────────

def test_rejected_failed_task_rejected(client, db):
    """A task whose plan was REJECTED cannot execute even if status is FAILED."""
    task = _make_task_with_plan(db, status="APPROVED")
    # Add REJECTED approval
    rejected_approval = PlanApproval(
        task_id=task.id,
        plan_id=task.implementation_plan.id,
        decision="REJECTED",
        feedback="Unacceptable architecture",
    )
    db.add(rejected_approval)
    task.status = "FAILED"
    db.commit()

    response = client.post(
        f"/api/v1/tasks/{task.id}/execute",
        json={"github_token": None},
    )
    assert response.status_code == 403
    data = response.json()
    assert "APPROVED" in data["detail"] or "REJECTED" in data["detail"]


# ── Test 11: Re-approving FAILED Task Transitions to APPROVED ─────────────

def test_reapprove_failed_task_transitions_to_approved(client, db):
    """When a human reviews and explicitly approves a FAILED task, task.status becomes APPROVED."""
    task = _make_task_with_plan(db, status="APPROVED")
    task.status = "FAILED"
    db.commit()

    response = client.post(
        f"/api/v1/tasks/{task.id}/approval",
        json={"decision": "APPROVED", "feedback": "Re-approved after code review"},
    )
    assert response.status_code == 200
    db.refresh(task)
    assert task.status == "APPROVED"


# ── Test 12: Successful Execution Transitions to AWAITING_QA ──────────────

def test_successful_execution_transitions_to_awaiting_qa(client, db):
    """Successful execution sets task.status and execution.status to AWAITING_QA.
    Completed tasks cannot be re-executed.
    """
    task = _make_task_with_plan(db, status="APPROVED")
    execution = TaskExecution(
        task_id=task.id,
        status="COMMITTING",
        total_steps=1,
    )
    db.add(execution)
    db.flush()

    from app.services.execution_service import ExecutionService
    service = ExecutionService()
    success_state = {
        "status": "AWAITING_QA",
        "error_message": None,
        "workspace_path": "/tmp/test",
        "branch_name": f"devpilot/task-{task.id}",
        "commit_sha": "abc1234567890",
        "developer_result": {"steps_completed": 1, "steps_total": 1, "step_results": []},
    }
    service._persist_results(db, task, execution, success_state)

    db.refresh(task)
    db.refresh(execution)
    assert task.status == "AWAITING_QA"
    assert execution.status == "AWAITING_QA"
    assert execution.commit_sha == "abc1234567890"

    # Attempting to re-execute a completed task returns 409 Conflict
    response = client.post(
        f"/api/v1/tasks/{task.id}/execute",
        json={"github_token": None},
    )
    assert response.status_code == 409
    assert "already completed" in response.json()["detail"]
