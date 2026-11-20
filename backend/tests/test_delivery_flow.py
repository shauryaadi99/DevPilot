"""Comprehensive tests for Chapter 5: GitHub Delivery, Final Approval 2, and Pull Request flow."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    Repository,
    Task,
    TaskExecution,
    FileChange,
    ImplementationPlan,
    QAReport,
    CodeReviewReport,
    DeliveryApproval,
    PullRequestRecord,
)
from app.services.delivery_service import (
    format_pull_request_content,
    get_task_diff,
    get_task_timeline,
    validate_delivery_eligibility,
    record_delivered_pull_request,
)
from app.services.git_service import push_task_branch


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_task(in_memory_db):
    repo = Repository(
        id="repo-123",
        name="taskflow-app",
        full_name="testuser/taskflow-app",
        owner="testuser",
        default_branch="main",
        html_url="https://github.com/testuser/taskflow-app",
    )
    task = Task(
        id="task-test-5555",
        repository_id=repo.id,
        title="Add User Authentication & Password Reset",
        user_requirement="Add JWT authentication and a password reset flow with bcrypt.",
        status="AWAITING_DELIVERY",
    )
    plan = ImplementationPlan(
        id="plan-1",
        task_id=task.id,
        summary="Implement authController, authRoutes, and User model.",
        repository_understanding="Node.js Express backend with MongoDB.",
        implementation_steps=[
            {"step_number": 1, "step_title": "Create User model", "target_file": "backend/models/User.js"},
            {"step_number": 2, "step_title": "Create authController", "target_file": "backend/controllers/authController.js"},
        ],
    )
    execution = TaskExecution(
        id="exec-1",
        task_id=task.id,
        status="AWAITING_DELIVERY",
        branch_name="devpilot/task-test-5555",
        commit_sha="a1b2c3d4e5f67890",
    )
    fc1 = FileChange(
        execution_id=execution.id,
        file_path="backend/models/User.js",
        change_type="CREATE",
        lines_added=45,
        lines_removed=0,
        diff_summary="Added User schema",
    )
    fc2 = FileChange(
        execution_id=execution.id,
        file_path="backend/controllers/authController.js",
        change_type="CREATE",
        lines_added=80,
        lines_removed=0,
        diff_summary="Added register & login",
    )
    execution.file_changes = [fc1, fc2]

    qa = QAReport(
        id="qa-1",
        task_id=task.id,
        execution_id=execution.id,
        cycle_number=1,
        overall_passed=True,
        tests_passed=5,
        tests_failed=0,
        tests_skipped=0,
        commands_executed=["npm test"],
        acceptance_criteria_results=[
            {"criterion": "User model has password hash", "status": "SATISFIED"},
            {"criterion": "Login returns JWT token", "status": "SATISFIED"},
        ],
    )
    review = CodeReviewReport(
        id="rev-1",
        task_id=task.id,
        execution_id=execution.id,
        cycle_number=1,
        outcome="APPROVED",
        quality_score=9,
        summary="Clean, robust auth implementation with secure bcrypt hashing.",
        correctness_assessment="All endpoints handle error states gracefully.",
        security_assessment="Bcrypt salt rounds sufficient; JWT expiry enforced.",
    )
    in_memory_db.add_all([repo, task, plan, execution, fc1, fc2, qa, review])
    in_memory_db.commit()
    in_memory_db.refresh(task)
    return task


# ── Test 1: Main branch protection in Git push ───────────────────────────────

def test_git_push_protects_main_branch():
    """Verify push_task_branch raises ValueError if target branch is 'main' or 'master'."""
    dummy_path = Path("/tmp/dummy")
    with pytest.raises(ValueError, match="strictly forbidden"):
        push_task_branch(
            workspace_path=dummy_path,
            branch_name="main",
            clone_url="https://github.com/test/repo",
            github_token="fake_token",
        )

    with pytest.raises(ValueError, match="strictly forbidden"):
        push_task_branch(
            workspace_path=dummy_path,
            branch_name="master",
            clone_url="https://github.com/test/repo",
            github_token="fake_token",
        )


# ── Test 2: Rich Multi-Agent PR formatting ───────────────────────────────────

def test_format_pull_request_content(sample_task):
    """Verify PR title and Markdown body contain requirement, plan, QA stats, and review score."""
    title, body = format_pull_request_content(sample_task)

    assert title == "[DevPilot] Add User Authentication & Password Reset"
    assert "## 🚀 DevPilot Autonomous Engineering Delivery" in body
    assert "Add JWT authentication" in body
    assert "Implement authController" in body
    assert "backend/models/User.js" in body
    assert "Overall QA Status:" in body
    assert "5` passed" in body
    assert "Independent Code Review Assessment" in body
    assert "9/10" in body
    assert "devpilot/task-" in body


# ── Test 3: Delivery blocked without Approval 2 ──────────────────────────────

def test_validate_delivery_blocked_without_final_approval_2(in_memory_db, sample_task):
    """Verify validate_delivery_eligibility raises ValueError if Approval 2 is not yet granted."""
    with pytest.raises(ValueError, match="Final Delivery Approval \\(Approval 2\\) is required"):
        validate_delivery_eligibility(sample_task, in_memory_db)


# ── Test 4: Delivery blocked if Approval 2 was REJECTED ──────────────────────

def test_validate_delivery_blocked_when_final_approval_rejected(in_memory_db, sample_task):
    """Verify validate_delivery_eligibility raises ValueError if latest Approval 2 was REJECTED."""
    rej_approval = DeliveryApproval(
        task_id=sample_task.id,
        decision="REJECTED",
        feedback="Missing rate limiting on login endpoint.",
    )
    in_memory_db.add(rej_approval)
    in_memory_db.commit()

    with pytest.raises(ValueError, match="Final Delivery Approval \\(Approval 2\\) is required"):
        validate_delivery_eligibility(sample_task, in_memory_db)


# ── Test 5: Delivery blocked when task status is not ready ───────────────────

def test_validate_delivery_blocked_when_not_ready(in_memory_db, sample_task):
    """Verify validate_delivery_eligibility raises ValueError if task status is PENDING and no approved review."""
    sample_task.status = "PENDING"
    sample_task.review_reports = []
    approval = DeliveryApproval(
        task_id=sample_task.id,
        decision="APPROVED",
    )
    in_memory_db.add(approval)
    in_memory_db.commit()

    with pytest.raises(ValueError, match="is not eligible for delivery"):
        validate_delivery_eligibility(sample_task, in_memory_db)


# ── Test 6: Delivery validation succeeds when ready ──────────────────────────

def test_validate_delivery_succeeds_when_ready(in_memory_db, sample_task):
    """Verify validate_delivery_eligibility succeeds with no exception when approved and ready."""
    approval = DeliveryApproval(
        task_id=sample_task.id,
        decision="APPROVED",
        feedback="Looks great, verified diff.",
    )
    in_memory_db.add(approval)
    in_memory_db.commit()

    # Should not raise
    validate_delivery_eligibility(sample_task, in_memory_db)


# ── Test 7: Recording delivered PR ───────────────────────────────────────────

def test_record_delivered_pull_request(in_memory_db, sample_task):
    """Verify record_delivered_pull_request creates record, updates status, and logs event."""
    pr_data = {
        "pr_number": 42,
        "html_url": "https://github.com/testuser/taskflow-app/pull/42",
        "title": "[DevPilot] Add User Authentication & Password Reset",
        "state": "OPEN",
    }
    pr_record = record_delivered_pull_request(
        db=in_memory_db,
        task=sample_task,
        pr_data=pr_data,
        pr_body="Sample PR Body",
    )

    assert pr_record.id is not None
    assert pr_record.pr_number == 42
    assert pr_record.html_url == "https://github.com/testuser/taskflow-app/pull/42"
    assert pr_record.status == "OPEN"

    # Verify task updated to COMPLETED
    in_memory_db.refresh(sample_task)
    assert sample_task.status == "COMPLETED"
    assert sample_task.pull_request is not None
    assert sample_task.pull_request.pr_number == 42

    # Verify idempotency check ignores already delivered tasks
    validate_delivery_eligibility(sample_task, in_memory_db)


# ── Test 8: End-to-End Timeline & Diff Queries ───────────────────────────────

def test_get_task_timeline_and_diff(in_memory_db, sample_task):
    """Verify get_task_timeline returns chronological events across all chapters."""
    appr = DeliveryApproval(
        task_id=sample_task.id,
        decision="APPROVED",
        feedback="Ready for PR.",
    )
    in_memory_db.add(appr)
    in_memory_db.commit()

    timeline = get_task_timeline(sample_task)
    assert len(timeline) >= 4

    types = [e["type"] for e in timeline]
    assert "TASK_CREATED" in types
    assert "PLAN_GENERATED" in types
    assert "QA_CYCLE" in types
    assert "CODE_REVIEW" in types
    assert "DELIVERY_APPROVED" in types

    diff = get_task_diff(sample_task)
    assert diff["task_id"] == sample_task.id
    assert diff["branch_name"] == "devpilot/task-test-5555"
    assert diff["base_branch"] == "main"
    assert len(diff["file_changes"]) == 2
    assert diff["total_added"] == 125
