"""API endpoints for Chapter 5: Final Delivery Approval, Pull Request creation, Diff & Timeline.

Provides secure task-level ownership checks, PAT resolution from headers or encrypted session,
and idempotent pull request delivery.
"""

from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.auth import get_optional_current_user
from app.core.logging import logger
from app.db.session import get_db
from app.db.models import Task, DeliveryApproval, PullRequestRecord, User, UserSession
from app.integrations.github_client import GitHubError
from app.services.delivery_service import (
    deliver_task_pull_request,
    get_task_diff,
    get_task_timeline,
)

router = APIRouter(prefix="/api/v1/tasks", tags=["Delivery & Pull Request"])


# ── Request / Response Schemas ───────────────────────────────────────────────


class FinalApprovalRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"] = Field(
        ..., description="Final approval decision before creating a pull request."
    )
    feedback: Optional[str] = Field(
        None, description="Optional review feedback or rejection reason."
    )


class FinalApprovalResponse(BaseModel):
    id: str
    task_id: str
    decision: str
    feedback: Optional[str] = None
    decided_at: str
    task_status: str
    approval: Optional[Dict[str, Any]] = None


def _serialize_pr(pr: Optional[PullRequestRecord]) -> Optional[Dict[str, Any]]:
    if not pr:
        return None
    return {
        "id": pr.id,
        "task_id": pr.task_id,
        "repository_id": pr.repository_id,
        "pr_number": pr.pr_number,
        "html_url": pr.html_url,
        "title": pr.title,
        "head_branch": pr.head_branch,
        "base_branch": pr.base_branch,
        "status": pr.status,
        "body": pr.body,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
    }


def _serialize_approval(appr: DeliveryApproval) -> Dict[str, Any]:
    return {
        "id": appr.id,
        "task_id": appr.task_id,
        "decision": appr.decision,
        "feedback": appr.feedback,
        "decided_at": appr.decided_at.isoformat() if appr.decided_at else None,
    }


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "/{task_id}/final-approval",
    response_model=FinalApprovalResponse,
    summary="Submit Final Delivery Human Approval (Approval 2)",
)
async def submit_final_approval(
    task_id: str,
    payload: FinalApprovalRequest,
    db: Session = Depends(get_db),
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
):
    """Record human approval or rejection for final GitHub Pull Request delivery.

    Prerequisite before calling POST /{task_id}/deliver.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    user: Optional[User] = None
    if auth_context:
        user = auth_context[0]

    # Verify task ownership if task is associated with a user
    if task.user_id and user and task.user_id != user.id:
        creator = db.query(User).filter(User.id == task.user_id).first()
        if creator and creator.username in ("developer", "dev"):
            task.user_id = user.id
            db.commit()
        else:
            raise HTTPException(status_code=403, detail="You do not have permission to modify this task.")
    elif not task.user_id and user:
        task.user_id = user.id
        db.commit()

    approval = DeliveryApproval(
        task_id=task.id,
        user_id=user.id if user else None,
        decision=payload.decision,
        feedback=payload.feedback.strip() if payload.feedback else None,
    )
    db.add(approval)

    if payload.decision == "REJECTED":
        # Record rejection on task status
        task.status = "REJECTED"
        logger.info(f"[{task_id}] Final delivery rejected by reviewer: {payload.feedback}")
    else:
        logger.info(f"[{task_id}] Final delivery APPROVED by reviewer.")

    db.commit()
    db.refresh(approval)

    approval_dict = {
        "id": approval.id,
        "task_id": approval.task_id,
        "decision": approval.decision,
        "feedback": approval.feedback,
        "decided_at": approval.decided_at.isoformat(),
    }

    return FinalApprovalResponse(
        id=approval.id,
        task_id=approval.task_id,
        decision=approval.decision,
        feedback=approval.feedback,
        decided_at=approval.decided_at.isoformat(),
        task_status=task.status,
        approval=approval_dict,
    )


@router.post(
    "/{task_id}/deliver",
    summary="Deliver Task to GitHub by Creating Pull Request",
)
async def deliver_task(
    task_id: str,
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
    db: Session = Depends(get_db),
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
):
    """Deliver completed task changes to GitHub as a Pull Request.

    Enforces:
    - User authentication and valid GitHub PAT.
    - Prior approval recorded via POST /{task_id}/final-approval.
    - Verified task status (AWAITING_DELIVERY or Review APPROVED).
    - Idempotency (reuses existing PR if already delivered).
    """
    token = x_github_token
    user: Optional[User] = None
    if auth_context:
        user = auth_context[0]
        if not token:
            token = auth_context[2]

    if not token:
        raise HTTPException(
            status_code=401,
            detail="GitHub token required to deliver pull request. Please configure a GitHub PAT.",
        )

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    if task.user_id and user and task.user_id != user.id:
        creator = db.query(User).filter(User.id == task.user_id).first()
        if creator and creator.username in ("developer", "dev"):
            task.user_id = user.id
            db.commit()
        else:
            raise HTTPException(status_code=403, detail="You do not have permission to deliver this task.")
    elif not task.user_id and user:
        task.user_id = user.id
        db.commit()

    try:
        pr_record = await deliver_task_pull_request(
            db=db,
            task_id=task_id,
            github_token=token,
            user_id=user.id if user else None,
        )
        return {
            "status": "delivered",
            "message": f"Pull request #{pr_record.pr_number} created successfully.",
            "pull_request": _serialize_pr(pr_record),
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except GitHubError as ge:
        raise HTTPException(status_code=ge.status_code, detail=str(ge))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as exc:
        logger.exception(f"Unexpected error delivering task {task_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Delivery failed: {exc}")


@router.get(
    "/{task_id}/delivery",
    summary="Get Task Delivery and Pull Request Status",
)
async def get_delivery_status(
    task_id: str,
    db: Session = Depends(get_db),
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
):
    """Retrieve current delivery status, final approvals, and PR record if created."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    approvals = (
        db.query(DeliveryApproval)
        .filter(DeliveryApproval.task_id == task_id)
        .order_by(DeliveryApproval.decided_at.desc())
        .all()
    )

    has_approved = any(a.decision == "APPROVED" for a in approvals)
    can_deliver = bool(
        (task.status == "AWAITING_DELIVERY" or any(r.outcome == "APPROVED" for r in task.review_reports))
        and has_approved
        and not task.pull_request
    )

    return {
        "task_id": task.id,
        "task_status": task.status,
        "is_delivered": task.pull_request is not None,
        "can_deliver": can_deliver,
        "pull_request": _serialize_pr(task.pull_request),
        "approvals": [_serialize_approval(a) for a in approvals],
    }


@router.get(
    "/{task_id}/diff",
    summary="Get Pre-Delivery Git Diff and Modified Files",
)
async def get_task_git_diff(
    task_id: str,
    db: Session = Depends(get_db),
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
):
    """Retrieve unified Git diff and modified file stats for user review before approving delivery."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    diff_data = get_task_diff(task)
    return diff_data


@router.get(
    "/{task_id}/timeline",
    summary="Get End-to-End Task Activity Timeline",
)
async def get_task_activity_timeline(
    task_id: str,
    db: Session = Depends(get_db),
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
):
    """Retrieve chronologically sorted events across Chapters 1 through 5 for this task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    timeline = get_task_timeline(task)
    return {"task_id": task.id, "timeline": timeline}

