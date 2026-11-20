"""Execution orchestration service for Chapters 3 & 4.

Uses LangGraph StateGraph with PostgreSQL checkpointing (PostgresSaver) to manage
the autonomous engineering pipeline:
VALIDATING → CLONING → EXECUTING → COMMITTING → QA_TESTING ⇄ EXECUTING → REVIEWING ⇄ EXECUTING → AWAITING_DELIVERY

Includes:
- Distributed execution locking (ExecutionLock) to prevent duplicate parallel runs
- Idempotent step-level execution (skips already applied steps on resume)
- Commit idempotency (reuses existing commit SHA if working tree already committed)
- Persistent workspace preservation (never auto-deletes workspaces on completion)
- QA Engineer Agent execution with bounded retry loops (default max 3)
- Repeated-failure detection (escalates early on identical failure signatures)
- Independent Code Reviewer Agent with outcome evaluation (APPROVED, CHANGES_REQUESTED, BLOCKED)
- Delivery state progression (AWAITING_DELIVERY) ready for Chapter 5 GitHub PR
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, Sequence, TypedDict
import uuid

from sqlalchemy.orm import Session
from git import Repo

from app.agents.code_reviewer import CodeReviewerAgent
from app.agents.developer import DeveloperAgent, DeveloperResult
from app.agents.qa_engineer import QAEngineerAgent
from app.agents.schemas import ArchitectPlanOutput, FileToCreate, FileToModify, ImplementationStep
from app.core.config import get_settings
from app.core.logging import logger
from app.db.models import (
    CodeReviewReport,
    ExecutionLock,
    ExecutionLog,
    FileChange,
    QAReport,
    Task,
    TaskExecution,
)
from app.services.git_service import (
    get_workspace_path,
    prepare_task_workspace,
    stage_and_commit,
)

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.base import BaseCheckpointSaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    BaseCheckpointSaver = object


class AsyncCompatiblePostgresSaver(BaseCheckpointSaver):
    """Wraps PostgresSaver to provide async checkpointer methods on all platforms.

    LangGraph async graphs (ainvoke) call async checkpointer methods (aget_tuple, aput).
    On Windows, psycopg async cannot use ProactorEventLoop; this wrapper executes
    synchronous PostgreSQL operations in an asyncio worker thread, ensuring seamless
    PostgreSQL checkpoint persistence across all OS environments and event loops.
    """

    def __init__(self, sync_saver: Any):
        super().__init__(serde=sync_saver.serde)
        self._sync = sync_saver

    def get_tuple(self, config: Dict[str, Any]) -> Optional[Any]:
        return self._sync.get_tuple(config)

    def list(self, config: Optional[Dict[str, Any]], *, filter: Optional[Dict[str, Any]] = None, before: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> Iterator[Any]:
        return self._sync.list(config, filter=filter, before=before, limit=limit)

    def put(self, config: Dict[str, Any], checkpoint: Any, metadata: Any, new_versions: Any) -> Dict[str, Any]:
        return self._sync.put(config, checkpoint, metadata, new_versions)

    def put_writes(self, config: Dict[str, Any], writes: Sequence[Any], task_id: str, task_path: str = "") -> None:
        return self._sync.put_writes(config, writes, task_id, task_path=task_path)

    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[Any]:
        return await asyncio.to_thread(self.get_tuple, config)

    async def alist(self, config: Optional[Dict[str, Any]], *, filter: Optional[Dict[str, Any]] = None, before: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> AsyncIterator[Any]:
        items = await asyncio.to_thread(lambda: list(self.list(config, filter=filter, before=before, limit=limit)))
        for item in items:
            yield item

    async def aput(self, config: Dict[str, Any], checkpoint: Any, metadata: Any, new_versions: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config: Dict[str, Any], writes: Sequence[Any], task_id: str, task_path: str = "") -> None:
        return await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path=task_path)


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
            return AsyncCompatiblePostgresSaver(saver)
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
        if lock.expires_at > now:
            logger.warning(f"Task {task_id} is locked by execution {lock.execution_id}")
            return None
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
    status: str
    error_message: Optional[str]
    completed_steps: Optional[List[int]]
    user_requirement: Optional[str]
    acceptance_criteria: Optional[List[str]]
    qa_cycle: int
    max_qa_cycles: int
    review_cycle: int
    max_review_cycles: int
    qa_result: Optional[Dict[str, Any]]
    review_result: Optional[Dict[str, Any]]
    failure_history: Optional[List[str]]
    feedback_for_developer: Optional[str]
    qa_reports_data: Optional[List[Dict[str, Any]]]
    review_reports_data: Optional[List[Dict[str, Any]]]


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
    """Run Developer Agent on approved plan with step-level idempotency and optional feedback."""
    task_id = state["task_id"]
    workspace = Path(state["workspace_path"])
    feedback = state.get("feedback_for_developer")
    mode_desc = f"with feedback: {feedback[:80]}..." if feedback else "initial implementation"
    logger.info(f"[{task_id}] Starting Developer Agent execution ({mode_desc})")

    # Write intermediate DB status so polling UI shows EXECUTING immediately
    try:
        from app.db.session import SessionLocal
        with SessionLocal() as _db:
            from app.db.models import Task as _Task, TaskExecution as _TaskExecution
            _exec = _db.query(_TaskExecution).filter(_TaskExecution.id == state["execution_id"]).first()
            _task = _db.query(_Task).filter(_Task.id == task_id).first()
            if _exec:
                _exec.status = "EXECUTING"
                if state.get("workspace_path"):
                    _exec.workspace_path = state["workspace_path"]
                if state.get("branch_name"):
                    _exec.branch_name = state["branch_name"]
            if _task:
                _task.status = "EXECUTING"
            _db.commit()
    except Exception as _e:
        logger.warning(f"[{task_id}] Could not write intermediate EXECUTING status: {_e}")

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

    # If in retry mode with feedback, do not skip steps based on prior cache
    completed_set = set() if feedback else set(state.get("completed_steps") or [])

    agent = DeveloperAgent()
    result = await agent.implement(
        plan=plan,
        workspace_path=workspace,
        completed_step_numbers=completed_set,
        feedback=feedback,
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
        return {
            **state,
            "status": "FAILED",
            "developer_result": result_dict,
            "error_message": result.error_message,
        }
    return {
        **state,
        "status": "COMMITTING",
        "developer_result": result_dict,
        "feedback_for_developer": None,  # Consumed
    }


async def node_commit(state: ExecutionState) -> ExecutionState:
    """Stage all changes and commit to task branch with idempotency check."""
    task_id = state["task_id"]
    workspace = Path(state["workspace_path"])
    logger.info(f"[{task_id}] Committing changes to branch {state['branch_name']}")

    # Write intermediate DB status so polling UI shows COMMITTING immediately
    try:
        from app.db.session import SessionLocal
        with SessionLocal() as _db:
            from app.db.models import Task as _Task, TaskExecution as _TaskExecution
            _exec = _db.query(_TaskExecution).filter(_TaskExecution.id == state["execution_id"]).first()
            _task = _db.query(_Task).filter(_Task.id == task_id).first()
            if _exec:
                _exec.status = "COMMITTING"
            if _task:
                _task.status = "EXECUTING"
            _db.commit()
    except Exception as _e:
        logger.warning(f"[{task_id}] Could not write intermediate COMMITTING status: {_e}")

    def _do_commit():
        repo = Repo(str(workspace))
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
        return {**state, "status": "QA_TESTING", "commit_sha": sha}
    except RuntimeError as exc:
        if "Nothing to commit" in str(exc):
            return {**state, "status": "QA_TESTING", "commit_sha": state.get("commit_sha")}
        return {**state, "status": "FAILED", "error_message": str(exc)}


async def node_qa(state: ExecutionState) -> ExecutionState:
    """Run QA Engineer Agent tests within the isolated workspace."""
    from app.db.session import SessionLocal
    task_id = state["task_id"]
    workspace = Path(state["workspace_path"])
    qa_cycle = (state.get("qa_cycle") or 0) + 1
    logger.info(f"[{task_id}] Starting QA cycle {qa_cycle}")

    # Ensure workspace exists before running QA tests
    if not workspace.exists() or not workspace.is_dir():
        logger.info(f"[{task_id}] Workspace {workspace} missing on disk; preparing workspace before QA...")
        from app.services.git_service import prepare_task_workspace
        workspace = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: prepare_task_workspace(
                clone_url=state["repo_clone_url"],
                task_id=task_id,
                github_token=state.get("github_token"),
                default_branch=state.get("default_branch") or "main",
            )
        )

    # Write intermediate DB status so UI shows QA_TESTING immediately
    try:
        with SessionLocal() as _db:
            from app.db.models import Task as _Task, TaskExecution as _TaskExecution
            _exec = _db.query(_TaskExecution).filter(_TaskExecution.id == state["execution_id"]).first()
            _task = _db.query(_Task).filter(_Task.id == task_id).first()
            if _exec:
                _exec.status = "QA_TESTING"
            if _task:
                _task.status = "QA_TESTING"
            _db.commit()
    except Exception as _e:
        logger.warning(f"[{task_id}] Could not write intermediate QA_TESTING status: {_e}")

    # Reconstruct plan using explicit field mapping (same pattern as node_execute)
    plan_data = state.get("plan")
    plan_obj = None
    if plan_data:
        try:
            plan_obj = ArchitectPlanOutput(
                summary=plan_data.get("summary", ""),
                repository_understanding=plan_data.get("repository_understanding", ""),
                confirmed_observations=plan_data.get("confirmed_observations", []),
                files_to_create=[FileToCreate(**f) for f in plan_data.get("files_to_create", [])],
                files_to_modify=[FileToModify(**f) for f in plan_data.get("files_to_modify", [])],
                implementation_steps=[ImplementationStep(**s) for s in plan_data.get("implementation_steps", [])],
                dependencies=plan_data.get("dependencies", []),
                testing_strategy=plan_data.get("testing_strategy", {}),
                risks_and_assumptions=plan_data.get("risks_and_assumptions", []),
            )
        except Exception as exc:
            logger.warning(f"[{task_id}] Plan reconstruction in node_qa failed: {exc}; proceeding without plan hints.")

    qa_agent = QAEngineerAgent()
    prev_sig = (state.get("failure_history") or [])[-1] if state.get("failure_history") else None

    qa_output = await qa_agent.execute_and_evaluate(
        workspace_path=workspace,
        acceptance_criteria=state.get("acceptance_criteria") or [],
        plan=plan_obj,
        previous_failure_signature=prev_sig,
    )

    qa_dict = qa_output.model_dump()
    qa_reports_data = list(state.get("qa_reports_data") or [])
    qa_reports_data.append({**qa_dict, "cycle_number": qa_cycle})

    new_failure_history = list(state.get("failure_history") or [])
    if qa_output.failure_signature:
        new_failure_history.append(qa_output.failure_signature)

    return {
        **state,
        "qa_cycle": qa_cycle,
        "qa_result": qa_dict,
        "qa_reports_data": qa_reports_data,
        "failure_history": new_failure_history,
        "status": "QA_EVALUATING",
    }


def route_qa(state: ExecutionState) -> str:
    """Route based on QA results: PASS -> Review; FAIL -> Check stall / limit -> Retry or Fail."""
    qa_res = state.get("qa_result") or {}
    if qa_res.get("overall_passed"):
        logger.info(f"[{state['task_id']}] QA passed on cycle {state.get('qa_cycle')}. Advancing to code review.")
        return "REVIEWING"

    # Repeated failure stall detection: if the last 2 signatures match and are not None
    history = state.get("failure_history") or []
    if len(history) >= 2 and history[-1] == history[-2] and history[-1] is not None:
        logger.warning(f"[{state['task_id']}] Repeated failure stall detected (signature: {history[-1]}). Halting early.")
        return "FAILED_STALLED"

    # Retry limit check
    current_cycle = state.get("qa_cycle", 1)
    max_cycles = state.get("max_qa_cycles", 3)
    if current_cycle >= max_cycles:
        logger.warning(f"[{state['task_id']}] QA retry limit exhausted ({current_cycle}/{max_cycles}).")
        return "FAILED_EXHAUSTED"

    logger.info(f"[{state['task_id']}] QA failed. Looping back to Developer Agent (cycle {current_cycle + 1}/{max_cycles}).")
    return "RETRY_DEVELOPER"


def node_qa_stalled(state: ExecutionState) -> ExecutionState:
    sig = (state.get("failure_history") or ["unknown"])[-1]
    return {
        **state,
        "status": "FAILED",
        "error_message": f"Execution halted: repeated identical failure signature '{sig}' detected across consecutive cycles without progress.",
    }


def node_qa_exhausted(state: ExecutionState) -> ExecutionState:
    cycles = state.get("qa_cycle", 3)
    return {
        **state,
        "status": "FAILED",
        "error_message": f"Execution halted: QA retry limit exhausted after {cycles} cycles without passing all tests.",
    }


def node_prepare_dev_retry(state: ExecutionState) -> ExecutionState:
    qa_res = state.get("qa_result") or {}
    feedback = qa_res.get("actionable_feedback") or qa_res.get("failure_summary") or "Fix failing tests."

    # Append concrete failing test details so Developer Agent sees the exact file, line, and code frame
    failing_items = qa_res.get("test_details") or []
    if failing_items:
        details_lines = [f"- {t.get('test_name', '')}: {t.get('error_message', '')}" for t in failing_items[:10]]
        feedback += "\n\nExact Failing Test Traces:\n" + "\n".join(details_lines)

    return {
        **state,
        "status": "EXECUTING",
        "feedback_for_developer": feedback,
    }


async def node_review(state: ExecutionState) -> ExecutionState:
    """Run Code Reviewer Agent on Git diff against base branch."""
    from app.db.session import SessionLocal
    task_id = state["task_id"]
    workspace = Path(state["workspace_path"])
    review_cycle = (state.get("review_cycle") or 0) + 1
    logger.info(f"[{task_id}] Starting Code Review cycle {review_cycle}")

    # Ensure workspace exists before running Code Review
    if not workspace.exists() or not workspace.is_dir():
        logger.info(f"[{task_id}] Workspace {workspace} missing on disk; preparing workspace before Code Review...")
        from app.services.git_service import prepare_task_workspace
        workspace = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: prepare_task_workspace(
                clone_url=state["repo_clone_url"],
                task_id=task_id,
                github_token=state.get("github_token"),
                default_branch=state.get("default_branch") or "main",
            )
        )

    # Write intermediate DB status so UI shows REVIEWING immediately
    try:
        with SessionLocal() as _db:
            from app.db.models import Task as _Task, TaskExecution as _TaskExecution
            _exec = _db.query(_TaskExecution).filter(_TaskExecution.id == state["execution_id"]).first()
            _task = _db.query(_Task).filter(_Task.id == task_id).first()
            if _exec:
                _exec.status = "REVIEWING"
            if _task:
                _task.status = "REVIEWING"
            _db.commit()
    except Exception as _e:
        logger.warning(f"[{task_id}] Could not write intermediate REVIEWING status: {_e}")

    reviewer = CodeReviewerAgent()
    plan_dict = state.get("plan") or {}
    plan_summary = plan_dict.get("summary", "")
    qa_summary = (state.get("qa_result") or {}).get("failure_summary") or "All automated tests verified and passing."

    review_output = await reviewer.review(
        workspace_path=workspace,
        task_requirement=state.get("user_requirement") or "Implement task cleanly.",
        plan_summary=plan_summary,
        qa_summary=qa_summary,
    )

    review_dict = review_output.model_dump()
    review_reports_data = list(state.get("review_reports_data") or [])
    review_reports_data.append({**review_dict, "cycle_number": review_cycle})

    return {
        **state,
        "review_cycle": review_cycle,
        "review_result": review_dict,
        "review_reports_data": review_reports_data,
        "status": "REVIEW_EVALUATING",
    }


def route_review(state: ExecutionState) -> str:
    """Route based on Code Review outcome: APPROVED -> Delivery; BLOCKED -> Fail; CHANGES -> Retry."""
    review_res = state.get("review_result") or {}
    outcome = review_res.get("outcome", "APPROVED").upper()

    if outcome == "APPROVED":
        logger.info(f"[{state['task_id']}] Code Review APPROVED. Task ready for delivery.")
        return "AWAITING_DELIVERY"

    if outcome == "BLOCKED":
        logger.warning(f"[{state['task_id']}] Code Review BLOCKED due to critical issues.")
        return "FAILED_BLOCKED"

    # CHANGES_REQUESTED
    current_cycle = state.get("review_cycle", 1)
    max_cycles = state.get("max_review_cycles", 2)
    if current_cycle >= max_cycles:
        logger.warning(f"[{state['task_id']}] Review change requests retry limit exhausted ({current_cycle}/{max_cycles}).")
        return "FAILED_EXHAUSTED"

    logger.info(f"[{state['task_id']}] Changes requested by reviewer. Looping back to Developer Agent.")
    return "RETRY_DEVELOPER"


def node_review_blocked(state: ExecutionState) -> ExecutionState:
    review_res = state.get("review_result") or {}
    return {
        **state,
        "status": "FAILED",
        "error_message": f"Execution halted: Code Review BLOCKED. {review_res.get('summary', 'Critical issues detected.')}",
    }


def node_review_exhausted(state: ExecutionState) -> ExecutionState:
    cycles = state.get("review_cycle", 2)
    return {
        **state,
        "status": "FAILED",
        "error_message": f"Execution halted: Review change requests exceeded maximum allowable cycles ({cycles}).",
    }


def node_prepare_review_retry(state: ExecutionState) -> ExecutionState:
    review_res = state.get("review_result") or {}
    issues_str = "\n".join(
        f"- [{i.get('severity')}] {i.get('file_path')}: {i.get('description')} (Fix: {i.get('suggested_fix')})"
        for i in review_res.get("issues", [])
    )
    feedback = f"Reviewer Changes Requested: {review_res.get('summary')}\nIssues:\n{issues_str}"
    return {
        **state,
        "status": "EXECUTING",
        "feedback_for_developer": feedback,
    }


def node_delivery(state: ExecutionState) -> ExecutionState:
    """Final delivery node marking task verified and awaiting Chapter 5 GitHub PR."""
    logger.info(f"[{state['task_id']}] All Chapter 4 checks passed. Task transitioning to AWAITING_DELIVERY.")
    return {**state, "status": "AWAITING_DELIVERY"}


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
    graph.add_node("QA_TESTING", node_qa)
    graph.add_node("QA_FAIL_STALLED", node_qa_stalled)
    graph.add_node("QA_FAIL_EXHAUSTED", node_qa_exhausted)
    graph.add_node("QA_RETRY_DEV", node_prepare_dev_retry)
    graph.add_node("REVIEWING", node_review)
    graph.add_node("REVIEW_FAIL_BLOCKED", node_review_blocked)
    graph.add_node("REVIEW_FAIL_EXHAUSTED", node_review_exhausted)
    graph.add_node("REVIEW_RETRY_DEV", node_prepare_review_retry)
    graph.add_node("DELIVERY", node_delivery)

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
        "QA_TESTING": "QA_TESTING",
        "FAILED": END,
    })
    graph.add_conditional_edges("QA_TESTING", route_qa, {
        "REVIEWING": "REVIEWING",
        "FAILED_STALLED": "QA_FAIL_STALLED",
        "FAILED_EXHAUSTED": "QA_FAIL_EXHAUSTED",
        "RETRY_DEVELOPER": "QA_RETRY_DEV",
    })
    graph.add_edge("QA_FAIL_STALLED", END)
    graph.add_edge("QA_FAIL_EXHAUSTED", END)
    graph.add_edge("QA_RETRY_DEV", "EXECUTING")

    graph.add_conditional_edges("REVIEWING", route_review, {
        "AWAITING_DELIVERY": "DELIVERY",
        "FAILED_BLOCKED": "REVIEW_FAIL_BLOCKED",
        "FAILED_EXHAUSTED": "REVIEW_FAIL_EXHAUSTED",
        "RETRY_DEVELOPER": "REVIEW_RETRY_DEV",
    })
    graph.add_edge("REVIEW_FAIL_BLOCKED", END)
    graph.add_edge("REVIEW_FAIL_EXHAUSTED", END)
    graph.add_edge("REVIEW_RETRY_DEV", "EXECUTING")
    graph.add_edge("DELIVERY", END)

    if checkpointer:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


# ── Execution Service ────────────────────────────────────────────────────────


class ExecutionService:
    """Orchestrates plan execution, QA, review, checkpointing, and DB persistence."""

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

        criteria: List[str] = []
        if task.requirement_analysis and task.requirement_analysis.acceptance_criteria:
            criteria = list(task.requirement_analysis.acceptance_criteria)

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
            "user_requirement": task.user_requirement,
            "acceptance_criteria": criteria,
            "qa_cycle": 0,
            "max_qa_cycles": 3,
            "review_cycle": 0,
            "max_review_cycles": 2,
            "qa_result": None,
            "review_result": None,
            "failure_history": [],
            "feedback_for_developer": None,
            "qa_reports_data": [],
            "review_reports_data": [],
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
            err_text = str(exc).strip() or exc.__class__.__name__
            logger.exception(f"Execution engine error for task {task.id}: {err_text}")
            final_state = {
                **initial_state,
                "status": "FAILED",
                "error_message": f"Execution engine error: {err_text}",
            }
        finally:
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

        completed_steps = [
            log.step_number
            for log in execution.logs
            if log.agent == "DeveloperAgent"
            and log.level == "INFO"
            and log.step_number is not None
            and log.step_number > 0
            and (execution.total_steps is None or log.step_number <= execution.total_steps)
        ]

        plan_data = None
        if task.implementation_plan:
            plan_data = task.implementation_plan.__dict__.copy()
            plan_data.pop("_sa_instance_state", None)

        criteria: List[str] = []
        if task.requirement_analysis and task.requirement_analysis.acceptance_criteria:
            criteria = list(task.requirement_analysis.acceptance_criteria)

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
            "user_requirement": task.user_requirement,
            "acceptance_criteria": criteria,
            "qa_cycle": 0 if (len(execution.qa_reports) >= 3 or execution.status == "FAILED") else len(execution.qa_reports),
            "max_qa_cycles": 3,
            "review_cycle": 0 if (len(execution.review_reports) >= 2 or execution.status == "FAILED") else len(execution.review_reports),
            "max_review_cycles": 2,
            "qa_result": None,
            "review_result": None,
            "failure_history": [] if (len(execution.qa_reports) >= 3 or execution.status == "FAILED") else [r.failure_signature for r in execution.qa_reports if r.failure_signature],
            "feedback_for_developer": None,
            "qa_reports_data": [],
            "review_reports_data": [],
        }

        try:
            if self._graph:
                config = {"configurable": {"thread_id": task.id}}
                final_state = await self._graph.ainvoke(resume_state, config=config)
            else:
                final_state = await self._sequential_fallback(resume_state)
        except Exception as exc:
            err_text = str(exc).strip() or exc.__class__.__name__
            logger.exception(f"Resume failed for task {task.id}: {err_text}")
            final_state = {
                **resume_state,
                "status": "FAILED",
                "error_message": f"Resume error: {err_text}",
            }
        finally:
            release_execution_lock(db, task.id, lock_token)

        self._persist_results(db, task, execution, final_state)

    async def run_qa_pipeline(
        self,
        db: Session,
        task: Task,
        execution: TaskExecution,
        github_token: Optional[str] = None,
    ) -> None:
        """Start QA pipeline directly from QA_TESTING node — bypasses VALIDATING/CLONING/EXECUTING.

        Called by the /run-qa endpoint when a task is AWAITING_QA but QA has not yet run
        (i.e. the inline pipeline completed COMMITTING but was interrupted before QA, or the
        user manually triggers QA for the first time on a task with a committed workspace).
        """
        lock_token = acquire_execution_lock(db, task.id, execution.id)
        if not lock_token:
            raise RuntimeError("Task execution is already running on another worker.")

        plan_data = None
        if task.implementation_plan:
            plan_data = task.implementation_plan.__dict__.copy()
            plan_data.pop("_sa_instance_state", None)

        criteria: List[str] = []
        if task.requirement_analysis and task.requirement_analysis.acceptance_criteria:
            criteria = list(task.requirement_analysis.acceptance_criteria)

        qa_state: ExecutionState = {
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
            "status": "QA_TESTING",         # <-- enter at QA node directly
            "error_message": None,
            "completed_steps": [],
            "user_requirement": task.user_requirement,
            "acceptance_criteria": criteria,
            "qa_cycle": 0 if (len(execution.qa_reports) >= 3 or execution.status == "FAILED") else len(execution.qa_reports),
            "max_qa_cycles": 3,
            "review_cycle": 0 if (len(execution.review_reports) >= 2 or execution.status == "FAILED") else len(execution.review_reports),
            "max_review_cycles": 2,
            "qa_result": None,
            "review_result": None,
            "failure_history": [] if (len(execution.qa_reports) >= 3 or execution.status == "FAILED") else [r.failure_signature for r in execution.qa_reports if r.failure_signature],
            "feedback_for_developer": None,
            "qa_reports_data": [],
            "review_reports_data": [],
        }

        # We cannot use the compiled LangGraph with a checkpoint thread that starts mid-graph,
        # so we drive the QA→Review→Delivery sub-graph manually.
        try:
            state = await node_qa(qa_state)
            route = route_qa(state)
            if route == "FAILED_STALLED":
                state = node_qa_stalled(state)
            elif route == "FAILED_EXHAUSTED":
                state = node_qa_exhausted(state)
            elif route == "RETRY_DEVELOPER":
                # QA failed on first explicit trigger — persist feedback and stop
                state = node_prepare_dev_retry(state)
                # Keep status as AWAITING_QA so the user can retry
                state = {**state, "status": "AWAITING_QA"}
            else:
                # QA passed → run code review
                state = await node_review(state)
                route_rev = route_review(state)
                if route_rev == "AWAITING_DELIVERY":
                    state = node_delivery(state)
                elif route_rev == "FAILED_BLOCKED":
                    state = node_review_blocked(state)
                elif route_rev == "FAILED_EXHAUSTED":
                    state = node_review_exhausted(state)
                else:
                    # CHANGES_REQUESTED — execute Developer Agent to implement requested review fixes
                    logger.info(f"[{task.id}] Review requested changes. Executing Developer Agent with review feedback...")
                    state = node_prepare_review_retry(state)
                    state = await node_execute(state)
                    state = node_commit(state)
                    state = await node_qa(state)
                    state = await node_review(state)
                    route_rev2 = route_review(state)
                    if route_rev2 == "AWAITING_DELIVERY":
                        state = node_delivery(state)
                    elif route_rev2 == "FAILED_BLOCKED":
                        state = node_review_blocked(state)
                    else:
                        state = node_review_exhausted(state)
        except Exception as exc:
            err_text = str(exc).strip() or exc.__class__.__name__
            logger.exception(f"QA pipeline error for task {task.id}: {err_text}")
            state = {
                **qa_state,
                "status": "FAILED",
                "error_message": f"QA pipeline error: {err_text}",
            }
        finally:
            release_execution_lock(db, task.id, lock_token)

        self._persist_results(db, task, execution, state)

    def _persist_results(
        self,
        db: Session,
        task: Task,
        execution: TaskExecution,
        state: ExecutionState,
    ) -> None:
        """Write execution, QA, and Code Review outcomes to DB models."""
        status = state["status"]
        execution.status = status
        execution.branch_name = state.get("branch_name")
        workspace = state.get("workspace_path")
        execution.workspace_path = workspace
        execution.commit_sha = state.get("commit_sha")
        execution.error_message = state.get("error_message")
        execution.completed_at = datetime.now(timezone.utc)

        task.status = status

        dev_result = state.get("developer_result") or {}
        step_results = dev_result.get("step_results", [])
        if dev_result.get("steps_total"):
            execution.total_steps = dev_result.get("steps_total", 0)
        if dev_result.get("steps_completed"):
            execution.current_step = dev_result.get("steps_completed", 0)

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

        # Persist QA reports
        for qr in state.get("qa_reports_data") or []:
            qa_model = QAReport(
                task_id=task.id,
                execution_id=execution.id,
                cycle_number=qr.get("cycle_number", 1),
                overall_passed=qr.get("overall_passed", False),
                commands_executed=qr.get("commands_executed", []),
                tests_passed=qr.get("tests_passed", 0),
                tests_failed=qr.get("tests_failed", 0),
                tests_skipped=qr.get("tests_skipped", 0),
                exit_codes=qr.get("exit_codes", []),
                logs=qr.get("logs", ""),
                failure_summary=qr.get("failure_summary"),
                failure_signature=qr.get("failure_signature"),
                test_details=[t.model_dump() if hasattr(t, "model_dump") else t for t in qr.get("test_details", [])],
                acceptance_criteria_results=[c.model_dump() if hasattr(c, "model_dump") else c for c in qr.get("acceptance_criteria_results", [])],
                actionable_feedback=qr.get("actionable_feedback"),
            )
            db.add(qa_model)
            qa_log_msg = f"QA Cycle {qr.get('cycle_number')}: {'PASSED' if qr.get('overall_passed') else 'FAILED'}. Passed: {qr.get('tests_passed')}, Failed: {qr.get('tests_failed')}."
            db.add(ExecutionLog(
                execution_id=execution.id,
                step_number=len(step_results) + qr.get("cycle_number", 1),
                level="INFO" if qr.get("overall_passed") else "WARNING",
                agent="QAEngineerAgent",
                message=qa_log_msg,
            ))

        # Persist Code Review reports
        for rr in state.get("review_reports_data") or []:
            rev_model = CodeReviewReport(
                task_id=task.id,
                execution_id=execution.id,
                cycle_number=rr.get("cycle_number", 1),
                outcome=rr.get("outcome", "APPROVED"),
                summary=rr.get("summary", ""),
                correctness_assessment=rr.get("correctness_assessment", ""),
                security_assessment=rr.get("security_assessment", ""),
                quality_score=rr.get("quality_score", 8),
                issues=[i.model_dump() if hasattr(i, "model_dump") else i for i in rr.get("issues", [])],
                approval_recommendation=rr.get("approval_recommendation", ""),
            )
            db.add(rev_model)
            rev_log_msg = f"Code Review Cycle {rr.get('cycle_number')}: Outcome={rr.get('outcome')}, Score={rr.get('quality_score')}/10. {rr.get('summary')}"
            db.add(ExecutionLog(
                execution_id=execution.id,
                step_number=len(step_results) + 10 + rr.get("cycle_number", 1),
                level="INFO" if rr.get("outcome") == "APPROVED" else "WARNING",
                agent="CodeReviewerAgent",
                message=rev_log_msg,
            ))

        final_msg = f"Execution {status}." + (
            f" Commit: {state['commit_sha']}" if state.get("commit_sha") else ""
        ) + (
            f" Error: {state['error_message']}" if state.get("error_message") else ""
        )
        db.add(ExecutionLog(
            execution_id=execution.id,
            step_number=len(step_results) + 50,
            level="INFO" if status in ("AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY") else "ERROR",
            agent="ExecutionService",
            message=final_msg,
        ))
        db.commit()

    async def _sequential_fallback(self, state: ExecutionState) -> ExecutionState:
        """Sequential fallback pipeline when LangGraph is not available."""
        state = node_validate(state)
        if state["status"] == "FAILED":
            return state
        state = await node_clone(state)
        if state["status"] == "FAILED":
            return state
        state = await node_execute(state)
        if state["status"] == "FAILED":
            return state
        state = await node_commit(state)
        if state["status"] == "FAILED":
            return state
        state = await node_qa(state)
        if route_qa(state) != "REVIEWING":
            return state
        state = await node_review(state)
        if route_review(state) == "AWAITING_DELIVERY":
            return node_delivery(state)
        return state
