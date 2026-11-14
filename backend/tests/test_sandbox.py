"""Sandbox Service isolation and security tests (Chapter 3).

Tests:
1. Environment sanitization removes all forbidden secrets.
2. Execution inside workspace returns expected stdout and exit code.
3. Timeout handling properly terminates long-running execution.
4. Metadata inspection reflects configured resource limits.
"""

import os
import sys
from pathlib import Path
import pytest

from app.services.sandbox_service import (
    SandboxService,
    SandboxExecutionResult,
    FORBIDDEN_ENV_KEYS,
)


def test_sanitize_env_strips_secrets():
    """Secrets like GITHUB_TOKEN and GROQ_API_KEY must never be passed to sandbox."""
    service = SandboxService()

    # Artificially populate secrets in os.environ for testing
    os.environ["GITHUB_TOKEN"] = "ghp_secret_token_123"
    os.environ["GROQ_API_KEY"] = "gsk_secret_key_456"
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"

    try:
        sanitized = service._sanitize_env({
            "CUSTOM_VAR": "safe_value",
            "OPENAI_API_KEY": "should_be_stripped",
        })

        # Assert no forbidden keys present
        for forbidden in FORBIDDEN_ENV_KEYS:
            assert forbidden not in sanitized, f"{forbidden} leaked into sanitized environment!"

        assert sanitized.get("CUSTOM_VAR") == "safe_value"
    finally:
        os.environ.pop("GITHUB_TOKEN", None)
        os.environ.pop("GROQ_API_KEY", None)
        os.environ.pop("DATABASE_URL", None)


def test_sandbox_run_command_success(tmp_path):
    """Sandbox executes command in workspace and captures output."""
    service = SandboxService()
    # Create a small script or file in workspace
    test_file = tmp_path / "hello.txt"
    test_file.write_text("sandbox test content", encoding="utf-8")

    # Use python executable to run a quick print command
    cmd = [sys.executable, "-c", "print('hello from sandbox')"]
    result = service.run_command(cmd, workspace_path=tmp_path, timeout=10.0)

    assert result.exit_code == 0
    assert "hello from sandbox" in result.stdout
    assert not result.timed_out
    assert result.error is None


def test_sandbox_timeout_handling(tmp_path):
    """Commands exceeding timeout threshold must be terminated."""
    service = SandboxService()
    # Python script that sleeps for 5 seconds, with 1s timeout
    cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
    result = service.run_command(cmd, workspace_path=tmp_path, timeout=1.0)

    assert result.timed_out is True
    assert result.exit_code == -1
    assert "timed out" in result.stderr.lower()


def test_sandbox_invalid_workspace():
    """Execution in non-existent directory must fail cleanly."""
    service = SandboxService()
    invalid_path = Path("/nonexistent/directory/path/devpilot")
    result = service.run_command(["echo", "1"], workspace_path=invalid_path)

    assert result.exit_code == -1
    assert "does not exist" in result.stderr


def test_sandbox_info_metadata():
    """Sandbox info must expose resource limits and isolation parameters."""
    service = SandboxService()
    info = service.get_sandbox_info()

    assert "mode" in info
    assert "memory_limit" in info
    assert "cpu_limit" in info
    assert "timeout_seconds" in info
    assert info["secrets_stripped"] is True

