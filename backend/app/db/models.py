"""SQLAlchemy ORM models for DevPilot.

Covers:
- Authentication & Identity: User, UserSession, UserCredential
- Repositories & Engineering Tasks: Repository, Task
- Planning & Review: InspectionResult, RequirementAnalysis, ImplementationPlan, PlanApproval
- Execution, Audit & Locks: TaskExecution, FileChange, ExecutionLog, ExecutionLock
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


# ── Group A: Authentication, Sessions & Credentials ─────────────────────────


class User(Base):
    """Authenticated developer identity obtained via GitHub OAuth."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    sessions: Mapped[List["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    credential: Mapped[Optional["UserCredential"]] = relationship("UserCredential", back_populates="user", uselist=False, cascade="all, delete-orphan")
    repositories: Mapped[List["Repository"]] = relationship("Repository", back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """Active user browser sessions. Tied to an HTTP-only session cookie."""

    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Secure session token
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    active_chapter: Mapped[str] = mapped_column(String(20), default="2")
    active_repo_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True)
    active_task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    active_repository: Mapped[Optional["Repository"]] = relationship("Repository", foreign_keys=[active_repo_id])
    active_task: Mapped[Optional["Task"]] = relationship("Task", foreign_keys=[active_task_id])


class UserCredential(Base):
    """Encrypted GitHub Personal Access Token (PAT) associated with an authenticated user."""

    __tablename__ = "user_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    encrypted_pat: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    pat_masked: Mapped[str] = mapped_column(String(20), nullable=False)  # Display hint: ghp_••••abcd
    scopes: Mapped[List[str]] = mapped_column(JSON, default=list)        # Validated scopes: ["repo"]
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    last_validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="credential")


# ── Group B: Repositories & Engineering Tasks ───────────────────────────────


class Repository(Base):
    """Connected GitHub repository metadata."""

    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    github_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    html_url: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="repositories")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="repository", cascade="all, delete-orphan")


class Task(Base):
    """User-submitted engineering task and workflow lifecycle."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    user_requirement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        index=True,
    )  # PENDING, INSPECTING, ANALYZING, PLANNING, AWAITING_APPROVAL, APPROVED, REJECTED, CHANGES_REQUESTED, EXECUTING, AWAITING_QA, AWAITING_REVIEW, AWAITING_DELIVERY, CLOSED, FAILED, CANCELLED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="tasks")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="tasks")
    inspection: Mapped[Optional["InspectionResult"]] = relationship("InspectionResult", back_populates="task", uselist=False, cascade="all, delete-orphan")
    requirement_analysis: Mapped[Optional["RequirementAnalysis"]] = relationship("RequirementAnalysis", back_populates="task", uselist=False, cascade="all, delete-orphan")
    implementation_plan: Mapped[Optional["ImplementationPlan"]] = relationship("ImplementationPlan", back_populates="task", uselist=False, cascade="all, delete-orphan")
    approvals: Mapped[List["PlanApproval"]] = relationship("PlanApproval", back_populates="task", cascade="all, delete-orphan")
    executions: Mapped[List["TaskExecution"]] = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")
    lock: Mapped[Optional["ExecutionLock"]] = relationship("ExecutionLock", back_populates="task", uselist=False, cascade="all, delete-orphan")


# ── Group C: Planning & Review ──────────────────────────────────────────────


class InspectionResult(Base):
    """Repository inspection findings and confirmed codebase facts."""

    __tablename__ = "inspection_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
    tree_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    detected_languages: Mapped[List[str]] = mapped_column(JSON, default=list)
    detected_frameworks: Mapped[List[str]] = mapped_column(JSON, default=list)
    detected_entrypoints: Mapped[List[str]] = mapped_column(JSON, default=list)
    manifests_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    confirmed_facts: Mapped[List[str]] = mapped_column(JSON, default=list)
    unknowns: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationship
    task: Mapped["Task"] = relationship("Task", back_populates="inspection")


class RequirementAnalysis(Base):
    """Structured requirement specification output by Product Analyst Agent."""

    __tablename__ = "requirement_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
    requirement_summary: Mapped[str] = mapped_column(Text, nullable=False)
    functional_requirements: Mapped[List[str]] = mapped_column(JSON, default=list)
    nonfunctional_requirements: Mapped[List[str]] = mapped_column(JSON, default=list)
    acceptance_criteria: Mapped[List[str]] = mapped_column(JSON, default=list)
    ambiguities: Mapped[List[str]] = mapped_column(JSON, default=list)
    clarification_questions: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationship
    task: Mapped["Task"] = relationship("Task", back_populates="requirement_analysis")


class ImplementationPlan(Base):
    """Structured architectural plan formulated by Architect Agent."""

    __tablename__ = "implementation_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    repository_understanding: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_observations: Mapped[List[str]] = mapped_column(JSON, default=list)
    files_to_create: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    files_to_modify: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    api_contract_changes: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    implementation_steps: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    dependencies: Mapped[List[str]] = mapped_column(JSON, default=list)
    testing_strategy: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    risks_and_assumptions: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="implementation_plan")
    approvals: Mapped[List["PlanApproval"]] = relationship("PlanApproval", back_populates="plan", cascade="all, delete-orphan")


class PlanApproval(Base):
    """Persistent record of human approval, rejection, or requested modifications."""

    __tablename__ = "plan_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("implementation_plans.id", ondelete="CASCADE"), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # APPROVED, REJECTED, CHANGES_REQUESTED
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="approvals")
    plan: Mapped["ImplementationPlan"] = relationship("ImplementationPlan", back_populates="approvals")


# ── Group D: Autonomous Execution, Audit & Locks ────────────────────────────


class TaskExecution(Base):
    """Tracks a single autonomous execution run of an approved plan."""

    __tablename__ = "task_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", index=True
    )  # PENDING, CLONING, EXECUTING, COMMITTING, AWAITING_QA, AWAITING_REVIEW, AWAITING_DELIVERY, CLOSED, FAILED, CANCELLED
    branch_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    workspace_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="executions")
    file_changes: Mapped[List["FileChange"]] = relationship("FileChange", back_populates="execution", cascade="all, delete-orphan")
    logs: Mapped[List["ExecutionLog"]] = relationship("ExecutionLog", back_populates="execution", cascade="all, delete-orphan", order_by="ExecutionLog.step_number")
    lock: Mapped[Optional["ExecutionLock"]] = relationship("ExecutionLock", back_populates="execution", uselist=False, cascade="all, delete-orphan")


class FileChange(Base):
    """Records a single file operation performed during task execution."""

    __tablename__ = "file_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("task_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # CREATE, MODIFY, DELETE
    diff_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lines_added: Mapped[int] = mapped_column(Integer, default=0)
    lines_removed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationship
    execution: Mapped["TaskExecution"] = relationship("TaskExecution", back_populates="file_changes")


class ExecutionLog(Base):
    """Append-only log of Developer Agent actions during execution."""

    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("task_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str] = mapped_column(String(20), default="INFO")  # INFO, WARNING, ERROR
    agent: Mapped[str] = mapped_column(String(100), default="DeveloperAgent")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationship
    execution: Mapped["TaskExecution"] = relationship("TaskExecution", back_populates="logs")


class ExecutionLock(Base):
    """Distributed execution lock to prevent parallel execution runs on the same task."""

    __tablename__ = "execution_locks"

    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("task_executions.id", ondelete="CASCADE"), nullable=False)
    lock_token: Mapped[str] = mapped_column(String(64), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="lock")
    execution: Mapped["TaskExecution"] = relationship("TaskExecution", back_populates="lock")
