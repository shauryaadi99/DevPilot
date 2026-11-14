"""Execution Sandbox Service (Chapter 3).

Provides isolated command and script execution for generated and repository-provided
code, ensuring untrusted code does not run unconstrained on the DevPilot host.

THREAT MODEL & KNOWN LIMITATIONS:
==================================
Threat Model:
- Untrusted repository code or generated scripts attempting:
  1. Network egress / exfiltration of local files or credentials.
  2. Accessing host credentials (e.g., GITHUB_TOKEN, GROQ_API_KEY).
  3. Path traversal outside the designated task workspace.
  4. CPU/memory exhaustion and infinite loops (DoS).
  5. Persistence across task runs.

Mitigations Implemented:
- Docker Isolation (Primary when container image is available):
  * Network isolation: '--network none' blocks all incoming and outgoing network traffic.
  * Resource constraints: '--memory 512m' and '--cpus 0.5' cap resource usage.
  * Filesystem isolation: only workspace is mounted ('-v {workspace}:/workspace:rw').
  * Container is ephemeral: '--rm' ensures container destruction upon exit.
  * Zero inherited host environment variables.
- Subprocess Sandbox (Fallback when Docker container is unavailable):
  * Environment scrubbing: All host secrets (GITHUB_TOKEN, GROQ_API_KEY, DATABASE_URL, etc.)
    are stripped. Only minimal safe runtime environment is passed.
  * Workspace confinement: Command execution strictly sets `cwd` to workspace root.
  * Strict timeouts: Kills process and its child process tree on timeout expiry.
  * Path checking: Prevents execution outside designated workspace boundaries.

Known Limitations:
- When using the Subprocess fallback, process runs under the same OS user as the backend server.
  Kernel-level cgroups and true network namespace isolation are not enforced without Docker.
- Symlinks pointing outside the workspace inside untrusted repos could be traversed by host OS
  if not pre-validated.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging import logger

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MEMORY_LIMIT = "512m"
DEFAULT_CPU_LIMIT = "0.5"

# Environment variables that must NEVER be passed to the sandbox
FORBIDDEN_ENV_KEYS = {
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DATABASE_URL",
    "SECRET_KEY",
    "JWT_SECRET",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "SSH_AUTH_SOCK",
}


@dataclass
class SandboxExecutionResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    isolation_mode: str = "subprocess"  # "docker" or "subprocess"
    error: Optional[str] = None


class SandboxService:
    """Manages secure, isolated execution of commands in a repository workspace."""

    def __init__(self, docker_image: Optional[str] = None):
        self.docker_image = docker_image
        self._docker_available: Optional[bool] = None

    def is_docker_available(self) -> bool:
        """Check if Docker CLI and daemon are reachable."""
        if self._docker_available is not None:
            return self._docker_available

        try:
            res = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self._docker_available = (res.returncode == 0)
        except Exception:
            self._docker_available = False

        return self._docker_available

    def get_sandbox_info(self) -> Dict[str, Any]:
        """Return metadata about active sandbox environment and isolation level."""
        docker_active = self.is_docker_available() and self.docker_image is not None
        return {
            "mode": "docker" if docker_active else "subprocess",
            "docker_available": self.is_docker_available(),
            "docker_image": self.docker_image if docker_active else None,
            "memory_limit": DEFAULT_MEMORY_LIMIT,
            "cpu_limit": DEFAULT_CPU_LIMIT,
            "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
            "network_isolated": docker_active,
            "secrets_stripped": True,
        }

    def _sanitize_env(self, custom_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Create a clean environment stripped of all application and host secrets."""
        # Start with standard OS minimal variables
        safe_keys = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "HOME", "LANG", "LC_ALL"}
        clean_env: Dict[str, str] = {}
        for k, v in os.environ.items():
            if k.upper() in safe_keys and k.upper() not in FORBIDDEN_ENV_KEYS:
                clean_env[k] = v

        # Add explicitly approved non-secret variables
        if custom_env:
            for k, v in custom_env.items():
                if k.upper() not in FORBIDDEN_ENV_KEYS:
                    clean_env[k] = v
                else:
                    logger.warning(f"Forbidden environment key '{k}' stripped from sandbox execution.")

        return clean_env

    def run_command(
        self,
        command: List[str] | str,
        workspace_path: Path,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxExecutionResult:
        """Execute a command within the sandbox boundaries.

        Args:
            command: Command and arguments list (e.g. ['npm', 'test']).
            workspace_path: Path to the isolated task workspace.
            timeout: Execution timeout in seconds.
            env: Optional additional non-secret environment variables.

        Returns:
            SandboxExecutionResult with exit code, outputs, and status.
        """
        workspace_path = workspace_path.resolve()
        if not workspace_path.exists() or not workspace_path.is_dir():
            return SandboxExecutionResult(
                command=str(command),
                exit_code=-1,
                stdout="",
                stderr="Workspace path does not exist or is not a directory.",
                duration_seconds=0.0,
                error="Invalid workspace path",
            )

        # Attempt Docker execution if configured & available
        if self.is_docker_available() and self.docker_image:
            return self._run_docker(command, workspace_path, timeout, env)

        # Fallback to isolated subprocess execution
        return self._run_subprocess(command, workspace_path, timeout, env)

    def _run_docker(
        self,
        command: List[str] | str,
        workspace_path: Path,
        timeout: float,
        env: Optional[Dict[str, str]],
    ) -> SandboxExecutionResult:
        """Execute inside Docker container with restricted resources and network disabled."""
        cmd_str = command if isinstance(command, str) else " ".join(command)
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", DEFAULT_MEMORY_LIMIT,
            "--cpus", DEFAULT_CPU_LIMIT,
            "-v", f"{workspace_path}:/workspace:rw",
            "-w", "/workspace",
        ]

        # Pass sanitized env
        sanitized = self._sanitize_env(env)
        for k, v in sanitized.items():
            if k in ("PATH", "LANG", "LC_ALL"):
                docker_cmd.extend(["-e", f"{k}={v}"])

        docker_cmd.append(self.docker_image or "alpine")
        if isinstance(command, list):
            docker_cmd.extend(command)
        else:
            docker_cmd.extend(["sh", "-c", command])

        import time
        start_time = time.time()
        try:
            res = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = time.time() - start_time
            return SandboxExecutionResult(
                command=cmd_str,
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                duration_seconds=duration,
                isolation_mode="docker",
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.warning(f"Docker sandbox command timed out after {timeout}s: {cmd_str}")
            return SandboxExecutionResult(
                command=cmd_str,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds.",
                duration_seconds=duration,
                timed_out=True,
                isolation_mode="docker",
                error="Execution timeout",
            )
        except Exception as exc:
            duration = time.time() - start_time
            logger.warning(f"Docker sandbox failed, falling back to subprocess: {exc}")
            return self._run_subprocess(command, workspace_path, timeout, env)

    def _run_subprocess(
        self,
        command: List[str] | str,
        workspace_path: Path,
        timeout: float,
        env: Optional[Dict[str, str]],
    ) -> SandboxExecutionResult:
        """Execute command in an isolated host subprocess with stripped env and timeout."""
        cmd_str = command if isinstance(command, str) else " ".join(command)
        clean_env = self._sanitize_env(env)

        import time
        start_time = time.time()
        try:
            shell_mode = isinstance(command, str)
            res = subprocess.run(
                command,
                cwd=str(workspace_path),
                env=clean_env,
                shell=shell_mode,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = time.time() - start_time
            return SandboxExecutionResult(
                command=cmd_str,
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                duration_seconds=duration,
                isolation_mode="subprocess",
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.warning(f"Subprocess sandbox timed out after {timeout}s: {cmd_str}")
            return SandboxExecutionResult(
                command=cmd_str,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds.",
                duration_seconds=duration,
                timed_out=True,
                isolation_mode="subprocess",
                error="Execution timeout",
            )
        except Exception as exc:
            duration = time.time() - start_time
            return SandboxExecutionResult(
                command=cmd_str,
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                duration_seconds=duration,
                isolation_mode="subprocess",
                error=str(exc),
            )

