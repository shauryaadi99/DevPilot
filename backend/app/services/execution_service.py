"""Execution orchestration service for Chapter 3.

Uses LangGraph StateGraph to manage the autonomous execution pipeline:
VALIDATING → CLONING → EXECUTING → COMMITTING → COMPLETED / FAILED / CANCELLED

Sandbox: Docker container with --network none, --memory 512m, --cpus 0.5.
Fallback: subprocess with stripped env, timeout, and workspace restriction.
"""

import asyncio
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy.orm import Session

from app.agents.developer import DeveloperAgent, DeveloperResult
from app.agents.schemas import ArchitectPlanOutput, FileToCreate, FileToModify, ImplementationStep
from app.core.logging import logger
from app.db.models import FileChange, ExecutionLog, Task, TaskExecution
from app.services.git_service import (
    prepare_task_workspace,
    create_task_branch,
    stage_and_commit,
    get_workspace_path,
)

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


# ── LangGraph State ────────────────────────────────────────────────────────

class ExecutionState(TypedDict):
    task_id: str
    execution_id: str
    repo_clone_url: str
    github_token: Optional[str]
    default_branch: str
    plan: Optional[Dict[str, Any]]
    workspace_path: Optional[str]
    branch_name: Optional[str]
    developer_result: Optional[Dict[str, Any]]
    commit_sha: Optional[str]
    status: str  # VALIDATING, CLONING, EXECUTING, COMMITTING, AWAITING_QA, FAILED, CANCELLED
    error_message: Optional[str]


# ── Node implementations ───────────────────────────────────────────────────

def node_validate(state: ExecutionState) -> ExecutionState:
    """Validate execution pre-conditions (plan, approval already verified by API layer)."""
    logger.info(f"[{state['task_id']}] Validating execution preconditions")
    if not state.get("plan"):
        return {**state, "status": "FAILED", "error_message": "No plan provided to execution engine."}
    return {**state, "status": "CLONING"}


async def node_clone(state: ExecutionState) -> ExecutionState:
    """Prepare persistent workspace (idempotent clone) and ensure task branch."""
    task_id = state["task_id"]
    logger.info(f"[{task_id}] Preparing workspace")
    try:
        workspace = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: prepare_task_workspace(
                clone_url=state["repo_clone_url"],
                task_id=task_id,
                github_token=state.get("github_token"),
                default_branch=state["default_branch"],
            )
        )
        branch_name = f"devpilot/task-{task_id}"
        return {**state, "workspace_path": str(workspace), "branch_name": branch_name, "status": "EXECUTING"}
    except RuntimeError as exc:
        return {**state, "status": "FAILED", "error_message": str(exc)}


async def node_execute(state: ExecutionState) -> ExecutionState:
    """Run Developer Agent on approved plan inside cloned workspace."""
    task_id = state["task_id"]
    workspace = Path(state["workspace_path"])
    logger.info(f"[{task_id}] Starting Developer Agent execution")

    plan_dict = state["plan"]
    try:
        # Reconstruct ArchitectPlanOutput from stored dict
        plan = ArchitectPlanOutput(
            summary=plan_dict.get("summary", ""),
            repository_understanding=plan_dict.get("repository_understanding", ""),
            confirmed_observations=plan_dict.get("confirmed_observations", []),
            files_to_create=[FileToCreate(**f) for f in plan_dict.get("files_to_create", [])],
            files_to_modify=[FileToModify(**f) for f in plan_dict.get("files_to_modify", [])],
            implementation_steps=[ImplementationStep(**s) for s in plan_dict.get("implementation_steps", [])],
            dependencies=plan_dict.get("dependencies", []),
            testing_strategy=plan_dict.get("testing_strategy", {}),
            risks_and_assumptions=plan_dict.get("risks_and_assumptions", []),
        )
    except Exception as exc:
        return {**state, "status": "FAILED", "error_message": f"Plan reconstruction failed: {exc}"}

    agent = DeveloperAgent()
    result = await agent.implement(plan=plan, workspace_path=workspace)

    result_dict = {
        "success": result.success,
        "steps_completed": result.steps_completed,
        "steps_total": result.steps_total,
        "error_message": result.error_message,
        "step_results": [
            {
                "step_number": sr.step_number,
                "step_title": sr.step_title,
                "file_path": sr.file_path,
                "change_type": sr.change_type,
                "success": sr.success,
                "explanation": sr.explanation,
                "error": sr.error,
                "lines_added": sr.lines_added,
                "lines_removed": sr.lines_removed,
                "diff_summary": sr.diff_summary,
            }
            for sr in result.step_results
        ],
    }

    if not result.success:
        return {**state, "status": "FAILED", "developer_result": result_dict,
                "error_message": result.error_message}
    return {**state, "status": "COMMITTING", "developer_result": result_dict}


async def node_commit(state: ExecutionState) -> ExecutionState:
    """Stage all changes and commit to task branch."""
    task_id = state["task_id"]
    workspace = Path(state["workspace_path"])
    logger.info(f"[{task_id}] Committing changes to branch {state['branch_name']}")
    try:
        sha = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: stage_and_commit(workspace, f"feat(devpilot): implement task {task_id}")
        )
        return {**state, "status": "AWAITING_QA", "commit_sha": sha}
    except RuntimeError as exc:
        # "Nothing to commit" is not fatal — treat as success without commit
        if "Nothing to commit" in str(exc):
            logger.warning(f"[{task_id}] No changes detected after execution.")
            return {**state, "status": "AWAITING_QA", "commit_sha": None}
        return {**state, "status": "FAILED", "error_message": str(exc)}


def _route(state: ExecutionState) -> str:
    """Conditional routing based on current status."""
    return state["status"]


# ── Graph assembly ─────────────────────────────────────────────────────────

def build_execution_graph():
    """Build and compile the LangGraph execution StateGraph."""
    graph = StateGraph(ExecutionState)
    graph.add_node("VALIDATING", node_validate)
    graph.add_node("CLONING", node_clone)
    graph.add_node("EXECUTING", node_execute)
    graph.add_node("COMMITTING", node_commit)

    graph.set_entry_point("VALIDATING")

    graph.add_conditional_edges("VALIDATING", _route, {
        "CLONING": "CLONING",
        "FAILED": END,
    })
    graph.add_conditional_edges("CLONING", _route, {
        "EXECUTING": "EXECUTING",
        "FAILED": END,
    })
    graph.add_conditional_edges("EXECUTING", _route, {
        "COMMITTING": "COMMITTING",
        "FAILED": END,
    })
    graph.add_conditional_edges("COMMITTING", _route, {
        "AWAITING_QA": END,
        "FAILED": END,
    })

    return graph.compile()


# ── Execution service ──────────────────────────────────────────────────────

class ExecutionService:
    """Orchestrates plan execution and persists results to DB."""

    def __init__(self):
        if LANGGRAPH_AVAILABLE:
            self._graph = build_execution_graph()
        else:
            self._graph = None
            logger.warning("LangGraph not available; sequential fallback will be used.")

    async def execute_plan(
        self,
        db: Session,
        task: Task,
        execution: TaskExecution,
        github_token: Optional[str] = None,
    ) -> None:
        """Run the execution pipeline and update DB records throughout.

        Args:
            db: Active SQLAlchemy session.
            task: Task ORM instance (must have APPROVED status).
            execution: TaskExecution ORM instance (status=PENDING).
            github_token: GitHub PAT for cloning (never stored in DB).
        """
        plan_data = None
        if task.implementation_plan:
            plan_data = task.implementation_plan.__dict__.copy()
            plan_data.pop("_sa_instance_state", None)

        initial_state: ExecutionState = {
            "task_id": task.id,
            "execution_id": execution.id,
            "repo_clone_url": task.repository.html_url.replace(
                "https://github.com/", "https://github.com/"  # keep HTTPS
            ),
            "github_token": github_token,
            "default_branch": task.repository.default_branch,
            "plan": plan_data,
            "workspace_path": None,
            "branch_name": None,
            "developer_result": None,
            "commit_sha": None,
            "status": "VALIDATING",
            "error_message": None,
        }

        # Persist CLONING status
        execution.status = "CLONING"
        task.status = "EXECUTING"
        db.commit()

        try:
            if self._graph:
                final_state = await self._graph.ainvoke(initial_state)
            else:
                # Minimal sequential fallback (no LangGraph)
                final_state = await self._sequential_fallback(initial_state)
        except Exception as exc:
            logger.error(f"Execution engine error for task {task.id}: {exc}")
            final_state = {
                **initial_state,
                "status": "FAILED",
                "error_message": f"Execution engine crash: {exc}",
            }

        # Persist final state to DB
        self._persist_results(db, task, execution, final_state)

    def _persist_results(
        self,
        db: Session,
        task: Task,
        execution: TaskExecution,
        state: ExecutionState,
    ) -> None:
        """Write execution outcomes to DB models. Workspace is NEVER deleted here."""
        status = state["status"]
        execution.status = status
        execution.branch_name = state.get("branch_name")
        workspace = state.get("workspace_path")
        execution.workspace_path = workspace
        execution.commit_sha = state.get("commit_sha")
        execution.error_message = state.get("error_message")
        execution.completed_at = datetime.now(timezone.utc)

        # Map internal AWAITING_QA -> task status (FAILED/CANCELLED pass through)
        task.status = status  # AWAITING_QA, FAILED, CANCELLED

        dev_result = state.get("developer_result") or {}
        step_results = dev_result.get("step_results", [])
        execution.total_steps = dev_result.get("steps_total", 0)
        execution.current_step = dev_result.get("steps_completed", 0)

        # Persist FileChange records
        for sr in step_results:
            fc = FileChange(
                execution_id=execution.id,
                file_path=sr["file_path"],
                change_type=sr["change_type"],
                diff_summary=sr.get("diff_summary", ""),
                lines_added=sr.get("lines_added", 0),
                lines_removed=sr.get("lines_removed", 0),
            )
            db.add(fc)

            level = "INFO" if sr["success"] else "ERROR"
            msg = sr.get("explanation") or sr.get("error") or f"Step {sr['step_number']}"
            log = ExecutionLog(
                execution_id=execution.id,
                step_number=sr["step_number"],
                level=level,
                agent="DeveloperAgent",
                message=f"[{sr['step_title']}] {sr['file_path']}: {msg}",
            )
            db.add(log)

        # Final status log
        final_msg = f"Execution {status}." + (
            f" Commit: {state['commit_sha']}" if state.get("commit_sha") else ""
        ) + (
            f" Error: {state['error_message']}" if state.get("error_message") else ""
        )
        db.add(ExecutionLog(
            execution_id=execution.id,
            step_number=len(step_results) + 1,
            level="INFO" if status == "AWAITING_QA" else "ERROR",
            agent="ExecutionService",
            message=final_msg,
        ))
        db.commit()
        # Workspace is preserved — cleanup only on explicit task closure via POST /close

    async def _sequential_fallback(self, state: ExecutionState) -> ExecutionState:
        """Minimal sequential pipeline when LangGraph is not available."""
        state = node_validate(state)
        if state["status"] == "FAILED":
            return state
        state = await node_clone(state)
        if state["status"] == "FAILED":
            return state
        state = await node_execute(state)
        if state["status"] == "FAILED":
            return state
        return await node_commit(state)

