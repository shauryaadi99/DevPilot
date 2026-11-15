"""Workflow and state transition tests for Chapter 4 QA & Code Review."""

import pytest

from app.services.execution_service import (
    ExecutionState,
    build_execution_graph,
    node_delivery,
    node_prepare_dev_retry,
    node_prepare_review_retry,
    node_qa_exhausted,
    node_qa_stalled,
    node_review_blocked,
    node_review_exhausted,
    route_qa,
    route_review,
)


def _base_state() -> ExecutionState:
    return {
        "task_id": "test-task-123",
        "execution_id": "exec-123",
        "repo_clone_url": "https://github.com/test/repo",
        "github_token": None,
        "default_branch": "main",
        "plan": {"summary": "Implement feature"},
        "workspace_path": "/fake/workspace",
        "branch_name": "devpilot/task-123",
        "developer_result": None,
        "commit_sha": "abc1234",
        "status": "QA_TESTING",
        "error_message": None,
        "completed_steps": [],
        "user_requirement": "Test req",
        "acceptance_criteria": ["Crit 1"],
        "qa_cycle": 1,
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


def test_route_qa_passes_advances_to_reviewing():
    state = _base_state()
    state["qa_result"] = {"overall_passed": True, "tests_passed": 5, "tests_failed": 0}
    decision = route_qa(state)
    assert decision == "REVIEWING"


def test_route_qa_failure_triggers_developer_retry():
    state = _base_state()
    state["qa_cycle"] = 1
    state["max_qa_cycles"] = 3
    state["qa_result"] = {
        "overall_passed": False,
        "tests_passed": 2,
        "tests_failed": 1,
        "failure_signature": "sig_cycle_1",
        "actionable_feedback": "Fix line 42 in auth.js",
    }
    state["failure_history"] = ["sig_cycle_1"]

    decision = route_qa(state)
    assert decision == "RETRY_DEVELOPER"

    next_state = node_prepare_dev_retry(state)
    assert next_state["status"] == "EXECUTING"
    assert next_state["feedback_for_developer"] == "Fix line 42 in auth.js"


def test_route_qa_repeated_failure_detects_stall_early():
    state = _base_state()
    state["qa_cycle"] = 2
    state["max_qa_cycles"] = 3
    # Two identical failure signatures in consecutive cycles
    state["failure_history"] = ["sig_repeated_error", "sig_repeated_error"]
    state["qa_result"] = {
        "overall_passed": False,
        "tests_failed": 1,
        "failure_signature": "sig_repeated_error",
    }

    decision = route_qa(state)
    assert decision == "FAILED_STALLED"

    stalled_state = node_qa_stalled(state)
    assert stalled_state["status"] == "FAILED"
    assert "repeated identical failure signature" in stalled_state["error_message"]


def test_route_qa_retry_exhausted():
    state = _base_state()
    state["qa_cycle"] = 3
    state["max_qa_cycles"] = 3
    state["failure_history"] = ["sig_1", "sig_2", "sig_3"]  # Different errors but limit reached
    state["qa_result"] = {"overall_passed": False, "tests_failed": 1}

    decision = route_qa(state)
    assert decision == "FAILED_EXHAUSTED"

    exhausted_state = node_qa_exhausted(state)
    assert exhausted_state["status"] == "FAILED"
    assert "QA retry limit exhausted" in exhausted_state["error_message"]


def test_route_review_approved_transitions_to_delivery():
    state = _base_state()
    state["review_cycle"] = 1
    state["review_result"] = {"outcome": "APPROVED", "quality_score": 9}

    decision = route_review(state)
    assert decision == "AWAITING_DELIVERY"

    delivery_state = node_delivery(state)
    assert delivery_state["status"] == "AWAITING_DELIVERY"


def test_route_review_blocked_fails_immediately():
    state = _base_state()
    state["review_cycle"] = 1
    state["review_result"] = {"outcome": "BLOCKED", "summary": "Critical secret key in code."}

    decision = route_review(state)
    assert decision == "FAILED_BLOCKED"

    blocked_state = node_review_blocked(state)
    assert blocked_state["status"] == "FAILED"
    assert "Code Review BLOCKED" in blocked_state["error_message"]


def test_route_review_changes_requested_triggers_retry():
    state = _base_state()
    state["review_cycle"] = 1
    state["max_review_cycles"] = 2
    state["review_result"] = {
        "outcome": "CHANGES_REQUESTED",
        "summary": "Fix error handling",
        "issues": [{"severity": "MEDIUM", "file_path": "app.js", "description": "Add try/catch", "suggested_fix": "Wrap route"}],
    }

    decision = route_review(state)
    assert decision == "RETRY_DEVELOPER"

    retry_state = node_prepare_review_retry(state)
    assert retry_state["status"] == "EXECUTING"
    assert "Reviewer Changes Requested" in retry_state["feedback_for_developer"]


def test_route_review_retry_exhausted():
    state = _base_state()
    state["review_cycle"] = 2
    state["max_review_cycles"] = 2
    state["review_result"] = {"outcome": "CHANGES_REQUESTED"}

    decision = route_review(state)
    assert decision == "FAILED_EXHAUSTED"

    exhausted_state = node_review_exhausted(state)
    assert exhausted_state["status"] == "FAILED"
    assert "exceeded maximum allowable cycles" in exhausted_state["error_message"]


def test_build_execution_graph_compiles_cleanly():
    graph = build_execution_graph(checkpointer=None)
    assert graph is not None

