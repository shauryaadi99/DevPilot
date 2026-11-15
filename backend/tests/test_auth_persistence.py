"""Integration and unit tests for PostgreSQL persistence, authentication, PAT encryption,
LangGraph checkpointer, and safe execution resumption.
"""

import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import inspect, text
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import encrypt_pat, decrypt_pat, mask_pat
from app.db.session import engine, SessionLocal
from app.db.models import (
    User,
    UserSession,
    UserCredential,
    Repository,
    Task,
    ImplementationPlan,
    PlanApproval,
    TaskExecution,
    ExecutionLock,
)
from app.services.execution_service import (
    acquire_execution_lock,
    release_execution_lock,
    get_checkpointer,
    ExecutionService,
)
from app.agents.developer import DeveloperAgent
from app.main import app


# ── 1. Database & Table Persistence ──────────────────────────────────────────


def test_postgres_connection_and_tables():
    """Verify SQLAlchemy engine connects to PostgreSQL and all 13 core tables exist."""
    settings = get_settings()
    assert "postgresql" in settings.DATABASE_URL, "Production database must be PostgreSQL."

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    required_tables = {
        "users",
        "user_sessions",
        "user_credentials",
        "repositories",
        "tasks",
        "inspection_results",
        "requirement_analyses",
        "implementation_plans",
        "plan_approvals",
        "task_executions",
        "file_changes",
        "execution_logs",
        "execution_locks",
    }

    missing = required_tables - table_names
    assert not missing, f"Missing required database tables: {missing}"

    # Also verify LangGraph checkpoint tables in PostgreSQL
    langgraph_tables = {"checkpoints", "checkpoint_blobs", "checkpoint_writes"}
    missing_lg = langgraph_tables - table_names
    assert not missing_lg, f"Missing LangGraph checkpointer tables: {missing_lg}"


# ── 2. PAT Encryption & Security ─────────────────────────────────────────────


def test_pat_encryption_roundtrip():
    """Verify AES-256 Fernet encrypt_pat produces ciphertext and decrypt_pat recovers original."""
    raw_pat = "ghp_TestSecretToken1234567890abcdefghijklmnopqrst"
    
    # Encryption produces non-empty bytes different from plaintext
    encrypted = encrypt_pat(raw_pat)
    assert isinstance(encrypted, bytes)
    assert raw_pat.encode() not in encrypted

    # Decryption recovers the exact plaintext
    decrypted = decrypt_pat(encrypted)
    assert decrypted == raw_pat

    # Masking hides secret characters while preserving prefix and last 4 chars
    masked = mask_pat(raw_pat)
    assert masked.startswith("ghp_")
    assert masked.endswith("qrst")
    assert "TestSecretToken" not in masked
    assert "•" in masked


def test_pat_encryption_empty_rejection():
    """Verify encrypting empty or whitespace-only token raises ValueError."""
    with pytest.raises(ValueError):
        encrypt_pat("")
    with pytest.raises(ValueError):
        encrypt_pat("   ")


# ── 3. Dev Login & Session Persistence ───────────────────────────────────────


def test_dev_login_and_session(client: TestClient):
    """Verify dev login creates User and UserSession in PostgreSQL and sets session cookie."""
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    res = client.post("/api/v1/auth/dev-login", json={"username": username})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "authenticated"
    assert data["user"]["username"] == username
    session_id = data["session_id"]
    assert session_id

    # Verify session cookie was set
    assert "devpilot_session_id" in client.cookies

    # Verify persisted in PostgreSQL
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        assert user.username == username

        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert sess is not None
        assert sess.user_id == user.id
    finally:
        db.close()


# ── 4. Session State Rehydration ─────────────────────────────────────────────


def test_session_state_rehydration(client: TestClient):
    """Verify /api/v1/session/state returns full workspace context for browser refresh."""
    db = SessionLocal()
    try:
        # Create test user and session
        test_uid = f"rehydrate_{uuid.uuid4().hex[:8]}"
        user = User(
            github_id=abs(hash(test_uid)) % 100000000,
            username=test_uid,
            name="Rehydrate Tester",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        session_token = f"sess_{uuid.uuid4().hex}"
        session = UserSession(
            id=session_token,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        # Store credential
        raw_pat = "ghp_RehydrateSecretToken12345678"
        cred = UserCredential(
            user_id=user.id,
            encrypted_pat=encrypt_pat(raw_pat),
            pat_masked=mask_pat(raw_pat),
            scopes=["repo", "read:org"],
            is_valid=True,
            last_validated_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.add(cred)

        # Create test repo and task
        repo = Repository(
            user_id=user.id,
            name="demo-repo",
            full_name=f"{test_uid}/demo-repo",
            owner=test_uid,
            default_branch="main",
            html_url=f"https://github.com/{test_uid}/demo-repo",
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

        task = Task(
            repository_id=repo.id,
            user_id=user.id,
            title="Add Persistence",
            user_requirement="Ensure state survives refresh.",
            status="APPROVED",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # Add implementation plan
        plan = ImplementationPlan(
            task_id=task.id,
            version=1,
            summary="Persistent PostgreSQL layer",
            repository_understanding="FastAPI stack",
            files_to_modify=[{"path": "backend/app/db/models.py", "reason": "Update models"}],
            files_to_create=[],
            implementation_steps=[
                {"step_number": 1, "description": "Update models", "file_path": "models.py", "action": "MODIFY"}
            ],
            risks_and_assumptions=["Requires live Postgres"],
        )
        db.add(plan)
        db.commit()

        # Query session state using session cookie
        client.cookies.clear()
        res = client.get("/api/v1/session/state", cookies={"devpilot_session_id": session_token})
        assert res.status_code == 200
        state = res.json()

        assert state["authenticated"] is True
        assert state["user"]["username"] == test_uid
        assert state["pat_status"]["has_pat"] is True
        assert state["pat_status"]["is_valid"] is True
        assert "ghp_" in state["pat_status"]["pat_masked"]
        assert state["selected_repository"]["full_name"] == f"{test_uid}/demo-repo"
        assert state["current_task"]["id"] == task.id
        assert state["current_task"]["title"] == "Add Persistence"
        assert state["current_task"]["implementation_plan"] is not None
    finally:
        db.close()


# ── 5. Execution Lock Idempotency ────────────────────────────────────────────


def test_execution_lock_prevent_duplicate():
    """Verify execution locking prevents two concurrent executions on the same task."""
    db = SessionLocal()
    try:
        # Create user, repo, task to satisfy foreign key constraints
        u_name = f"lockuser_{uuid.uuid4().hex[:8]}"
        user = User(github_id=abs(hash(u_name)) % 100000000, username=u_name)
        db.add(user)
        db.commit()
        db.refresh(user)

        repo = Repository(
            user_id=user.id,
            name="lock-repo",
            full_name=f"{u_name}/lock-repo",
            owner=u_name,
            html_url="https://github.com/demo/lock",
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

        task = Task(repository_id=repo.id, user_id=user.id, title="Lock Task", user_requirement="Testing lock.")
        db.add(task)
        db.commit()
        db.refresh(task)

        exec1 = TaskExecution(task_id=task.id, status="PENDING")
        exec2 = TaskExecution(task_id=task.id, status="PENDING")
        db.add(exec1)
        db.add(exec2)
        db.commit()
        db.refresh(exec1)
        db.refresh(exec2)

        # 1. First lock acquisition succeeds and returns a token
        token1 = acquire_execution_lock(db, task.id, exec1.id)
        assert token1 is not None, "First lock acquisition must succeed."

        # 2. Second lock acquisition on same task must fail
        token2 = acquire_execution_lock(db, task.id, exec2.id)
        assert token2 is None, "Concurrent lock acquisition must be rejected."

        # 3. Release lock
        release_execution_lock(db, task.id, token1)

        # 4. After release, acquisition succeeds again
        token3 = acquire_execution_lock(db, task.id, exec2.id)
        assert token3 is not None
        release_execution_lock(db, task.id, token3)
    finally:
        db.close()


# ── 6. Step Idempotency on Workflow Resumption ───────────────────────────────


@pytest.mark.asyncio
async def test_developer_agent_skips_completed_steps(tmp_path):
    """Verify DeveloperAgent skips steps that are already completed when resumed."""
    from pathlib import Path
    from unittest.mock import AsyncMock, patch
    from app.agents.schemas import ArchitectPlanOutput, ImplementationStep
    from app.agents.developer import StepResult

    agent = DeveloperAgent()

    plan = ArchitectPlanOutput(
        summary="Test multi-step execution",
        implementation_steps=[
            ImplementationStep(step_number=1, title="Step 1 - Skipped", description="Already done", affected_files=["step1.txt"]),
            ImplementationStep(step_number=2, title="Step 2 - Executed", description="Should execute", affected_files=["step2.txt"]),
        ],
    )

    # Mock _execute_step for step 2 so test runs deterministically without external API calls
    mock_step2_result = StepResult(
        step_number=2,
        step_title="Step 2 - Executed",
        file_path="step2.txt",
        change_type="CREATE",
        success=True,
        explanation="Step 2 executed successfully",
    )

    with patch.object(agent, "_execute_step", new=AsyncMock(return_value=mock_step2_result)):
        result = await agent.implement(
            plan=plan,
            workspace_path=Path(tmp_path),
            completed_step_numbers={1},
        )

        assert len(result.step_results) == 2
        # Step 1 was skipped and preserved
        assert result.step_results[0].step_number == 1
        assert result.step_results[0].change_type == "PRESERVED"
        assert result.step_results[0].success is True
        # Step 2 was executed
        assert result.step_results[1].step_number == 2
        assert result.step_results[1].change_type == "CREATE"


# ── 7. LangGraph PostgreSQL Checkpointer ──────────────────────────────────────


def test_langgraph_postgres_checkpointer():
    """Verify LangGraph PostgresSaver checkpointer connects to PostgreSQL."""
    checkpointer = get_checkpointer()
    assert checkpointer is not None, "PostgresSaver checkpointer must be initialized."

    # Verify checkpointer table has records or can be queried
    db = SessionLocal()
    try:
        count = db.execute(text("SELECT COUNT(*) FROM checkpoints")).scalar()
        assert count is not None and count >= 0
    finally:
        db.close()
