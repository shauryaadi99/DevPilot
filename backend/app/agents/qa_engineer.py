"""QA Engineer Agent (Chapter 4).

Executes repository-appropriate tests inside an isolated workspace,
inspects execution logs, evaluates acceptance criteria, calculates
deterministic failure signatures for stall detection, and produces
structured QA reports with actionable feedback for the Developer Agent.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agents.schemas import (
    AcceptanceCriterionResult,
    ArchitectPlanOutput,
    QAOutput,
    QATestResult,
)
from app.core.logging import logger
from app.integrations.groq_client import get_groq_provider
from app.services.sandbox_service import SandboxService

QA_SYSTEM_PROMPT = """You are the QA Engineer Agent for DevPilot, an autonomous software engineering system.
Your responsibility:
1. Analyze the test execution logs and individual test failure traces.
2. Determine whether the implementation satisfies the acceptance criteria.
3. If code test failures occurred, diagnose the exact root cause and formulate concise, actionable feedback for the Developer Agent.

CRITICAL RULES:
- Never suggest adding test files or dependencies in languages not used by the repository (e.g. NEVER suggest Python tests or pytest for JavaScript/TypeScript repositories).
- Never suggest installing dependencies unless they are genuinely missing from package.json or requirements.txt.
- Focus exclusively on correcting the implementation logic in the files modified for the current task.
- If the failure is an environment/configuration issue (e.g. missing dependencies or binary not found), clearly state that rather than suggesting code changes.

Output Rules:
- Return ONLY valid JSON matching this schema:
{
  "failure_summary": "1 to 2 sentences diagnosing why tests failed, or null if all passed",
  "actionable_feedback": "Concrete instructions for Developer Agent detailing the exact files, functions, and logic to fix, or null if passed",
  "acceptance_criteria_results": [
    {"criterion": "string", "status": "SATISFIED" | "NOT_SATISFIED" | "UNKNOWN", "evidence": "string"}
  ]
}
"""


class QAEngineerAgent:
    """Automates test execution, analysis, and feedback in isolated task workspaces."""

    def __init__(self, sandbox: Optional[SandboxService] = None):
        self.sandbox = sandbox or SandboxService()
        self.provider = get_groq_provider()

    def detect_ecosystem(self, workspace_path: Path) -> Dict[str, Any]:
        """Inspect workspace to identify languages, package managers, and test files."""
        # Find test files excluding hidden and vendor directories
        js_test_files: List[Path] = []
        py_test_files: List[Path] = []

        for p in workspace_path.rglob("*"):
            if not p.is_file():
                continue
            parts = p.parts
            if any(part.startswith(".") or part in ("node_modules", ".venv", "venv", "dist", "build", "__pycache__") for part in parts):
                continue

            name_lower = p.name.lower()
            if (
                name_lower.endswith(".test.js") or name_lower.endswith(".spec.js") or
                name_lower.endswith(".test.ts") or name_lower.endswith(".spec.ts") or
                name_lower.endswith(".test.jsx") or name_lower.endswith(".test.tsx")
            ):
                js_test_files.append(p)
            elif (
                (name_lower.startswith("test_") and name_lower.endswith(".py")) or
                name_lower.endswith("_test.py")
            ):
                py_test_files.append(p)

        has_root_pkg = (workspace_path / "package.json").is_file()
        has_backend_pkg = (workspace_path / "backend" / "package.json").is_file()
        has_frontend_pkg = (workspace_path / "frontend" / "package.json").is_file()

        has_pytest_cfg = (
            (workspace_path / "pytest.ini").is_file() or
            (workspace_path / "pyproject.toml").is_file() or
            (workspace_path / "setup.cfg").is_file() or
            (workspace_path / "backend" / "pytest.ini").is_file()
        )

        is_node = has_root_pkg or has_backend_pkg or has_frontend_pkg or bool(js_test_files)

        # STRICT PYTHON RULE:
        # Python test runner is only valid if actual Python test files exist,
        # OR if Python config exists in a non-Node repository.
        has_py_source = any(
            p.suffix == ".py"
            for p in workspace_path.rglob("*.py")
            if not any(part.startswith(".") or part in ("node_modules", ".venv", "venv", "__pycache__") for part in p.parts)
        )
        is_python = bool(py_test_files) or (has_pytest_cfg and (has_py_source or not is_node))

        return {
            "is_node": is_node,
            "is_python": is_python,
            "js_test_files": js_test_files,
            "py_test_files": py_test_files,
            "has_root_pkg": has_root_pkg,
            "has_backend_pkg": has_backend_pkg,
            "has_frontend_pkg": has_frontend_pkg,
        }

    def discover_test_commands(
        self,
        workspace_path: Path,
        plan: Optional[ArchitectPlanOutput] = None,
    ) -> List[str]:
        """Discover appropriate test commands by inspecting repository structure and manifests."""
        eco = self.detect_ecosystem(workspace_path)
        commands: List[str] = []

        # 1. Check if testing_strategy in plan provides explicit test commands
        if plan and plan.testing_strategy:
            explicit_cmds = plan.testing_strategy.get("commands") or plan.testing_strategy.get("test_commands")
            if explicit_cmds and isinstance(explicit_cmds, list):
                for cmd in explicit_cmds:
                    if isinstance(cmd, str) and cmd.strip():
                        # Validate that explicit command matches ecosystem (e.g. reject pytest on Node-only)
                        if "pytest" in cmd and not eco["is_python"]:
                            logger.warning(f"Rejecting plan test command '{cmd}' because repository has no Python test suite.")
                            continue
                        commands.append(cmd.strip())

        if commands:
            return commands

        # 2. Node.js test discovery with monorepo script deduplication
        if eco["is_node"]:
            root_orchestrator = False
            root_pkg_path = workspace_path / "package.json"
            if root_pkg_path.is_file():
                try:
                    data = json.loads(root_pkg_path.read_text(encoding="utf-8"))
                    scripts = data.get("scripts", {})
                    test_script = scripts.get("test", "")
                    if test_script and "no test specified" not in test_script.lower():
                        # Check if root script orchestrates subprojects
                        is_orchestrator = any(
                            sub in test_script.lower()
                            for sub in ["backend", "frontend", "--prefix", "workspaces", "turbo", "lerna", "concurrently"]
                        )
                        if "jest" in test_script:
                            commands.append("npm test -- --runInBand")
                        else:
                            commands.append("npm test")

                        if is_orchestrator:
                            root_orchestrator = True
                except Exception as e:
                    logger.warning(f"Failed parsing root package.json: {e}")

            # Only inspect subprojects if root does not already orchestrate them
            if not root_orchestrator:
                for subdir in ["backend", "frontend"]:
                    sub_pkg = workspace_path / subdir / "package.json"
                    if sub_pkg.is_file():
                        try:
                            data = json.loads(sub_pkg.read_text(encoding="utf-8"))
                            scripts = data.get("scripts", {})
                            test_script = scripts.get("test", "")
                            if test_script and "no test specified" not in test_script.lower():
                                test_cmd = "npm test -- --runInBand" if "jest" in test_script else "npm test"
                                commands.append(f"cd {subdir} && {test_cmd}")
                        except Exception as e:
                            logger.warning(f"Failed parsing {subdir}/package.json: {e}")

        # 3. Python test discovery (STRICT: only if Python tests actually exist)
        if eco["is_python"] and (eco["py_test_files"] or not eco["is_node"]):
            backend_tests = workspace_path / "backend" / "tests"
            backend_has_py = (
                backend_tests.exists() and
                any(p.name.endswith(".py") for p in backend_tests.iterdir() if p.is_file())
            )
            if (workspace_path / "backend" / "pytest.ini").is_file() or backend_has_py:
                commands.append("pytest backend/tests -v")
            else:
                commands.append("pytest -v")

        # 4. Fallback default if nothing detected
        if not commands:
            logger.info("No explicit test runners detected; defaulting to basic status verification.")
            commands.append("git status")

        return commands

    def ensure_dependencies(self, workspace_path: Path, commands: List[str]) -> None:
        """Pre-flight check: ensure required dependencies exist before executing test commands."""
        for cmd in commands:
            if "npm" in cmd or "jest" in cmd:
                # Check root
                root_pkg = workspace_path / "package.json"
                if root_pkg.is_file() and not (workspace_path / "node_modules").exists():
                    logger.info(f"Root node_modules missing in {workspace_path}. Bootstrapping dependencies...")
                    self.sandbox.run_command("npm install --prefer-offline --no-audit", workspace_path, timeout=120.0)

                # Check backend
                backend_dir = workspace_path / "backend"
                if backend_dir.is_dir() and (backend_dir / "package.json").is_file() and not (backend_dir / "node_modules").exists():
                    logger.info(f"Backend node_modules missing in {backend_dir}. Bootstrapping dependencies...")
                    self.sandbox.run_command("npm install --prefer-offline --no-audit", backend_dir, timeout=120.0)

                # Check frontend
                frontend_dir = workspace_path / "frontend"
                if "frontend" in cmd and frontend_dir.is_dir() and (frontend_dir / "package.json").is_file() and not (frontend_dir / "node_modules").exists():
                    logger.info(f"Frontend node_modules missing in {frontend_dir}. Bootstrapping dependencies...")
                    self.sandbox.run_command("npm install --prefer-offline --no-audit", frontend_dir, timeout=120.0)

    def parse_test_output(
        self,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
    ) -> Dict[str, Any]:
        """Extract test counts, classify failure type, and extract failing test details."""
        full_text = f"{stdout}\n{stderr}"
        passed = 0
        failed = 0
        skipped = 0
        test_details: List[QATestResult] = []
        failure_type: Optional[str] = None

        # 1. Detect Environment Errors
        env_error_patterns = [
            r"(?:'jest'|'vitest'|'mocha'|'pytest') is not recognized",
            r"(?:jest|vitest|mocha|pytest): (?:command not found|not found)",
            r"Cannot find module ['\"]([^'\"]+)['\"]",
            r"MODULE_NOT_FOUND",
            r"npm ERR! missing script:",
            r"No such file or directory",
        ]
        is_env_error = any(re.search(pat, full_text, re.IGNORECASE) for pat in env_error_patterns)

        # 2. Detect "No Tests Found"
        no_tests_patterns = [
            r"collected 0 items",
            r"no tests collected",
            r"no tests found matching",
            r"No tests found related to files changed",
        ]
        is_no_tests = any(re.search(pat, full_text, re.IGNORECASE) for pat in no_tests_patterns)

        # 3. Parse Jest output: "Tests: 1 failed, 7 passed, 8 total"
        jest_match = re.search(
            r"Tests:\s*(?:(\d+)\s+failed,?\s*)?(?:(\d+)\s+skipped,?\s*)?(?:(\d+)\s+passed,?\s*)?(\d+)\s+total",
            full_text,
            re.IGNORECASE,
        )
        if jest_match:
            failed = int(jest_match.group(1) or 0)
            skipped = int(jest_match.group(2) or 0)
            passed = int(jest_match.group(3) or 0)
        else:
            # 4. Parse Pytest output: "5 passed, 1 failed, 2 skipped in 1.2s"
            pytest_passed = re.search(r"(\d+)\s+passed", full_text)
            pytest_failed = re.search(r"(\d+)\s+failed", full_text)
            pytest_skipped = re.search(r"(\d+)\s+skipped", full_text)
            if pytest_passed or pytest_failed or pytest_skipped:
                passed = int(pytest_passed.group(1)) if pytest_passed else 0
                failed = int(pytest_failed.group(1)) if pytest_failed else 0
                skipped = int(pytest_skipped.group(2 if pytest_failed and pytest_passed else 1)) if pytest_skipped else 0

        # Classify Failure Type
        if exit_code != 0 or failed > 0:
            if is_env_error:
                failure_type = "ENVIRONMENT_ERROR"
                if failed == 0 and passed == 0:
                    failed = 1
            elif is_no_tests and passed == 0:
                failure_type = "NO_TESTS_FOUND"
                if failed == 0:
                    failed = 1
            else:
                failure_type = "CODE_REGRESSION"
                if exit_code != 0 and failed == 0 and passed == 0:
                    failed = 1

        # Extract specific failing test names (for Jest and Pytest)
        failing_names = re.findall(r"(?:FAIL|FAILED|✕|×|●)\s+([^\n\r]+)", full_text)
        for name in failing_names[:10]:
            clean_name = name.strip()
            if any(clean_name.startswith(w) for w in ["Test Suites:", "Tests:", "Snapshots:", "Time:"]):
                continue
            test_details.append(
                QATestResult(
                    test_name=clean_name,
                    status="FAILED",
                    error_message=clean_name,
                )
            )

        return {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "test_details": test_details,
            "failure_type": failure_type,
        }

    def compute_failure_signature(
        self,
        exit_codes: List[int],
        failing_tests: List[QATestResult],
        stderr: str,
        failure_types: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Compute a deterministic SHA-256 fingerprint for stall detection.

        Identical failures produce identical signatures, allowing the engine
        to detect when a retry cycle made zero progress.
        """
        if all(code == 0 for code in exit_codes) and not failing_tests:
            return None

        components: List[str] = []
        if failure_types:
            for ft in sorted(set(failure_types)):
                if ft:
                    components.append(f"type:{ft}")

        for t in sorted(failing_tests, key=lambda x: x.test_name):
            components.append(f"test:{t.test_name}")

        # Capture key error names from stderr (e.g. ModuleNotFoundError, TypeError, SyntaxError)
        error_types = sorted(set(re.findall(r"([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):", stderr)))
        for et in error_types:
            components.append(f"err:{et}")

        if not components:
            first_lines = "\n".join(stderr.strip().splitlines()[:5])
            components.append(f"raw:{first_lines}")

        payload = "|".join(components)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    async def execute_and_evaluate(
        self,
        workspace_path: Path,
        acceptance_criteria: Optional[List[str]] = None,
        plan: Optional[ArchitectPlanOutput] = None,
        previous_failure_signature: Optional[str] = None,
    ) -> QAOutput:
        """Run discovered test commands, parse logs, calculate signatures, and formulate report."""
        test_execution_id = str(uuid.uuid4())
        commands = self.discover_test_commands(workspace_path, plan)
        logger.info(f"QA Agent executing commands in {workspace_path}: {commands}")

        # Pre-flight check: ensure dependencies exist
        self.ensure_dependencies(workspace_path, commands)

        all_passed = True
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        exit_codes: List[int] = []
        all_logs: List[str] = []
        all_test_details: List[QATestResult] = []
        combined_stderr: List[str] = []
        failure_types: List[str] = []

        for cmd in commands:
            res = self.sandbox.run_command(cmd, workspace_path, timeout=90.0)
            exit_codes.append(res.exit_code)
            all_logs.append(f"--- Command: {cmd} (Exit Code: {res.exit_code}) ---\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
            if res.stderr:
                combined_stderr.append(res.stderr)

            parsed = self.parse_test_output(cmd, res.exit_code, res.stdout, res.stderr)
            total_passed += parsed["passed"]
            total_failed += parsed["failed"]
            total_skipped += parsed["skipped"]
            all_test_details.extend(parsed["test_details"])
            if parsed.get("failure_type"):
                failure_types.append(parsed["failure_type"])

            if res.exit_code != 0 or parsed["failed"] > 0:
                all_passed = False

        logs_str = "\n\n".join(all_logs)
        stderr_str = "\n".join(combined_stderr)

        # Compute deterministic signature
        failure_sig = self.compute_failure_signature(exit_codes, all_test_details, stderr_str, failure_types) if not all_passed else None

        # Format initial acceptance criteria results
        crit_results: List[AcceptanceCriterionResult] = []
        for crit in (acceptance_criteria or []):
            crit_results.append(
                AcceptanceCriterionResult(
                    criterion=crit,
                    status="SATISFIED" if all_passed else "NOT_SATISFIED",
                    evidence=f"Overall tests {'passed' if all_passed else 'failed'} (Exit codes: {exit_codes})"
                )
            )

        failure_summary = None
        actionable_feedback = None

        if not all_passed:
            is_all_env_errors = all(ft in ("ENVIRONMENT_ERROR", "NO_TESTS_FOUND") for ft in failure_types) if failure_types else False

            if is_all_env_errors:
                failure_summary = (
                    f"Test environment configuration issue detected (exit codes: {exit_codes}). "
                    f"Test runner or dependencies are not installed in workspace. No code regression was detected."
                )
                actionable_feedback = (
                    "Ensure repository package dependencies and test runner binaries are installed in the workspace. "
                    "Do NOT modify application code logic or create tests in unrelated languages."
                )
            else:
                # Generate AI diagnosis for Developer Agent focused strictly on real code regressions
                failure_summary = f"Tests failed with exit codes {exit_codes}. {total_failed} test(s) failed."
                if all_test_details:
                    failure_summary += f" Failing items: {', '.join(t.test_name for t in all_test_details[:5])}."

                try:
                    prompt = (
                        f"Test execution failed.\n\n"
                        f"Commands executed: {commands}\n"
                        f"Exit codes: {exit_codes}\n"
                        f"Failing tests: {[t.test_name for t in all_test_details]}\n"
                        f"Execution Logs (truncated):\n{logs_str[-2500:]}\n\n"
                        f"Produce the JSON diagnosis and actionable feedback for the Developer Agent. "
                        f"Target ONLY the failing application code files. Do NOT suggest adding tests in other languages."
                    )
                    response = await self.provider.chat_completion(
                        messages=[
                            {"role": "system", "content": QA_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.1,
                        response_format={"type": "json_object"},
                    )
                    data = json.loads(response.content)
                    if data.get("failure_summary"):
                        failure_summary = data["failure_summary"]
                    actionable_feedback = data.get("actionable_feedback") or "Review failing test logs and correct logic."
                    if data.get("acceptance_criteria_results") and isinstance(data["acceptance_criteria_results"], list):
                        crit_results = [AcceptanceCriterionResult(**item) for item in data["acceptance_criteria_results"]]
                except Exception as e:
                    logger.warning(f"QA LLM evaluation fallback: {e}")
                    actionable_feedback = f"Investigate test failures in {commands}. Inspect logs:\n{stderr_str[:500]}"

        return QAOutput(
            test_execution_id=test_execution_id,
            overall_passed=all_passed,
            commands_executed=commands,
            tests_passed=total_passed,
            tests_failed=total_failed,
            tests_skipped=total_skipped,
            exit_codes=exit_codes,
            logs=logs_str,
            failure_summary=failure_summary,
            failure_signature=failure_sig,
            test_details=all_test_details,
            acceptance_criteria_results=crit_results,
            actionable_feedback=actionable_feedback,
        )
