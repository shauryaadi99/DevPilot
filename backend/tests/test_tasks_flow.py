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
