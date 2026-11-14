"""Tests for repository inspection engine."""

import pytest
from unittest.mock import AsyncMock
from app.services.inspection_service import InspectionService


@pytest.mark.asyncio
async def test_inspection_service_detection():
    """Verify inspection service detects languages, manifests, frameworks, and entrypoints."""
    mock_github = AsyncMock()

    # Mock file tree
    mock_github.get_tree.return_value = [
        {"path": "package.json", "type": "blob", "size": 300},
        {"path": "src/app/page.tsx", "type": "blob", "size": 1500},
        {"path": "src/main.py", "type": "blob", "size": 800},
        {"path": "requirements.txt", "type": "blob", "size": 250},
        {"path": "README.md", "type": "blob", "size": 1200},
    ]

    # Mock file content
    def mock_content(owner, repo, path, branch=None):
        if path == "package.json":
            return '{"name": "my-web-app", "dependencies": {"next": "^15.0.0", "react": "^19.0.0"}}'
        if path == "requirements.txt":
            return "fastapi>=0.115.0\npytest>=8.0.0\n"
        return "Generic readme content"

    mock_github.get_file_content.side_effect = mock_content

    service = InspectionService(github_client=mock_github)
    result = await service.inspect_repository(owner="test-owner", repo="test-repo", default_branch="main")

    assert "TypeScript (React)" in result["detected_languages"]
    assert "Python" in result["detected_languages"]
    assert "Next.js" in result["detected_frameworks"]
    assert "React" in result["detected_frameworks"]
    assert "FastAPI" in result["detected_frameworks"]
    assert "src/app/page.tsx" in result["detected_entrypoints"]
    assert "package.json" in result["manifests_summary"]
    assert len(result["confirmed_facts"]) > 0
    assert len(result["unknowns"]) > 0
