"""Unified session and workspace rehydration endpoint.

Provides complete state restoration for browser refresh, independent of whether
an execution is currently running.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.auth import get_optional_current_user
from app.db.session import get_db
from app.db.models import (
    User,
    UserSession,
    Repository,
    Task,
    InspectionResult,
    RequirementAnalysis,
    ImplementationPlan,
    PlanApproval,
    TaskExecution,
    QAReport,
    CodeReviewReport,
)

router = APIRouter(prefix="/api/v1/session", tags=["Session & State Rehydration"])


@router.get("/state", summary="Restore Full Workspace State on Page Load / Refresh")
async def get_session_state(
    request: Request,
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full application context for immediate UI restoration.

    Restores:
    - User identity & avatar
    - PAT availability & validity (masked only)
    - Active chapter
    - Selected repository
    - Current task, inspection findings, requirements analysis, plan, approvals
    - Execution progress, file changes, and step logs
    """
    if not auth_context:
        return {
            "authenticated": False,
            "user": None,
            "pat_status": {"has_pat": False, "is_valid": False, "pat_masked": None, "scopes": []},
            "active_chapter": "2",
            "selected_repository": None,
            "current_task": None,
            "can_resume": False,
        }

    user, session, decrypted_pat = auth_context

    pat_status = {
        "has_pat": bool(user.credential),
        "is_valid": bool(user.credential and user.credential.is_valid),
        "pat_masked": user.credential.pat_masked if user.credential else None,
        "scopes": user.credential.scopes if user.credential else [],
    }

    # Resolve active repository
    repo: Optional[Repository] = None
    if session.active_repo_id:
        repo = db.query(Repository).filter(Repository.id == session.active_repo_id).first()

    # Resolve active task strictly scoped to active repository
    task: Optional[Task] = None
    if repo:
        if session.active_task_id:
            task = db.query(Task).filter(Task.id == session.active_task_id).first()
            if task and task.repository_id != repo.id:
                # Prevent cross-repository task pollution
                task = None
                session.active_task_id = None
                db.commit()

    # Available repositories for switcher
    repo_query = db.query(Repository)
    if user:
        repo_query = repo_query.filter((Repository.user_id == user.id) | (Repository.user_id.is_(None)))
    user_repos = repo_query.order_by(Repository.updated_at.desc()).all()
    available_repositories = [
        {
            "id": r.id,
            "name": r.name,
            "full_name": r.full_name,
            "owner": r.owner,
            "default_branch": r.default_branch,
            "html_url": r.html_url,
            "description": r.description,
        }
        for r in user_repos
    ]

    # Available tasks for the selected repository
    available_tasks = []
    if repo:
        tasks_query = (
            db.query(Task)
            .filter(Task.repository_id == repo.id)
            .order_by(Task.created_at.desc())
            .all()
        )
        available_tasks = [
            {
                "id": t.id,
                "title": t.title,
                "requirement": t.user_requirement,
                "status": t.status,
                "is_delivered": t.pull_request is not None,
                "pr_number": t.pull_request.pr_number if t.pull_request else None,
                "pr_url": t.pull_request.html_url if t.pull_request else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks_query
        ]

    # Build task detail payload
    task_detail: Optional[Dict[str, Any]] = None
    execution_detail: Optional[Dict[str, Any]] = None
    can_resume = False

    if task:
        # Latest approval
        latest_approval = (
            db.query(PlanApproval)
            .filter(PlanApproval.task_id == task.id)
            .order_by(PlanApproval.decided_at.desc())
            .first()
        )

        # Latest execution
        execution = (
            db.query(TaskExecution)
            .filter(TaskExecution.task_id == task.id)
            .order_by(TaskExecution.started_at.desc())
            .first()
        )

        if execution:
            can_resume = execution.status in ("CLONING", "EXECUTING", "COMMITTING")
            execution_detail = {
                "execution_id": execution.id,
                "task_id": task.id,
                "status": execution.status,
                "branch_name": execution.branch_name,
                "current_step": execution.current_step,
                "total_steps": execution.total_steps,
                "commit_sha": execution.commit_sha,
                "error_message": execution.error_message,
                "started_at": execution.started_at.isoformat(),
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "file_changes": [
                    {
                        "file_path": fc.file_path,
                        "change_type": fc.change_type,
                        "diff_summary": fc.diff_summary,
                        "lines_added": fc.lines_added,
                        "lines_removed": fc.lines_removed,
                    }
                    for fc in execution.file_changes
                ],
                "logs": [
                    {
                        "step_number": log.step_number,
                        "level": log.level,
                        "agent": log.agent,
                        "message": log.message,
                        "timestamp": log.timestamp.isoformat(),
                    }
                    for log in execution.logs
                ],
                "qa_reports": [
                    {
                        "id": qr.id,
                        "cycle_number": qr.cycle_number,
                        "overall_passed": qr.overall_passed,
                        "commands_executed": qr.commands_executed,
                        "tests_passed": qr.tests_passed,
                        "tests_failed": qr.tests_failed,
                        "tests_skipped": qr.tests_skipped,
                        "exit_codes": qr.exit_codes,
                        "logs": qr.logs,
                        "failure_summary": qr.failure_summary,
                        "failure_signature": qr.failure_signature,
                        "test_details": qr.test_details,
                        "acceptance_criteria_results": qr.acceptance_criteria_results,
                        "actionable_feedback": qr.actionable_feedback,
                        "created_at": qr.created_at.isoformat() if qr.created_at else None,
                    }
                    for qr in execution.qa_reports
                ],
                "review_reports": [
                    {
                        "id": rr.id,
                        "cycle_number": rr.cycle_number,
                        "outcome": rr.outcome,
                        "summary": rr.summary,
                        "correctness_assessment": rr.correctness_assessment,
                        "security_assessment": rr.security_assessment,
                        "quality_score": rr.quality_score,
                        "issues": rr.issues,
                        "approval_recommendation": rr.approval_recommendation,
                        "created_at": rr.created_at.isoformat() if rr.created_at else None,
                    }
                    for rr in execution.review_reports
                ],
            }

        is_plan_approved = (
            latest_approval is not None
            and latest_approval.decision == "APPROVED"
            and task.implementation_plan is not None
            and latest_approval.plan_id == task.implementation_plan.id
        )

        task_detail = {
            "id": task.id,
            "title": task.title,
            "requirement": task.user_requirement,
            "status": task.status,
            "plan_approval_status": latest_approval.decision if latest_approval else "PENDING_REVIEW",
            "is_plan_approved": is_plan_approved,
            "execution_status": execution.status if execution else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "repository": {
                "id": task.repository.id,
                "name": task.repository.name,
                "full_name": task.repository.full_name,
                "owner": task.repository.owner,
                "default_branch": task.repository.default_branch,
                "html_url": task.repository.html_url,
            },
            "inspection": {
                "tree_summary": task.inspection.tree_summary,
                "detected_languages": task.inspection.detected_languages,
                "detected_frameworks": task.inspection.detected_frameworks,
                "detected_entrypoints": task.inspection.detected_entrypoints,
                "manifests_summary": task.inspection.manifests_summary,
                "confirmed_facts": task.inspection.confirmed_facts,
                "unknowns": task.inspection.unknowns,
            } if task.inspection else None,
            "requirement_analysis": {
                "requirement_summary": task.requirement_analysis.requirement_summary,
                "functional_requirements": task.requirement_analysis.functional_requirements,
                "nonfunctional_requirements": task.requirement_analysis.nonfunctional_requirements,
                "acceptance_criteria": task.requirement_analysis.acceptance_criteria,
                "ambiguities": task.requirement_analysis.ambiguities,
                "clarification_questions": task.requirement_analysis.clarification_questions,
            } if task.requirement_analysis else None,
            "implementation_plan": {
                "id": task.implementation_plan.id,
                "version": task.implementation_plan.version,
                "summary": task.implementation_plan.summary,
                "repository_understanding": task.implementation_plan.repository_understanding,
                "confirmed_observations": task.implementation_plan.confirmed_observations,
                "files_to_create": task.implementation_plan.files_to_create,
                "files_to_modify": task.implementation_plan.files_to_modify,
                "api_contract_changes": task.implementation_plan.api_contract_changes,
                "implementation_steps": task.implementation_plan.implementation_steps,
                "dependencies": task.implementation_plan.dependencies,
                "testing_strategy": task.implementation_plan.testing_strategy,
                "risks_and_assumptions": task.implementation_plan.risks_and_assumptions,
            } if task.implementation_plan else None,
            "latest_approval": {
                "id": latest_approval.id,
                "decision": latest_approval.decision,
                "feedback": latest_approval.feedback,
                "decided_at": latest_approval.decided_at.isoformat(),
            } if latest_approval else None,
            "approvals": [
                {
                    "id": a.id,
                    "decision": a.decision,
                    "feedback": a.feedback,
                    "decided_at": a.decided_at.isoformat(),
                }
                for a in task.approvals
            ],
            "delivery_approvals": [
                {
                    "id": da.id,
                    "decision": da.decision,
                    "feedback": da.feedback,
                    "decided_at": da.decided_at.isoformat() if da.decided_at else None,
                }
                for da in (task.delivery_approvals or [])
            ],
            "pull_request": {
                "id": task.pull_request.id,
                "pr_number": task.pull_request.pr_number,
                "html_url": task.pull_request.html_url,
                "title": task.pull_request.title,
                "head_branch": task.pull_request.head_branch,
                "base_branch": task.pull_request.base_branch,
                "status": task.pull_request.status,
                "created_at": task.pull_request.created_at.isoformat() if task.pull_request.created_at else None,
            } if task.pull_request else None,
            "is_delivered": task.pull_request is not None,
            "executions": [
                {
                    "id": e.id,
                    "status": e.status,
                    "current_step": e.current_step,
                    "total_steps": e.total_steps,
                    "commit_sha": e.commit_sha,
                    "error_message": e.error_message,
                    "started_at": e.started_at.isoformat(),
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                }
                for e in sorted(task.executions, key=lambda x: x.started_at, reverse=True)
            ],
        }

    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url,
        },
        "pat_status": pat_status,
        "active_chapter": session.active_chapter,
        "selected_repository": {
            "id": repo.id,
            "name": repo.name,
            "full_name": repo.full_name,
            "owner": repo.owner,
            "default_branch": repo.default_branch,
            "html_url": repo.html_url,
            "description": repo.description,
        } if repo else None,
        "current_task": task_detail,
        "execution": execution_detail,
        "available_repositories": available_repositories,
        "available_tasks": available_tasks,
        "can_resume": can_resume,
    }


class SelectRepoSessionRequest(BaseModel):
    repository_id: Optional[str] = None


class SelectTaskSessionRequest(BaseModel):
    task_id: Optional[str] = None


@router.post("/select-repo", summary="Switch Active Repository / Project")
async def select_session_repo(
    payload: SelectRepoSessionRequest,
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Switch active project repository and select its latest task or reset task context."""
    if not auth_context:
        return {"status": "unauthenticated"}
    user, session, _ = auth_context

    if payload.repository_id:
        repo = db.query(Repository).filter(Repository.id == payload.repository_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")
        session.active_repo_id = repo.id
        latest_task = (
            db.query(Task)
            .filter(Task.repository_id == repo.id)
            .order_by(Task.created_at.desc())
            .first()
        )
        session.active_task_id = latest_task.id if latest_task else None
    else:
        # Starting new project / clear repository selection
        session.active_repo_id = None
        session.active_task_id = None

    db.commit()
    return {
        "status": "ok",
        "active_repo_id": session.active_repo_id,
        "active_task_id": session.active_task_id,
    }


@router.post("/select-task", summary="Switch Active Task or Prepare New Task")
async def select_session_task(
    payload: SelectTaskSessionRequest,
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Switch to a specific task or prepare an empty slate for a new task."""
    if not auth_context:
        return {"status": "unauthenticated"}
    user, session, _ = auth_context

    if payload.task_id:
        task = db.query(Task).filter(Task.id == payload.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")
        session.active_task_id = task.id
        session.active_repo_id = task.repository_id
    else:
        # Clear active task for new task creation within active repo
        session.active_task_id = None

    db.commit()
    return {"status": "ok", "active_task_id": session.active_task_id}


@router.post("/new-project", summary="Reset Session for New Project Formulation")
async def start_new_project(
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Reset both active repository and active task for a clean new project."""
    if not auth_context:
        return {"status": "unauthenticated"}
    user, session, _ = auth_context
    session.active_repo_id = None
    session.active_task_id = None
    db.commit()
    return {"status": "ok", "message": "Ready for new project repository"}


@router.post("/new-task", summary="Reset Session for New Task in Current Repository")
async def start_new_task(
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Reset active task while maintaining active repository for new task formulation."""
    if not auth_context:
        return {"status": "unauthenticated"}
    user, session, _ = auth_context
    session.active_task_id = None
    db.commit()
    return {"status": "ok", "message": "Ready for new task in repository"}

