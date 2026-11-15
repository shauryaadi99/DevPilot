"""Execution orchestration service for Chapter 3.

Uses LangGraph StateGraph with PostgreSQL checkpointing (PostgresSaver) to manage
the autonomous execution pipeline:
VALIDATING → CLONING → EXECUTING → COMMITTING → AWAITING_QA / FAILED / CANCELLED

Includes:
- Distributed execution locking (ExecutionLock) to prevent duplicate parallel runs
- Idempotent step-level execution (skips already applied steps on resume)
- Commit idempotency (reuses existing commit SHA if working tree already committed)
- Persistent workspace preservation (never auto-deletes workspaces on completion)
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypedDict
import uuid

from sqlalchemy.orm import Session
from git import Repo

from app.agents.developer import DeveloperAgent, DeveloperResult
from app.agents.schemas import ArchitectPlanOutput, FileToCreate, FileToModify, ImplementationStep
from app.core.config import get_settings
from app.core.logging import logger
from app.db.models import FileChange, ExecutionLog, ExecutionLock, Task, TaskExecution
from app.services.git_service import (
    prepare_task_workspace,
    stage_and_commit,
    get_workspace_path,
)

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


def _get_postgres_saver():
    """Return LangGraph PostgresSaver checkpointer if PostgreSQL is configured."""
    settings = get_settings()
    if "postgres" in settings.DATABASE_URL:
        try:
            import psycopg
            from langgraph.checkpoint.postgres import PostgresSaver

            conn_uri = settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
            conn = psycopg.connect(conn_uri, autocommit=True)
            saver = PostgresSaver(conn)
            saver.setup()
            return saver
        except Exception as e:
            logger.warning(f"Could not initialize LangGraph PostgresSaver: {e}")
    return None


get_checkpointer = _get_postgres_saver


# ── Execution Locking Helpers ────────────────────────────────────────────────


def acquire_execution_lock(db: Session, task_id: str, execution_id: str) -> Optional[str]:
    """Acquire execution lock. Returns lock_token on success, None if actively locked."""
    now = datetime.now(timezone.utc)
    lock = db.query(ExecutionLock).filter(ExecutionLock.task_id == task_id).first()

    if lock:
        # Check if lock is still active and fresh (< 60s)
        if lock.expires_at > now:
            logger.warning(f"Task {task_id} is locked by execution {lock.execution_id}")
            return None
        # Stale/crashed lock — reclaim it
        logger.info(f"Reclaiming stale lock on task {task_id}")
        token = str(uuid.uuid4())
        lock.execution_id = execution_id
        lock.lock_token = token
        lock.acquired_at = now
        lock.heartbeat_at = now
        lock.expires_at = now + timedelta(seconds=60)
    else:
        token = str(uuid.uuid4())
        lock = ExecutionLock(
            task_id=task_id,
            execution_id=execution_id,
            lock_token=token,
            acquired_at=now,
            heartbeat_at=now,
            expires_at=now + timedelta(seconds=60),
        )
        db.add(lock)

    db.commit()
    return token


def release_execution_lock(db: Session, task_id: str, lock_token: Optional[str] = None) -> None:
    """Release execution lock for a task."""
    query = db.query(ExecutionLock).filter(ExecutionLock.task_id == task_id)
    if lock_token:
        query = query.filter(ExecutionLock.lock_token == lock_token)
    query.delete()
    db.commit()


# ── LangGraph State ──────────────────────────────────────────────────────────


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
    completed_steps: Optional[List[int]]


# ── Node Implementations ─────────────────────────────────────────────────────


def node_validate(state: ExecutionState) -> ExecutionState:
    """Validate execution pre-conditions."""
    logger.info(f"[{state['task_id']}] Validating execution preconditions")
    if not state.get("plan"):
        return {**state, "status": "FAILED", "error_message": "No plan provided to execution engine."}
    return {**state, "status": "CLONING"}


async def node_clone(state: ExecutionState) -> ExecutionState:
    """Prepare persistent workspace (idempotent clone) and ensure task branch."""
    task_id = state["task_id"]
    logger.info(f"[{task_id}] Preparing persistent workspace")
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
    """Run Developer Agent on approved plan with step-level idempotency."""
    task_id = state["task_id"]
    workspace = Path(state["workspace_path"])
    logger.info(f"[{task_id}] Starting Developer Agent execution")

    plan_dict = state["plan"]
    try:
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

    completed_set = set(state.get("completed_steps") or [])

    agent = DeveloperAgent()
    result = await agent.implement(
        plan=plan,
        workspace_path=workspace,
        completed_step_numbers=completed_set,
    )

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
    """Stage all changes and commit to task branch with idempotency check."""
    task_id = state["task_id"]
    workspace = Path(state["workspace_path"])
    logger.info(f"[{task_id}] Committing changes to branch {state['branch_name']}")

    def _do_commit():
        repo = Repo(str(workspace))
        # If already committed in a prior run and working tree is clean:
        if not repo.is_dirty(untracked_files=True):
            if repo.head.is_valid():
                commit_msg = repo.head.commit.message
                if f"implement task {task_id}" in commit_msg:
                    logger.info(f"Reusing existing commit {repo.head.commit.hexsha[:7]}")
                    return repo.head.commit.hexsha
            return None
        return stage_and_commit(workspace, f"feat(devpilot): implement task {task_id}")

    try:
        sha = await asyncio.get_event_loop().run_in_executor(None, _do_commit)
        return {**state, "status": "AWAITING_QA", "commit_sha": sha}
    except RuntimeError as exc:
        if "Nothing to commit" in str(exc):
            return {**state, "status": "AWAITING_QA", "commit_sha": None}
        return {**state, "status": "FAILED", "error_message": str(exc)}


def _route(state: ExecutionState) -> str:
    return state["status"]


# ── Graph Assembly ───────────────────────────────────────────────────────────


def build_execution_graph(checkpointer=None):
    """Build and compile the LangGraph execution StateGraph with checkpointer."""
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

    if checkpointer:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


# ── Execution Service ────────────────────────────────────────────────────────


class ExecutionService:
    """Orchestrates plan execution, checkpointing, and DB persistence."""

    def __init__(self):
        self._checkpointer = _get_postgres_saver()
        if LANGGRAPH_AVAILABLE:
            self._graph = build_execution_graph(checkpointer=self._checkpointer)
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
        """Run execution pipeline with locking and checkpoint recovery."""
        # 1. Acquire execution lock
        lock_token = acquire_execution_lock(db, task.id, execution.id)
        if not lock_token:
            execution.status = "FAILED"
            execution.error_message = "Task execution is already running on another worker."
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        plan_data = None
        if task.implementation_plan:
            plan_data = task.implementation_plan.__dict__.copy()
            plan_data.pop("_sa_instance_state", None)

        initial_state: ExecutionState = {
            "task_id": task.id,
            "execution_id": execution.id,
            "repo_clone_url": task.repository.html_url,
            "github_token": github_token,
            "default_branch": task.repository.default_branch,
            "plan": plan_data,
            "workspace_path": None,
            "branch_name": None,
            "developer_result": None,
            "commit_sha": None,
            "status": "VALIDATING",
            "error_message": None,
            "completed_steps": [],
        }

        execution.status = "CLONING"
        task.status = "EXECUTING"
        db.commit()

        try:
            if self._graph:
                config = {"configurable": {"thread_id": task.id}}
                final_state = await self._graph.ainvoke(initial_state, config=config)
            else:
                final_state = await self._sequential_fallback(initial_state)
        except Exception as exc:
            logger.error(f"Execution engine error for task {task.id}: {exc}")
            final_state = {
                **initial_state,
                "status": "FAILED",
                "error_message": f"Execution engine crash: {exc}",
            }
        finally:
            # Always release execution lock
            release_execution_lock(db, task.id, lock_token)

        self._persist_results(db, task, execution, final_state)

    async def resume_plan(
        self,
        db: Session,
        task: Task,
        execution: TaskExecution,
        github_token: Optional[str] = None,
    ) -> None:
        """Resume an interrupted execution without repeating completed steps."""
        lock_token = acquire_execution_lock(db, task.id, execution.id)
        if not lock_token:
            raise RuntimeError("Task execution is already running on another worker.")

        # Determine already completed steps from FileChange / logs
        completed_step_numbers = [
            fc.execution_id for fc in execution.file_changes
        ]
        completed_steps = [
            log.step_number for log in execution.logs if log.agent == "DeveloperAgent" and log.level == "INFO"
        ]

        plan_data = None
        if task.implementation_plan:
            plan_data = task.implementation_plan.__dict__.copy()
            plan_data.pop("_sa_instance_state", None)

        resume_state: ExecutionState = {
            "task_id": task.id,
            "execution_id": execution.id,
            "repo_clone_url": task.repository.html_url,
            "github_token": github_token,
            "default_branch": task.repository.default_branch,
            "plan": plan_data,
            "workspace_path": execution.workspace_path or str(get_workspace_path(task.id)),
            "branch_name": execution.branch_name or f"devpilot/task-{task.id}",
            "developer_result": None,
            "commit_sha": execution.commit_sha,
            "status": "EXECUTING",
            "error_message": None,
            "completed_steps": completed_steps,
        }

        try:
            if self._graph:
                config = {"configurable": {"thread_id": task.id}}
                final_state = await self._graph.ainvoke(resume_state, config=config)
            else:
                final_state = await self._sequential_fallback(resume_state)
        except Exception as exc:
            final_state = {
                **resume_state,
                "status": "FAILED",
                "error_message": f"Resume failed: {exc}",
            }
        finally:
            release_execution_lock(db, task.id, lock_token)

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

        task.status = status  # AWAITING_QA, FAILED, CANCELLED

        dev_result = state.get("developer_result") or {}
        step_results = dev_result.get("step_results", [])
        execution.total_steps = dev_result.get("steps_total", 0)
        execution.current_step = dev_result.get("steps_completed", 0)

        # Existing file change paths to avoid duplicating on resume
        existing_paths = {fc.file_path for fc in execution.file_changes}

        for sr in step_results:
            if sr["file_path"] not in existing_paths and sr.get("change_type") != "PRESERVED":
                fc = FileChange(
                    execution_id=execution.id,
                    file_path=sr["file_path"],
                    change_type=sr["change_type"],
                    diff_summary=sr.get("diff_summary", ""),
                    lines_added=sr.get("lines_added", 0),
                    lines_removed=sr.get("lines_removed", 0),
                )
                db.add(fc)
                existing_paths.add(sr["file_path"])

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
