"""Unified session and workspace rehydration endpoint.

Provides complete state restoration for browser refresh, independent of whether
an execution is currently running.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Request
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
    if not repo:
        repo = (
            db.query(Repository)
            .filter((Repository.user_id == user.id) | (Repository.user_id.is_(None)))
            .order_by(Repository.updated_at.desc())
            .first()
        )

    # Resolve active task
    task: Optional[Task] = None
    if session.active_task_id:
        task = db.query(Task).filter(Task.id == session.active_task_id).first()
    if not task and repo:
        task = (
            db.query(Task)
            .filter(Task.repository_id == repo.id)
            .order_by(Task.created_at.desc())
            .first()
        )
    if not task:
        task = db.query(Task).order_by(Task.created_at.desc()).first()

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
            }

        task_detail = {
            "id": task.id,
            "title": task.title,
            "requirement": task.user_requirement,
            "status": task.status,
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
        "can_resume": can_resume,
    }

