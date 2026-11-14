"""SQLAlchemy ORM models for DevPilot.

Covers repository tracking, tasks, inspection results,
agent analyses, implementation plans, and human approval decisions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Repository(Base):
    """Connected GitHub repository metadata."""

    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    github_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
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
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="repository", cascade="all, delete-orphan")


class Task(Base):
    """User-submitted engineering task and workflow lifecycle."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    user_requirement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        index=True,
    )  # PENDING, INSPECTING, ANALYZING, PLANNING, AWAITING_APPROVAL, APPROVED, REJECTED, CHANGES_REQUESTED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="tasks")
    inspection: Mapped[Optional["InspectionResult"]] = relationship("InspectionResult", back_populates="task", uselist=False, cascade="all, delete-orphan")
    requirement_analysis: Mapped[Optional["RequirementAnalysis"]] = relationship("RequirementAnalysis", back_populates="task", uselist=False, cascade="all, delete-orphan")
    implementation_plan: Mapped[Optional["ImplementationPlan"]] = relationship("ImplementationPlan", back_populates="task", uselist=False, cascade="all, delete-orphan")
    approvals: Mapped[List["PlanApproval"]] = relationship("PlanApproval", back_populates="task", cascade="all, delete-orphan")


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
    """Structured requirements analysis from the Product Analyst Agent."""

    __tablename__ = "requirement_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
    requirement_summary: Mapped[str] = mapped_column(Text, nullable=False)
    functional_requirements: Mapped[List[str]] = mapped_column(JSON, default=list)
    nonfunctional_requirements: Mapped[List[str]] = mapped_column(JSON, default=list)
    acceptance_criteria: Mapped[List[str]] = mapped_column(JSON, default=list)
    ambiguities: Mapped[List[str]] = mapped_column(JSON, default=list)
    clarification_questions: Mapped[List[str]] = mapped_column(JSON, default=list)
    raw_llm_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationship
    task: Mapped["Task"] = relationship("Task", back_populates="requirement_analysis")


class ImplementationPlan(Base):
    """Structured, repository-aware implementation plan from the Architect Agent."""

    __tablename__ = "implementation_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
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
    raw_llm_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationship
    task: Mapped["Task"] = relationship("Task", back_populates="implementation_plan")
    approvals: Mapped[List["PlanApproval"]] = relationship("PlanApproval", back_populates="plan", cascade="all, delete-orphan")


class PlanApproval(Base):
    """Persistent record of human approval, rejection, or requested modifications."""

    __tablename__ = "plan_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("implementation_plans.id", ondelete="CASCADE"), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # APPROVED, REJECTED, CHANGES_REQUESTED
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="approvals")
    plan: Mapped["ImplementationPlan"] = relationship("ImplementationPlan", back_populates="approvals")

