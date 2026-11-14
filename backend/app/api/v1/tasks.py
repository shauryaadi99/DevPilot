"""Tasks API router.

Handles requirement submission, repository inspection, Product Analyst analysis,
Architect planning, persistent human approval workflows, and Chapter 3 autonomous execution.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    Repository,
    Task,
    InspectionResult,
    RequirementAnalysis,
    ImplementationPlan,
    PlanApproval,
    TaskExecution,
)
from app.integrations.github_client import GitHubClient, GitHubError
from app.services.inspection_service import InspectionService
from app.agents.product_analyst import ProductAnalystAgent
from app.agents.architect import ArchitectAgent
from app.agents.schemas import (
    ProductAnalystOutput,
    ArchitectPlanOutput,
    FileToCreate,
    FileToModify,
    ApiContractChange,
    ImplementationStep,
)
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks & Planning"])


class CreateTaskRequest(BaseModel):
    repository_id: str
    title: str
    requirement: str


class ApprovalRequest(BaseModel):
    decision: str  # APPROVED, REJECTED, CHANGES_REQUESTED
    feedback: Optional[str] = None


@router.post("", summary="Create a New Task")
def create_task(payload: CreateTaskRequest, db: Session = Depends(get_db)):
    """Submit a natural-language engineering requirement for a connected repository."""
    repo = db.query(Repository).filter(Repository.id == payload.repository_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Target repository not found.")

    task = Task(
        repository_id=repo.id,
        title=payload.title.strip(),
        user_requirement=payload.requirement.strip(),
        status="PENDING",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", summary="List All Tasks")
def list_tasks(limit: int = 20, db: Session = Depends(get_db)):
    """List recent engineering tasks."""
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(limit).all()
    return tasks


@router.get("/{task_id}", summary="Get Full Task Details")
def get_task(task_id: str, db: Session = Depends(get_db)):
    """Retrieve full task context including inspection findings, requirements, plan, and approval."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    return {
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
        "approvals": [
            {
                "id": a.id,
                "decision": a.decision,
                "feedback": a.feedback,
                "decided_at": a.decided_at.isoformat(),
            }
            for a in task.approvals
        ],
    }


@router.post("/{task_id}/pipeline", summary="Execute Full Intelligence & Planning Pipeline")
async def run_task_pipeline(
    task_id: str,
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
    db: Session = Depends(get_db),
):
    """Run the complete Chapter 2 pipeline:

    1. Inspect codebase.
    2. Run Product Analyst Agent.
    3. Run Architect Agent.
    4. Save plan and transition to AWAITING_APPROVAL.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    repo = task.repository
    github_client = GitHubClient(token=x_github_token)

    try:
        # Step 1: Repository Inspection
        task.status = "INSPECTING"
        db.commit()

        inspection_service = InspectionService(github_client=github_client)
        inspection_data = await inspection_service.inspect_repository(
            owner=repo.owner,
            repo=repo.name,
            default_branch=repo.default_branch,
        )

        # Upsert InspectionResult
        if task.inspection:
            db.delete(task.inspection)
            db.flush()

        insp_record = InspectionResult(
            task_id=task.id,
            tree_summary=inspection_data.get("tree_summary", {}),
            detected_languages=inspection_data.get("detected_languages", []),
            detected_frameworks=inspection_data.get("detected_frameworks", []),
            detected_entrypoints=inspection_data.get("detected_entrypoints", []),
            manifests_summary=inspection_data.get("manifests_summary", {}),
            confirmed_facts=inspection_data.get("confirmed_facts", []),
            unknowns=inspection_data.get("unknowns", []),
        )
        db.add(insp_record)

        # Step 2: Product Analyst Agent
        task.status = "ANALYZING"
        db.commit()

        analyst_agent = ProductAnalystAgent()
        analysis_output = await analyst_agent.analyze(
            requirement=task.user_requirement,
            repo_context=inspection_data,
        )

        if task.requirement_analysis:
            db.delete(task.requirement_analysis)
            db.flush()

        req_record = RequirementAnalysis(
            task_id=task.id,
            requirement_summary=analysis_output.requirement_summary,
            functional_requirements=analysis_output.functional_requirements,
            nonfunctional_requirements=analysis_output.nonfunctional_requirements,
            acceptance_criteria=analysis_output.acceptance_criteria,
            ambiguities=analysis_output.ambiguities,
            clarification_questions=analysis_output.clarification_questions,
            raw_llm_response=analysis_output.model_dump(),
        )
        db.add(req_record)

        # Step 3: Architect Agent
        task.status = "PLANNING"
        db.commit()

        architect_agent = ArchitectAgent()
        plan_output = await architect_agent.plan(
            analysis=analysis_output,
            repo_inspection=inspection_data,
        )

        if task.implementation_plan:
            db.delete(task.implementation_plan)
            db.flush()

        plan_record = ImplementationPlan(
            task_id=task.id,
            summary=plan_output.summary,
            repository_understanding=plan_output.repository_understanding,
            confirmed_observations=plan_output.confirmed_observations,
            files_to_create=[f.model_dump() for f in plan_output.files_to_create],
            files_to_modify=[f.model_dump() for f in plan_output.files_to_modify],
            api_contract_changes=[a.model_dump() for a in plan_output.api_contract_changes],
            implementation_steps=[s.model_dump() for s in plan_output.implementation_steps],
            dependencies=plan_output.dependencies,
            testing_strategy=plan_output.testing_strategy,
            risks_and_assumptions=plan_output.risks_and_assumptions,
            raw_llm_response=plan_output.model_dump(),
        )
        db.add(plan_record)

        # Final transition to AWAITING_APPROVAL
        task.status = "AWAITING_APPROVAL"
        db.commit()

        return get_task(task_id=task.id, db=db)

    except GitHubError as e:
        task.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=e.status_code, detail=f"GitHub Error: {str(e)}")
    except Exception as e:
        logger.error(f"Pipeline execution failure on task {task_id}: {e}", exc_info=True)
        task.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Planning pipeline failed: {str(e)}")


@router.post("/{task_id}/approval", summary="Record Human Plan Review Decision")
async def record_plan_approval(
    task_id: str,
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
):
    """Record human approval, rejection, or change request for the implementation plan.

    If CHANGES_REQUESTED is submitted with feedback, automatically executes a closed-loop
    re-planning cycle with Product Analyst and Architect agents to revise the plan.

    STRICT SAFETY RULE: Approving a plan must NOT trigger code modifications in this chapter.
    """
    decision = payload.decision.upper()
    if decision not in ("APPROVED", "REJECTED", "CHANGES_REQUESTED"):
        raise HTTPException(
            status_code=400,
            detail="Invalid decision. Must be APPROVED, REJECTED, or CHANGES_REQUESTED.",
        )

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    if not task.implementation_plan:
        raise HTTPException(status_code=400, detail="Cannot review a task without an implementation plan.")

    # Record persistent approval row
    approval = PlanApproval(
        task_id=task.id,
        plan_id=task.implementation_plan.id,
        decision=decision,
        feedback=payload.feedback,
    )
    db.add(approval)
    task.status = decision
    db.commit()
    db.refresh(approval)

    # If CHANGES_REQUESTED, trigger closed-loop plan revision
    if decision == "CHANGES_REQUESTED" and payload.feedback and payload.feedback.strip():
        logger.info(f"Closed-loop re-planning triggered for task {task.id} with feedback: {payload.feedback}")

        inspection_data = {
            "tree_summary": task.inspection.tree_summary if task.inspection else {},
            "detected_languages": task.inspection.detected_languages if task.inspection else [],
            "detected_frameworks": task.inspection.detected_frameworks if task.inspection else [],
            "detected_entrypoints": task.inspection.detected_entrypoints if task.inspection else [],
            "manifests_summary": task.inspection.manifests_summary if task.inspection else {},
            "confirmed_facts": task.inspection.confirmed_facts if task.inspection else [],
            "unknowns": task.inspection.unknowns if task.inspection else [],
        }

        # 1. Revise Requirement Analysis with feedback
        analyst_agent = ProductAnalystAgent()
        prev_analysis = None
        if task.requirement_analysis:
            prev_analysis = ProductAnalystOutput(
                requirement_summary=task.requirement_analysis.requirement_summary,
                functional_requirements=task.requirement_analysis.functional_requirements,
                nonfunctional_requirements=task.requirement_analysis.nonfunctional_requirements,
                acceptance_criteria=task.requirement_analysis.acceptance_criteria,
                ambiguities=task.requirement_analysis.ambiguities,
                clarification_questions=task.requirement_analysis.clarification_questions,
            )

        revised_analysis = await analyst_agent.analyze(
            requirement=task.user_requirement,
            repo_context=inspection_data,
            user_feedback=payload.feedback,
            previous_analysis=prev_analysis,
        )

        if task.requirement_analysis:
            task.requirement_analysis.requirement_summary = revised_analysis.requirement_summary
            task.requirement_analysis.functional_requirements = revised_analysis.functional_requirements
            task.requirement_analysis.nonfunctional_requirements = revised_analysis.nonfunctional_requirements
            task.requirement_analysis.acceptance_criteria = revised_analysis.acceptance_criteria
            task.requirement_analysis.ambiguities = revised_analysis.ambiguities
            task.requirement_analysis.clarification_questions = revised_analysis.clarification_questions
            task.requirement_analysis.raw_llm_response = revised_analysis.model_dump()

        # 2. Revise Architect Plan with feedback
        architect_agent = ArchitectAgent()
        prev_plan = None
        if task.implementation_plan:
            prev_plan = ArchitectPlanOutput(
                summary=task.implementation_plan.summary,
                repository_understanding=task.implementation_plan.repository_understanding,
                confirmed_observations=task.implementation_plan.confirmed_observations,
                files_to_create=[FileToCreate(**f) for f in task.implementation_plan.files_to_create],
                files_to_modify=[FileToModify(**f) for f in task.implementation_plan.files_to_modify],
                api_contract_changes=[ApiContractChange(**a) for a in task.implementation_plan.api_contract_changes],
                implementation_steps=[ImplementationStep(**s) for s in task.implementation_plan.implementation_steps],
                dependencies=task.implementation_plan.dependencies,
                testing_strategy=task.implementation_plan.testing_strategy,
                risks_and_assumptions=task.implementation_plan.risks_and_assumptions,
            )

        revised_plan = await architect_agent.plan(
            analysis=revised_analysis,
            repo_inspection=inspection_data,
            user_feedback=payload.feedback,
            previous_plan=prev_plan,
        )

        # Update ImplementationPlan in database
        task.implementation_plan.summary = revised_plan.summary
        task.implementation_plan.repository_understanding = revised_plan.repository_understanding
        task.implementation_plan.confirmed_observations = revised_plan.confirmed_observations
        task.implementation_plan.files_to_create = [f.model_dump() for f in revised_plan.files_to_create]
        task.implementation_plan.files_to_modify = [f.model_dump() for f in revised_plan.files_to_modify]
        task.implementation_plan.api_contract_changes = [a.model_dump() for a in revised_plan.api_contract_changes]
        task.implementation_plan.implementation_steps = [s.model_dump() for s in revised_plan.implementation_steps]
        task.implementation_plan.dependencies = revised_plan.dependencies
        task.implementation_plan.testing_strategy = revised_plan.testing_strategy
        task.implementation_plan.risks_and_assumptions = revised_plan.risks_and_assumptions
        task.implementation_plan.raw_llm_response = revised_plan.model_dump()

        # Transition task back to AWAITING_APPROVAL with revised plan
        task.status = "AWAITING_APPROVAL"
        db.commit()

    return {
        "status": "recorded",
        "task_id": task.id,
        "decision": decision,
        "message": (
            "Plan approved! Chapter 2 requirement satisfied. "
            "No autonomous code modification will be executed until Chapter 3 engine is activated."
            if decision == "APPROVED"
            else "Plan revised to incorporate review feedback! Task is ready for re-review."
            if decision == "CHANGES_REQUESTED"
            else f"Plan decision recorded as {decision}."
        ),
        "approval": {
            "id": approval.id,
            "decision": approval.decision,
            "feedback": approval.feedback,
            "decided_at": approval.decided_at.isoformat(),
        },
        "task": get_task(task_id=task.id, db=db),
    }



# ── Chapter 3: Autonomous Execution Endpoints ──────────────────────────────

from app.services.execution_service import ExecutionService


class ExecuteRequest(BaseModel):
    github_token: Optional[str] = None  # PAT for private repos; never stored


@router.post("/{task_id}/execute", summary="Execute Approved Plan (Chapter 3)")
async def execute_plan(
    task_id: str,
    payload: ExecuteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start autonomous execution of an APPROVED implementation plan.

    Backend enforces:
    - Task exists with APPROVED status
    - ImplementationPlan exists
    - Latest PlanApproval.decision == APPROVED
    - No execution already running
    Returns 403 if any check fails.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    # Approval gate enforcement (backend, not frontend-only)
    if task.status not in ("APPROVED",):
        raise HTTPException(
            status_code=403,
            detail=f"Task is not in APPROVED state (current: {task.status}). Cannot execute.",
        )

    if not task.implementation_plan:
        raise HTTPException(status_code=403, detail="No implementation plan found for this task.")

    latest_approval = (
        db.query(PlanApproval)
        .filter(PlanApproval.task_id == task_id)
        .order_by(PlanApproval.decided_at.desc())
        .first()
    )
    if not latest_approval or latest_approval.decision != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail="No APPROVED plan approval record found. Human review required.",
        )

    # Prevent duplicate executions
    running = (
        db.query(TaskExecution)
        .filter(TaskExecution.task_id == task_id, TaskExecution.status.in_(["CLONING", "EXECUTING", "COMMITTING"]))
        .first()
    )
    if running:
        raise HTTPException(status_code=409, detail=f"Execution {running.id} is already running.")

    # Create execution record
    execution = TaskExecution(
        task_id=task.id,
        status="PENDING",
        total_steps=len(task.implementation_plan.implementation_steps),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    # Launch async background execution
    service = ExecutionService()
    background_tasks.add_task(
        service.execute_plan,
        db=db,
        task=task,
        execution=execution,
        github_token=payload.github_token,
    )

    return {
        "status": "started",
        "execution_id": execution.id,
        "task_id": task_id,
        "message": "Execution started in background. Poll GET /{task_id}/execution for status.",
    }


@router.get("/{task_id}/execution", summary="Get Execution Status (Chapter 3)")
def get_execution_status(task_id: str, db: Session = Depends(get_db)):
    """Poll execution progress, file changes, and logs for a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    execution = (
        db.query(TaskExecution)
        .filter(TaskExecution.task_id == task_id)
        .order_by(TaskExecution.started_at.desc())
        .first()
    )
    if not execution:
        raise HTTPException(status_code=404, detail="No execution found for this task.")

    return {
        "execution_id": execution.id,
        "task_id": task_id,
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


@router.post("/{task_id}/cancel", summary="Cancel Running Execution (Chapter 3)")
def cancel_execution(task_id: str, db: Session = Depends(get_db)):
    """Mark a running execution as CANCELLED. Cleans up workspace."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    execution = (
        db.query(TaskExecution)
        .filter(TaskExecution.task_id == task_id)
        .order_by(TaskExecution.started_at.desc())
        .first()
    )
    if not execution:
        raise HTTPException(status_code=404, detail="No execution found.")

    if execution.status in ("COMPLETED", "FAILED", "CANCELLED"):
        raise HTTPException(
            status_code=409,
            detail=f"Execution already in terminal state: {execution.status}",
        )

    from datetime import datetime, timezone
    execution.status = "CANCELLED"
    execution.completed_at = datetime.now(timezone.utc)
    task.status = "CANCELLED"
    db.commit()

    # Best-effort workspace cleanup
    try:
        from app.services.git_service import cleanup_workspace
        cleanup_workspace(task_id)
    except Exception:
        pass

    return {
        "status": "cancelled",
        "execution_id": execution.id,
        "task_id": task_id,
        "message": "Execution marked as CANCELLED. Workspace cleaned up.",
    }
