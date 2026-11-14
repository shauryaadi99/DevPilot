"""Integration tests for Task creation, planning pipeline, and human approval flow."""

from unittest.mock import patch, MagicMock
from app.db.models import Repository, Task, ImplementationPlan


def test_task_creation_and_approval_flow(client):
    """Verify task creation, planning persistence, and approval decision."""
    # 1. Select repository
    repo_payload = {
        "github_id": 99991234,
        "name": "sample-repo",
        "full_name": "bit/sample-repo",
        "owner": "bit",
        "default_branch": "main",
        "is_private": False,
        "html_url": "https://github.com/bit/sample-repo",
        "description": "Sample test repo",
    }
    repo_res = client.post("/api/v1/github/select", json=repo_payload)
    assert repo_res.status_code == 200
    repo_data = repo_res.json()["repository"]
    repo_id = repo_data["id"]

    # 2. Create task
    task_payload = {
        "repository_id": repo_id,
        "title": "Add health check endpoint",
        "requirement": "Add a /health endpoint that reports service uptime.",
    }
    task_res = client.post("/api/v1/tasks", json=task_payload)
    assert task_res.status_code == 200
    task = task_res.json()
    task_id = task["id"]
    assert task["status"] == "PENDING"

    # 3. Mock pipeline execution
    mock_inspection = {
        "tree_summary": {"total_files": 5, "key_paths": ["app/main.py"]},
        "detected_languages": ["Python"],
        "detected_frameworks": ["FastAPI"],
        "detected_entrypoints": ["app/main.py"],
        "manifests_summary": {},
        "confirmed_facts": ["FastAPI installed"],
        "unknowns": [],
    }

    from app.agents.schemas import ProductAnalystOutput, ArchitectPlanOutput, FileToModify, ImplementationStep
    mock_analysis = ProductAnalystOutput(
        requirement_summary="Add /health endpoint",
        functional_requirements=["Endpoint responds with 200 OK"],
        nonfunctional_requirements=["Fast response < 50ms"],
        acceptance_criteria=["GET /health returns HTTP 200"],
        ambiguities=[],
        clarification_questions=[],
    )
    mock_plan = ArchitectPlanOutput(
        summary="Add health endpoint in main.py",
        repository_understanding="FastAPI app",
        confirmed_observations=["FastAPI installed"],
        files_to_create=[],
        files_to_modify=[FileToModify(path="app/main.py", reason="Add endpoint", changes_summary="Add GET /health")],
        api_contract_changes=[],
        implementation_steps=[ImplementationStep(step_number=1, title="Add route", description="Implement endpoint", affected_files=["app/main.py"])],
        dependencies=[],
        testing_strategy={"unit_tests": ["Test /health"]},
        risks_and_assumptions=[],
    )

    with patch("app.services.inspection_service.InspectionService.inspect_repository", return_value=mock_inspection), \
         patch("app.agents.product_analyst.ProductAnalystAgent.analyze", return_value=mock_analysis), \
         patch("app.agents.architect.ArchitectAgent.plan", return_value=mock_plan):

        pipeline_res = client.post(f"/api/v1/tasks/{task_id}/pipeline", headers={"X-GitHub-Token": "mock_token"})
        assert pipeline_res.status_code == 200
        pipeline_data = pipeline_res.json()

        assert pipeline_data["status"] == "AWAITING_APPROVAL"
        assert pipeline_data["inspection"] is not None
        assert pipeline_data["requirement_analysis"] is not None
        assert pipeline_data["implementation_plan"] is not None
        assert len(pipeline_data["implementation_plan"]["implementation_steps"]) == 1

    # 4. Human Approval Decision
    approval_res = client.post(
        f"/api/v1/tasks/{task_id}/approval",
        json={"decision": "APPROVED", "feedback": "Looks great, proceed."},
    )
    assert approval_res.status_code == 200
    approval_data = approval_res.json()
    assert approval_data["status"] == "recorded"
    assert approval_data["decision"] == "APPROVED"
    assert "No autonomous code modification" in approval_data["message"]

    # Verify task state in database
    detail_res = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["status"] == "APPROVED"
    assert len(detail["approvals"]) == 1
    assert detail["approvals"][0]["decision"] == "APPROVED"


def test_changes_requested_closed_loop_replanning(client):
    """Verify that requesting changes triggers closed-loop re-planning and updates the plan."""
    from app.agents.schemas import (
        ProductAnalystOutput,
        ArchitectPlanOutput,
        FileToCreate,
        FileToModify,
        ImplementationStep,
    )

    # 1. Setup Repo and Task
    repo_payload = {
        "github_id": 99995678,
        "name": "auth-service",
        "full_name": "bit/auth-service",
        "owner": "bit",
        "default_branch": "main",
        "is_private": False,
        "html_url": "https://github.com/bit/auth-service",
    }
    repo_res = client.post("/api/v1/github/select", json=repo_payload)
    repo_id = repo_res.json()["repository"]["id"]

    task_payload = {
        "repository_id": repo_id,
        "title": "Add Password Reset",
        "requirement": "Add password reset flow.",
    }
    task_res = client.post("/api/v1/tasks", json=task_payload)
    task_id = task_res.json()["id"]

    mock_inspection = {
        "tree_summary": {"total_files": 3, "key_paths": ["app/auth.py"]},
        "detected_languages": ["Python"],
        "detected_frameworks": ["FastAPI"],
        "detected_entrypoints": ["app/auth.py"],
        "manifests_summary": {},
        "confirmed_facts": [],
        "unknowns": [],
    }

    initial_analysis = ProductAnalystOutput(
        requirement_summary="Initial password reset analysis",
        functional_requirements=["Send email reset link"],
        nonfunctional_requirements=[],
        acceptance_criteria=["Email received"],
        ambiguities=[],
        clarification_questions=[],
    )
    initial_plan = ArchitectPlanOutput(
        summary="Initial Plan: Store token in memory",
        repository_understanding="FastAPI auth service",
        confirmed_observations=[],
        files_to_create=[],
        files_to_modify=[FileToModify(path="app/auth.py", reason="Add endpoint", changes_summary="Add reset")],
        api_contract_changes=[],
        implementation_steps=[ImplementationStep(step_number=1, title="Add route", description="Memory token", affected_files=["app/auth.py"])],
        dependencies=[],
        testing_strategy={"unit_tests": ["Test reset"]},
        risks_and_assumptions=[],
    )

    with patch("app.services.inspection_service.InspectionService.inspect_repository", return_value=mock_inspection), \
         patch("app.agents.product_analyst.ProductAnalystAgent.analyze", return_value=initial_analysis), \
         patch("app.agents.architect.ArchitectAgent.plan", return_value=initial_plan):

        pipeline_res = client.post(f"/api/v1/tasks/{task_id}/pipeline")
        assert pipeline_res.status_code == 200
        assert pipeline_res.json()["implementation_plan"]["summary"] == "Initial Plan: Store token in memory"

    # 2. Submit CHANGES_REQUESTED with detailed feedback
    revised_analysis = ProductAnalystOutput(
        requirement_summary="Revised password reset with MongoDB and hash",
        functional_requirements=["Store token in MongoDB", "Hash password with bcrypt"],
        nonfunctional_requirements=["15 min token expiry"],
        acceptance_criteria=["Password hashed in DB", "Expired tokens rejected"],
        ambiguities=[],
        clarification_questions=[],
    )
    revised_plan = ArchitectPlanOutput(
        summary="Revised Plan: MongoDB token storage with bcrypt hashing and 15min expiry",
        repository_understanding="FastAPI auth service with MongoDB",
        confirmed_observations=["MongoDB client used"],
        files_to_create=[FileToCreate(path="app/services/token_service.py", purpose="Token management")],
        files_to_modify=[FileToModify(path="app/auth.py", reason="Update reset endpoint", changes_summary="Use token service")],
        api_contract_changes=[],
        implementation_steps=[
            ImplementationStep(step_number=1, title="Create token service", description="Token lifecycle", affected_files=["app/services/token_service.py"]),
            ImplementationStep(step_number=2, title="Update auth route", description="Call token service", affected_files=["app/auth.py"]),
        ],
        dependencies=["bcrypt", "motor"],
        testing_strategy={"unit_tests": ["Test token expiry", "Test bcrypt hash"]},
        risks_and_assumptions=["MongoDB availability"],
    )

    feedback_text = "Store reset tokens in MongoDB with 15min expiration and hash new passwords using bcrypt."
    with patch("app.agents.product_analyst.ProductAnalystAgent.analyze", return_value=revised_analysis) as mock_analyze, \
         patch("app.agents.architect.ArchitectAgent.plan", return_value=revised_plan) as mock_plan:

        changes_res = client.post(
            f"/api/v1/tasks/{task_id}/approval",
            json={"decision": "CHANGES_REQUESTED", "feedback": feedback_text},
        )
        assert changes_res.status_code == 200
        changes_data = changes_res.json()

        # Verify response structure and message
        assert changes_data["status"] == "recorded"
        assert changes_data["decision"] == "CHANGES_REQUESTED"
        assert "Plan revised to incorporate review feedback" in changes_data["message"]
        assert changes_data["task"] is not None

        # Verify returned task has updated plan and AWAITING_APPROVAL status
        updated_task = changes_data["task"]
        assert updated_task["status"] == "AWAITING_APPROVAL"
        assert updated_task["implementation_plan"]["summary"] == "Revised Plan: MongoDB token storage with bcrypt hashing and 15min expiry"
        assert len(updated_task["implementation_plan"]["files_to_create"]) == 1
        assert updated_task["implementation_plan"]["files_to_create"][0]["path"] == "app/services/token_service.py"
        assert len(updated_task["implementation_plan"]["implementation_steps"]) == 2

        # Verify agents were called with feedback and previous state
        mock_analyze.assert_called_once()
        _, analyze_kwargs = mock_analyze.call_args
        assert analyze_kwargs["user_feedback"] == feedback_text
        assert analyze_kwargs["previous_analysis"] is not None

        mock_plan.assert_called_once()
        _, plan_kwargs = mock_plan.call_args
        assert plan_kwargs["user_feedback"] == feedback_text
        assert plan_kwargs["previous_plan"] is not None

    # 3. Verify GET /tasks/{task_id} reflects the revised plan in the database
    get_res = client.get(f"/api/v1/tasks/{task_id}")
    assert get_res.status_code == 200
    current = get_res.json()
    assert current["status"] == "AWAITING_APPROVAL"
    assert current["implementation_plan"]["summary"] == "Revised Plan: MongoDB token storage with bcrypt hashing and 15min expiry"
    assert len(current["approvals"]) == 1
    assert current["approvals"][0]["decision"] == "CHANGES_REQUESTED"
    assert current["approvals"][0]["feedback"] == feedback_text

    # 4. Now Human Approves the REVISED plan
    final_approval_res = client.post(
        f"/api/v1/tasks/{task_id}/approval",
        json={"decision": "APPROVED", "feedback": "Revised plan looks great!"},
    )
    assert final_approval_res.status_code == 200
    final_data = final_approval_res.json()
    assert final_data["decision"] == "APPROVED"
    assert final_data["task"]["status"] == "APPROVED"
    # Verify the approved plan is the revised plan
    assert final_data["task"]["implementation_plan"]["summary"] == "Revised Plan: MongoDB token storage with bcrypt hashing and 15min expiry"
    assert len(final_data["task"]["approvals"]) == 2


