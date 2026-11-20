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
- JSON schema for single-file step: {"file_path": "relative/path", "content": "<full file content as string>", "explanation": "<1 sentence>"}
- JSON schema for multi-file step: [{"file_path": "relative/path", "content": "<full file content as string>", "explanation": "<1 sentence>"}, ...]
- If a step lists multiple affected files, you MUST implement ALL of them and output a JSON array of file objects.
- Write the COMPLETE file content — not a diff, not a snippet.
- Respect existing code style, indentation, imports, and naming conventions.
- When importing packages, check existing package manifests (e.g. package.json dependencies like bcryptjs vs bcrypt) and import only packages installed in the project.
- NEVER require() or import any external third-party package (e.g. nodemailer, express-rate-limit, redis) that is not already listed in package.json. Implement lightweight in-memory implementations (e.g. JavaScript Map/Set) or built-in standard libraries instead.
- When modifying existing files, PRESERVE all existing routes, middleware, handlers, and exports unless explicitly asked to remove them. Never discard existing functionality.
- Ensure import paths and exported names match other modules exactly (e.g. if a controller exports requestPasswordReset, do not import forgotPassword).
- If the step creates a new file, write the full new file.
- explanation: 1 sentence max, describes what you did and why."""

FALLBACK_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]


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
        completed_step_numbers: Optional[set[int]] = None,
        feedback: Optional[str] = None,
    ) -> DeveloperResult:
        """Execute the full approved plan inside workspace_path.

        Args:
            plan: Approved ArchitectPlanOutput.
            workspace_path: Absolute path to cloned task workspace.
            progress_callback: Called with (current_step, total_steps, message) on each step.
            completed_step_numbers: Set of step numbers already successfully executed (for resume).
            feedback: Corrective feedback from QA or Code Review if in a retry cycle.

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
        completed_set = completed_step_numbers or set()

        for i, step in enumerate(steps, start=1):
            step_title = step.title if hasattr(step, "title") else f"Step {i}"

            # Idempotency check: skip already completed steps when resuming
            if i in completed_set:
                logger.info(f"Developer Agent — step {i}/{total} ({step_title}) already completed — skipping.")
                step_results.append(StepResult(
                    step_number=i,
                    step_title=step_title,
                    file_path=step.affected_files[0] if hasattr(step, "affected_files") and step.affected_files else "unknown",
                    change_type="PRESERVED",
                    success=True,
                    explanation=f"Step {i} was completed in previous execution frame.",
                ))
                continue

            logger.info(f"Developer Agent — step {i}/{total}: {step_title}")

            if progress_callback:
                progress_callback(i, total, f"Executing: {step_title}")

            result = await self._execute_step(step, plan, fs, i, feedback=feedback)
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
        feedback: Optional[str] = None,
    ) -> StepResult:
        """Run a single implementation step via LLM + filesystem tools."""
        step_title = step.title if hasattr(step, "title") else f"Step {step_num}"
        affected = step.affected_files if hasattr(step, "affected_files") and step.affected_files else []
        description = step.description if hasattr(step, "description") else str(step)
        target_file = affected[0] if affected else None

        # Read existing file contents for context (capped per file)
        existing_contents: Dict[str, str] = {}
        for fp in affected:
            read_result = fs.read_file(fp)
            if "content" in read_result:
                c = read_result["content"]
                existing_contents[fp] = c[:5000] if len(c) > 5000 else c

        # Context awareness: also include newly created controllers/services/models from this plan
        # so later steps (e.g. routes, frontend, tests) know the exact filenames and exported functions
        for fc in (plan.files_to_create or []):
            fc_path = getattr(fc, "path", None) or (fc.get("path") if isinstance(fc, dict) else None)
            if fc_path and fc_path != target_file and fc_path not in existing_contents:
                if fs.file_exists(fc_path):
                    read_result = fs.read_file(fc_path)
                    if "content" in read_result:
                        c = read_result["content"]
                        existing_contents[fc_path] = c[:2000] if len(c) > 2000 else c

        # Load package manifests in summary form (only dependency names) to save tokens
        for manifest_candidate in ["package.json", "backend/package.json", "frontend/package.json"]:
            if fs.file_exists(manifest_candidate):
                m_res = fs.read_file(manifest_candidate)
                if "content" in m_res:
                    try:
                        pdata = json.loads(m_res["content"])
                        dep_list = list(pdata.get("dependencies", {}).keys()) + list(pdata.get("devDependencies", {}).keys())
                        existing_contents[f"{manifest_candidate} (installed packages)"] = f"Installed packages: {', '.join(dep_list)}"
                    except Exception:
                        existing_contents[manifest_candidate] = m_res["content"][:1000]
                break

        # If feedback mentions specific files, load them into context as well (capped)
        if feedback:
            import re
            mentioned_files = re.findall(r"[\w\-\./\\]+\.(?:js|jsx|ts|tsx|py|json)", feedback)
            for mf in mentioned_files[:2]:
                for cand in [mf, f"backend/{mf}", f"frontend/{mf}"]:
                    if cand not in existing_contents and fs.file_exists(cand):
                        read_res = fs.read_file(cand)
                        if "content" in read_res:
                            c = read_res["content"]
                            existing_contents[cand] = c[:2000] if len(c) > 2000 else c
                            break

        # Check if file should be created or modified
        create_paths = {f.path for f in plan.files_to_create if hasattr(f, "path")}
        change_type = "CREATE" if target_file and target_file in create_paths else "MODIFY"

        # Build LLM prompt with strict overall budget to stay safely within Groq TPM limits
        context_parts = []
        total_chars = 0
        max_context_chars = 8000
        for fp, content in existing_contents.items():
            if total_chars + len(content) > max_context_chars:
                remaining = max(0, max_context_chars - total_chars)
                if remaining > 200:
                    context_parts.append(f"=== {fp} (summary) ===\n{content[:remaining]}")
                break
            context_parts.append(f"=== {fp} ===\n{content}")
            total_chars += len(content)

        context_str = "\n\n".join(context_parts) if context_parts else "(no existing files — create new)"

        # Instructions depending on single or multiple affected files
        if len(affected) > 1:
            files_desc = "\n".join(f"- {f}" for f in affected)
            step_target_info = (
                f"Affected files for this step ({len(affected)} files):\n{files_desc}\n"
                f"You MUST implement and output ALL of these affected files as a JSON array of objects: "
                f"[{{\"file_path\": \"...\", \"content\": \"...\", \"explanation\": \"...\"}}, ...]"
            )
        else:
            step_target_info = (
                f"Target file: {target_file or 'determine from description'}\n"
                f"Change type: {change_type}\n"
                f"Output JSON: {{\"file_path\": \"...\", \"content\": \"...\", \"explanation\": \"...\"}}"
            )

        # Key files overview from plan (brief)
        plan_summary = (
            f"Task: {plan.summary[:200]}\n"
            f"Step {step_num}: {step_title}\n"
            f"Description: {description}\n"
            f"{step_target_info}"
        )
        if feedback:
            feedback_excerpt = feedback[:1500] if len(feedback) > 1500 else feedback
            plan_summary += (
                f"\n\nCORRECTIVE FEEDBACK FROM QA / TESTS / REVIEW:\n{feedback_excerpt}\n"
                f"Please address and correct these exact issues in this step. Fix any broken imports, missing exports, or undefined callbacks. Never import uninstalled packages."
            )

        user_prompt = (
            f"{plan_summary}\n\n"
            f"Existing file content & dependencies:\n{context_str}\n\n"
            f"Generate the full file contents now in JSON format."
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
                    max_tokens=8192,
                    response_format={"type": "json_object"},
                )
                raw_output = response.choices[0].message.content
                break
            except Exception as exc:
                last_error = str(exc)
                logger.warning(f"Developer Agent model {model} failed: {exc}")
                # Resilient recovery: if Groq truncated JSON, check for failed_generation in error payload
                try:
                    err_body = getattr(exc, "body", None) or {}
                    if isinstance(err_body, dict):
                        failed_gen = err_body.get("error", {}).get("failed_generation")
                        if failed_gen:
                            try:
                                json.loads(failed_gen)
                                raw_output = failed_gen
                                break
                            except Exception:
                                for suffix in ['"}', '"}\n}', '"} }', '"}']:
                                    try:
                                        json.loads(failed_gen + suffix)
                                        raw_output = failed_gen + suffix
                                        break
                                    except Exception:
                                        pass
                                if raw_output:
                                    break
                except Exception:
                    pass
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
        except Exception as exc:
            return StepResult(
                step_number=step_num, step_title=step_title,
                file_path=target_file or "", change_type=change_type,
                success=False, explanation="", error=f"JSON parse error: {exc}",
            )

        # Normalize parsed output into a list of file items (handles dict, list of dicts, or dict with 'files'/'changes')
        items: List[Dict[str, Any]] = []
        if isinstance(parsed, list):
            items = [item for item in parsed if isinstance(item, dict)]
        elif isinstance(parsed, dict):
            if "files" in parsed and isinstance(parsed["files"], list):
                items = [item for item in parsed["files"] if isinstance(item, dict)]
            elif "changes" in parsed and isinstance(parsed["changes"], list):
                items = [item for item in parsed["changes"] if isinstance(item, dict)]
            else:
                items = [parsed]
        else:
            return StepResult(
                step_number=step_num, step_title=step_title,
                file_path=target_file or "", change_type=change_type,
                success=False, explanation="",
                error=f"Unexpected LLM output format: expected dict or list, got {type(parsed).__name__}",
            )

        if not items:
            return StepResult(
                step_number=step_num, step_title=step_title,
                file_path=target_file or "", change_type=change_type,
                success=False, explanation="",
                error="LLM output did not contain any valid file change objects.",
            )

        applied_paths: List[str] = []
        total_added = 0
        total_removed = 0
        explanations: List[str] = []

        for item in items:
            item_path = str(item.get("file_path") or item.get("path") or target_file or "").strip()
            item_content = item.get("content", "")
            item_exp = str(item.get("explanation") or "").strip()
            if item_exp:
                explanations.append(item_exp)

            if not item_path or not item_content:
                continue

            try:
                item_create = (change_type == "CREATE" and not fs.file_exists(item_path))
                if item_create:
                    res = fs.create_file(item_path, item_content)
                else:
                    res = fs.upsert_file(item_path, item_content)

                if "error" in res:
                    return StepResult(
                        step_number=step_num, step_title=step_title,
                        file_path=item_path, change_type=change_type,
                        success=False, explanation="; ".join(explanations), error=res["error"],
                    )

                applied_paths.append(item_path)
                old_lines = len(existing_contents.get(item_path, "").splitlines())
                new_lines = len(item_content.splitlines())
                total_added += max(0, new_lines - old_lines)
                total_removed += max(0, old_lines - new_lines)

            except FilesystemSecurityError as exc:
                return StepResult(
                    step_number=step_num, step_title=step_title,
                    file_path=item_path, change_type=change_type,
                    success=False, explanation="", error=f"Security violation: {exc}",
                )
            except Exception as exc:
                return StepResult(
                    step_number=step_num, step_title=step_title,
                    file_path=item_path, change_type=change_type,
                    success=False, explanation="", error=f"Unexpected error: {exc}",
                )

        if not applied_paths:
            return StepResult(
                step_number=step_num, step_title=step_title,
                file_path=target_file or "", change_type=change_type,
                success=False, explanation="; ".join(explanations),
                error="LLM returned empty file_path or content in all items.",
            )

        primary_path = applied_paths[0]
        combined_explanation = "; ".join(explanations) if explanations else f"Applied changes to {', '.join(applied_paths)}"

        return StepResult(
            step_number=step_num, step_title=step_title,
            file_path=primary_path, change_type=change_type,
            success=True, explanation=combined_explanation,
            lines_added=total_added, lines_removed=total_removed,
            diff_summary=f"+{total_added} -{total_removed} lines ({len(applied_paths)} file(s))",
        )

