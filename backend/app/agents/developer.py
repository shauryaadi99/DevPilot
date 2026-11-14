"""Developer Agent (Chapter 3).

Interprets an approved ArchitectPlanOutput and implements it step-by-step
using restricted filesystem tools within an isolated task workspace.
Reads existing files before writing, tracks changes, and reports progress.
Never modifies the approved plan or deviates silently.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from app.agents.schemas import ArchitectPlanOutput, ImplementationStep, FileToCreate, FileToModify
from app.core.logging import logger
from app.integrations.groq_client import get_groq_provider
from app.tools.filesystem_tools import FilesystemTools, FilesystemSecurityError

DEVELOPER_SYSTEM_PROMPT = """You are the Developer Agent for DevPilot, an autonomous software engineering system.
You receive ONE implementation step at a time with its context and produce the exact file content to write.

Rules (CRITICAL):
- Output ONLY valid JSON. No prose, no markdown fences, no explanations outside JSON.
- JSON schema: {"file_path": "relative/path", "content": "<full file content as string>", "explanation": "<1 sentence>"}
- Write the COMPLETE file content — not a diff, not a snippet.
- Respect existing code style, indentation, imports, and naming conventions.
- Reuse existing utilities/patterns; do not introduce unnecessary dependencies.
- If the step requires modifying an existing file, include ALL original content plus your changes.
- If the step creates a new file, write the full new file.
- explanation: 1 sentence max, describes what you did and why."""

FALLBACK_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]


@dataclass
class StepResult:
    step_number: int
    step_title: str
    file_path: str
    change_type: str  # CREATE or MODIFY
    success: bool
    explanation: str
    error: Optional[str] = None
    lines_added: int = 0
    lines_removed: int = 0
    diff_summary: str = ""


@dataclass
class DeveloperResult:
    success: bool
    steps_completed: int
    steps_total: int
    step_results: List[StepResult] = field(default_factory=list)
    error_message: Optional[str] = None
    commit_sha: Optional[str] = None


class DeveloperAgent:
    """Implements approved plans inside an isolated Git workspace."""

    def __init__(self):
        self.groq_provider = get_groq_provider()

    async def implement(
        self,
        plan: ArchitectPlanOutput,
        workspace_path: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> DeveloperResult:
        """Execute the full approved plan inside workspace_path.

        Args:
            plan: Approved ArchitectPlanOutput.
            workspace_path: Absolute path to cloned task workspace.
            progress_callback: Called with (current_step, total_steps, message) on each step.

        Returns:
            DeveloperResult with per-step outcomes.
        """
        if not self.groq_provider.is_configured:
            return DeveloperResult(
                success=False,
                steps_completed=0,
                steps_total=len(plan.implementation_steps),
                error_message="Groq API key not configured.",
            )

        fs = FilesystemTools(workspace_path)
        step_results: List[StepResult] = []
        steps = plan.implementation_steps
        total = len(steps)

        for i, step in enumerate(steps, start=1):
            step_title = step.title if hasattr(step, "title") else f"Step {i}"
            logger.info(f"Developer Agent — step {i}/{total}: {step_title}")

            if progress_callback:
                progress_callback(i, total, f"Executing: {step_title}")

            result = await self._execute_step(step, plan, fs, i)
            step_results.append(result)

            if not result.success:
                logger.error(f"Step {i} failed: {result.error}")
                return DeveloperResult(
                    success=False,
                    steps_completed=i - 1,
                    steps_total=total,
                    step_results=step_results,
                    error_message=f"Step {i} ({step_title}) failed: {result.error}",
                )

        return DeveloperResult(
            success=True,
            steps_completed=total,
            steps_total=total,
            step_results=step_results,
        )

    async def _execute_step(
        self,
        step: ImplementationStep,
        plan: ArchitectPlanOutput,
        fs: FilesystemTools,
        step_num: int,
    ) -> StepResult:
        """Run a single implementation step via LLM + filesystem tools."""
        step_title = step.title if hasattr(step, "title") else f"Step {step_num}"
        affected = step.affected_files if hasattr(step, "affected_files") and step.affected_files else []
        description = step.description if hasattr(step, "description") else str(step)

        # Read existing file contents for context
        existing_contents: Dict[str, str] = {}
        for fp in affected:
            read_result = fs.read_file(fp)
            if "content" in read_result:
                existing_contents[fp] = read_result["content"]

        # Determine primary file target from plan
        target_file = affected[0] if affected else None

        # Check if file should be created or modified
        create_paths = {f.path for f in plan.files_to_create if hasattr(f, "path")}
        change_type = "CREATE" if target_file and target_file in create_paths else "MODIFY"

        # Build LLM prompt
        context_parts = []
        for fp, content in existing_contents.items():
            # Cap each file at 3000 chars to stay within token budget
            snippet = content[:3000] + ("...[truncated]" if len(content) > 3000 else "")
            context_parts.append(f"=== {fp} ===\n{snippet}")

        context_str = "\n\n".join(context_parts) if context_parts else "(no existing files — create new)"

        # Key files overview from plan (brief)
        plan_summary = (
            f"Task: {plan.summary[:200]}\n"
            f"Step {step_num}: {step_title}\n"
            f"Description: {description}\n"
            f"Target file: {target_file or 'determine from description'}\n"
            f"Change type: {change_type}"
        )

        user_prompt = (
            f"{plan_summary}\n\n"
            f"Existing file content:\n{context_str}\n\n"
            "Output JSON only: {\"file_path\": \"...\", \"content\": \"...\", \"explanation\": \"...\"}"
        )

        # Try models with fallback
        raw_output = None
        last_error = None
        for model in FALLBACK_MODELS:
            try:
                client = self.groq_provider._get_client()
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": DEVELOPER_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=2500,
                    response_format={"type": "json_object"},
                )
                raw_output = response.choices[0].message.content
                break
            except Exception as exc:
                last_error = str(exc)
                logger.warning(f"Developer Agent model {model} failed: {exc}")
                continue

        if not raw_output:
            return StepResult(
                step_number=step_num, step_title=step_title,
                file_path=target_file or "", change_type=change_type,
                success=False, explanation="", error=f"All models failed: {last_error}",
            )

        # Parse LLM output
        try:
            parsed = json.loads(raw_output)
            file_path = parsed.get("file_path", target_file or "").strip()
            content = parsed.get("content", "")
            explanation = parsed.get("explanation", "")
        except json.JSONDecodeError as exc:
            return StepResult(
                step_number=step_num, step_title=step_title,
                file_path=target_file or "", change_type=change_type,
                success=False, explanation="", error=f"JSON parse error: {exc}",
            )

        if not file_path or not content:
            return StepResult(
                step_number=step_num, step_title=step_title,
                file_path=file_path or "", change_type=change_type,
                success=False, explanation=explanation,
                error="LLM returned empty file_path or content.",
            )

        # Apply change via filesystem tools
        try:
            if change_type == "CREATE" and not fs.file_exists(file_path):
                result = fs.create_file(file_path, content)
            else:
                result = fs.upsert_file(file_path, content)

            if "error" in result:
                return StepResult(
                    step_number=step_num, step_title=step_title,
                    file_path=file_path, change_type=change_type,
                    success=False, explanation=explanation, error=result["error"],
                )

            # Rough diff accounting
            old_lines = len(existing_contents.get(file_path, "").splitlines())
            new_lines = len(content.splitlines())
            lines_added = max(0, new_lines - old_lines)
            lines_removed = max(0, old_lines - new_lines)

            return StepResult(
                step_number=step_num, step_title=step_title,
                file_path=file_path, change_type=result.get("status", change_type).upper(),
                success=True, explanation=explanation,
                lines_added=lines_added, lines_removed=lines_removed,
                diff_summary=f"+{lines_added} -{lines_removed} lines",
            )

        except FilesystemSecurityError as exc:
            return StepResult(
                step_number=step_num, step_title=step_title,
                file_path=file_path, change_type=change_type,
                success=False, explanation="", error=f"Security violation: {exc}",
            )
        except Exception as exc:
            return StepResult(
                step_number=step_num, step_title=step_title,
                file_path=file_path, change_type=change_type,
                success=False, explanation="", error=f"Unexpected error: {exc}",
            )

