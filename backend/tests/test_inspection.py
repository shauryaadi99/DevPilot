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


@pytest.mark.asyncio
async def test_inspection_mern_monorepo_detection():
    """Verify inspection service accurately detects MERN monorepo components (Express, MongoDB, React, Vite)."""
    mock_github = AsyncMock()

    mock_github.get_tree.return_value = [
        {"path": "package.json", "type": "blob", "size": 200},
        {"path": "backend/package.json", "type": "blob", "size": 600},
        {"path": "backend/src/server.js", "type": "blob", "size": 800},
        {"path": "backend/src/app.js", "type": "blob", "size": 1200},
        {"path": "backend/src/models/User.js", "type": "blob", "size": 1500},
        {"path": "backend/src/controllers/authController.js", "type": "blob", "size": 2500},
        {"path": "backend/src/routes/authRoutes.js", "type": "blob", "size": 900},
        {"path": "frontend/package.json", "type": "blob", "size": 500},
        {"path": "frontend/src/main.jsx", "type": "blob", "size": 400},
        {"path": "frontend/src/pages/Login.jsx", "type": "blob", "size": 2000},
        {"path": "README.md", "type": "blob", "size": 1500},
    ]

    def mock_content(owner, repo, path, branch=None):
        if path == "package.json":
            return '{"name": "taskflow-workspace"}'
        if path == "backend/package.json":
            return '{"name": "taskflow-backend", "dependencies": {"express": "^4.19.0", "mongoose": "^8.4.0", "bcryptjs": "^2.4.3", "jsonwebtoken": "^9.0.0"}}'
        if path == "frontend/package.json":
            return '{"name": "taskflow-frontend", "dependencies": {"react": "^18.3.0", "react-dom": "^18.3.0"}, "devDependencies": {"vite": "^5.0.0", "tailwindcss": "^3.4.0"}}'
        if path == "README.md":
            return "# TaskFlow\nBuilt using the MERN stack (MongoDB, Express, React, Node)."
        return ""

    mock_github.get_file_content.side_effect = mock_content

    service = InspectionService(github_client=mock_github)
    result = await service.inspect_repository(owner="shauryaadi99", repo="devpilot-taskflow-test", default_branch="main")

    assert "Express.js" in result["detected_frameworks"]
    assert "MongoDB" in result["detected_frameworks"]
    assert "Mongoose" in result["detected_frameworks"]
    assert "React" in result["detected_frameworks"]
    assert "Vite" in result["detected_frameworks"]
    assert "Tailwind CSS" in result["detected_frameworks"]
    assert "backend/src/server.js" in result["detected_entrypoints"]
    assert "frontend/src/main.jsx" in result["detected_entrypoints"]

    facts_joined = " ".join(result["confirmed_facts"])
    assert "bcryptjs" in facts_joined
    assert "backend/src/models/User.js" in facts_joined
    assert "backend/src/controllers/authController.js" in facts_joined


