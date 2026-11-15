"""Unit tests for QA Engineer Agent (Chapter 4)."""

import json
from pathlib import Path
import pytest

from app.agents.qa_engineer import QAEngineerAgent
from app.agents.schemas import QATestResult


def test_discover_test_commands_nodejs_root(tmp_path: Path):
    agent = QAEngineerAgent()
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"scripts": {"test": "jest --detectOpenHandles"}}), encoding="utf-8")

    cmds = agent.discover_test_commands(tmp_path)
    assert len(cmds) > 0
    assert any("jest" in c or "npm test" in c for c in cmds)
    # Must never include pytest on Node repo
    assert not any("pytest" in c for c in cmds)


def test_discover_test_commands_monorepo(tmp_path: Path):
    agent = QAEngineerAgent()
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir(parents=True)
    (backend_dir / "package.json").write_text(json.dumps({"scripts": {"test": "jest"}}), encoding="utf-8")

    cmds = agent.discover_test_commands(tmp_path)
    assert len(cmds) > 0
    assert any("cd backend" in c for c in cmds)
    assert not any("pytest" in c for c in cmds)


def test_discover_test_commands_monorepo_orchestrator_deduplication(tmp_path: Path):
    """If root package.json test script orchestrates backend, do not duplicate commands."""
    agent = QAEngineerAgent()
    root_pkg = tmp_path / "package.json"
    root_pkg.write_text(json.dumps({
        "scripts": {
            "test:backend": "npm --prefix backend test",
            "test": "npm run test:backend"
        }
    }), encoding="utf-8")

    backend_dir = tmp_path / "backend"
    backend_dir.mkdir(parents=True)
    (backend_dir / "package.json").write_text(json.dumps({"scripts": {"test": "jest"}}), encoding="utf-8")

    cmds = agent.discover_test_commands(tmp_path)
    # Should only run npm test, NOT also cd backend && npm test
    assert len(cmds) == 1
    assert cmds[0] == "npm test"


def test_never_runs_pytest_on_javascript_repo_with_backend_tests_folder(tmp_path: Path):
    """TaskFlow MERN bug reproduction: backend/tests has JS files, pytest must NEVER be invoked."""
    agent = QAEngineerAgent()
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"scripts": {"test": "npm run test:backend"}}), encoding="utf-8")

    backend_tests = tmp_path / "backend" / "tests"
    backend_tests.mkdir(parents=True)
    (backend_tests / "auth.test.js").write_text("// javascript test", encoding="utf-8")
    (backend_tests / "task.test.js").write_text("// javascript test", encoding="utf-8")

    cmds = agent.discover_test_commands(tmp_path)
    assert not any("pytest" in c for c in cmds)
    assert any("npm test" in c for c in cmds)


def test_discover_test_commands_python(tmp_path: Path):
    agent = QAEngineerAgent()
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_api.py").write_text("def test_dummy(): pass\n", encoding="utf-8")

    cmds = agent.discover_test_commands(tmp_path)
    assert any("pytest" in c for c in cmds)


def test_parse_test_output_jest():
    agent = QAEngineerAgent()
    stdout = """
PASS src/auth.test.js
FAIL src/passwordReset.test.js
  ● Password Reset › should return 400 if token missing

Tests:       1 failed, 7 passed, 8 total
Snapshots:   0 total
Time:        2.34 s
"""
    result = agent.parse_test_output("npm test", 1, stdout, "")
    assert result["passed"] == 7
    assert result["failed"] == 1
    assert result["failure_type"] == "CODE_REGRESSION"
    assert len(result["test_details"]) >= 1
    assert any("Password Reset" in t.test_name for t in result["test_details"])


def test_parse_test_output_env_error_missing_binary():
    agent = QAEngineerAgent()
    stderr = "'jest' is not recognized as an internal or external command, operable program or batch file."
    result = agent.parse_test_output("npm test", 1, "", stderr)
    assert result["failure_type"] == "ENVIRONMENT_ERROR"
    assert result["failed"] == 1


def test_parse_test_output_pytest():
    agent = QAEngineerAgent()
    stdout = "================== 12 passed, 2 failed in 3.14s =================="
    result = agent.parse_test_output("pytest", 1, stdout, "")
    assert result["passed"] == 12
    assert result["failed"] == 2
    assert result["failure_type"] == "CODE_REGRESSION"


def test_parse_test_output_pytest_no_tests():
    agent = QAEngineerAgent()
    stdout = "collected 0 items\nno tests ran in 0.01s"
    result = agent.parse_test_output("pytest", 5, stdout, "")
    assert result["failure_type"] == "NO_TESTS_FOUND"


def test_compute_failure_signature_deterministic():
    agent = QAEngineerAgent()
    failing_tests = [
        QATestResult(test_name="auth.test.js:test_login", status="FAILED"),
        QATestResult(test_name="auth.test.js:test_token", status="FAILED"),
    ]
    sig1 = agent.compute_failure_signature([1], failing_tests, "TypeError: cannot read property 'token'")
    sig2 = agent.compute_failure_signature([1], failing_tests, "TypeError: cannot read property 'token'")

    # Same failure produces identical deterministic signature
    assert sig1 == sig2
    assert sig1 is not None

    # Different failure produces different signature
    diff_tests = [QATestResult(test_name="different_test", status="FAILED")]
    sig3 = agent.compute_failure_signature([1], diff_tests, "SyntaxError: unexpected token")
    assert sig1 != sig3
