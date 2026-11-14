"""Tests for Product Analyst and Architect Agent schemas and execution."""

import pytest
from unittest.mock import MagicMock, patch
from app.agents.schemas import ProductAnalystOutput, ArchitectPlanOutput
from app.agents.product_analyst import ProductAnalystAgent
from app.agents.architect import ArchitectAgent


def test_product_analyst_schema_validation():
    """Verify ProductAnalystOutput validates complete requirement specification."""
    payload = {
        "requirement_summary": "Add JWT authentication to FastAPI backend.",
        "functional_requirements": ["Create login endpoint", "Return JWT bearer token"],
        "nonfunctional_requirements": ["Token expiration after 60 minutes", "Use BCrypt for passwords"],
        "acceptance_criteria": ["Given valid credentials, return 200 with JWT"],
        "ambiguities": ["Refresh token rotation not specified; default to single access token"],
        "clarification_questions": [],
    }
    output = ProductAnalystOutput.model_validate(payload)
    assert output.requirement_summary.startswith("Add JWT")
    assert len(output.functional_requirements) == 2


def test_architect_schema_validation():
    """Verify ArchitectPlanOutput validates complete implementation plan."""
    payload = {
        "summary": "Implement JWT authentication using existing FastAPI and Pydantic infrastructure.",
        "repository_understanding": "Python FastAPI application with SQLAlchemy and Alembic.",
        "confirmed_observations": ["FastAPI is present in requirements.txt", "app/main.py is entrypoint"],
        "files_to_create": [{"path": "app/core/security.py", "purpose": "Token creation and password hashing"}],
        "files_to_modify": [{"path": "app/main.py", "reason": "Mount auth router", "changes_summary": "Add auth router"}],
        "api_contract_changes": [{"endpoint": "/api/v1/auth/login", "method": "POST", "description": "Returns token"}],
        "implementation_steps": [{"step_number": 1, "title": "Create security module", "description": "Add JWT helpers", "affected_files": ["app/core/security.py"]}],
        "dependencies": ["pyjwt", "passlib"],
        "testing_strategy": {"unit_tests": ["Test password hashing", "Test token encoding/decoding"]},
        "risks_and_assumptions": ["Secret key must be supplied via environment variable"],
    }
    plan = ArchitectPlanOutput.model_validate(payload)
    assert len(plan.files_to_create) == 1
    assert len(plan.files_to_modify) == 1
    assert len(plan.implementation_steps) == 1


@pytest.mark.asyncio
async def test_product_analyst_mock_execution():
    """Verify Product Analyst runs and parses JSON completion."""
    agent = ProductAnalystAgent()
    agent.groq_provider.api_key = "gsk_mock_valid_key_123"

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"requirement_summary": "Test summary", "functional_requirements": ["Req 1"], "nonfunctional_requirements": ["Nonfunc 1"], "acceptance_criteria": ["Crit 1"], "ambiguities": [], "clarification_questions": []}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    with patch.object(agent.groq_provider, "_get_client", return_value=mock_client):
        result = await agent.analyze("Add payment gateway", {"detected_languages": ["Python"]})
        assert result.requirement_summary == "Test summary"
        assert result.functional_requirements == ["Req 1"]


@pytest.mark.asyncio
async def test_architect_mock_execution():
    """Verify Architect Agent runs and parses plan completion."""
    agent = ArchitectAgent()
    agent.groq_provider.api_key = "gsk_mock_valid_key_123"

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"summary": "Plan summary", "repository_understanding": "Repo underst.", "confirmed_observations": ["Fact 1"], "files_to_create": [{"path": "new.py", "purpose": "do something"}], "files_to_modify": [], "api_contract_changes": [], "implementation_steps": [{"step_number": 1, "title": "Step 1", "description": "Desc", "affected_files": ["new.py"]}], "dependencies": [], "testing_strategy": {}, "risks_and_assumptions": ["Risk 1"]}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    with patch.object(agent.groq_provider, "_get_client", return_value=mock_client):
        analysis = ProductAnalystOutput(
            requirement_summary="Summary",
            functional_requirements=["F1"],
            nonfunctional_requirements=["N1"],
            acceptance_criteria=["A1"],
            ambiguities=[],
            clarification_questions=[],
        )
        plan = await agent.plan(analysis, {"confirmed_facts": ["Fact 1"]})
        assert plan.summary == "Plan summary"
        assert len(plan.files_to_create) == 1
