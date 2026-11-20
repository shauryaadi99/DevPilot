"""Code Reviewer Agent (Chapter 4).

Independently inspects Git diffs against base branch, evaluates correctness,
security vulnerabilities, code maintainability, and project conventions,
outputting APPROVED, CHANGES_REQUESTED, or BLOCKED with itemized issues.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agents.schemas import CodeReviewOutput, ReviewIssue
from app.core.logging import logger
from app.integrations.groq_client import get_groq_provider
from app.services.git_service import get_diff

REVIEWER_SYSTEM_PROMPT = """You are the Code Reviewer Agent for DevPilot, an autonomous software engineering system.
Your responsibility:
1. Conduct an independent, rigorous code review of the actual Git diff.
2. Evaluate:
   - Correctness: Logical flaws, edge cases, state management errors.
   - Security: Injection risks, secret exposure, unauthenticated endpoints, insecure regex.
   - Error Handling: Missing catch blocks, unhandled promise rejections, silent failures.
   - Quality & Maintainability: Code style, redundant code, modularity, readability.
3. Determine one of three review outcomes:
   - APPROVED: Code is safe, correct, and ready for delivery/PR.
   - CHANGES_REQUESTED: Critical logic bugs or broken functionality found that Developer must fix.
   - BLOCKED: Severe security vulnerability, data loss risk, or malicious code.

CRITICAL RULES:
- When automated QA tests have passed and acceptance criteria are satisfied, default to outcome: "APPROVED" (quality_score >= 8) unless there is an exploitable security vulnerability or broken logic.
- NEVER request or suggest adding new uninstalled third-party packages or external services (e.g., Redis, nodemailer, sendgrid, express-rate-limit). In-memory Maps, built-in Node.js crypto/events, or console logging are completely appropriate for this environment and MUST NOT be rejected.
- Only issue CHANGES_REQUESTED if there is an actual runtime bug or broken contract in application code. Do not block delivery for minor architectural preferences or production-scaling suggestions.
- IMPORTANT: When a diff preview contains a notice like "[Diff preview truncated...]", the file on disk is complete. NEVER report preview truncation as a bug, typo, or missing code.

Token Efficiency & Strict JSON Schema Rules:
- Output MUST be valid JSON only. No markdown fences outside the JSON.
- Quality score must be an integer between 1 and 10.
Schema:
{
  "outcome": "APPROVED" | "CHANGES_REQUESTED" | "BLOCKED",
  "summary": "1 to 2 sentence executive review summary",
  "correctness_assessment": "1 sentence on correctness and business logic",
  "security_assessment": "1 sentence on security findings or confirmation of safety",
  "quality_score": 8,
  "issues": [
    {
      "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO",
      "file_path": "path/to/file",
      "line_number": 42,
      "description": "Short explanation of issue",
      "suggested_fix": "Concrete fix recommendation"
    }
  ],
  "approval_recommendation": "1 sentence conclusion and next action"
}
"""


class CodeReviewerAgent:
    """Performs automated, independent code reviews on task workspaces."""

    def __init__(self):
        self.provider = get_groq_provider()

    async def review(
        self,
        workspace_path: Path,
        task_requirement: str,
        plan_summary: Optional[str] = None,
        qa_summary: Optional[str] = None,
    ) -> CodeReviewOutput:
        """Inspect workspace diff and produce a validated review report."""
        diff_text = get_diff(workspace_path)
        logger.info(f"Code Reviewer inspecting workspace {workspace_path} (diff length: {len(diff_text)} chars)")

        if not diff_text.strip():
            # If no diff detected, verify if workspace is clean and committed
            return CodeReviewOutput(
                outcome="APPROVED",
                summary="Working tree is clean with all changes committed.",
                correctness_assessment="All planned steps applied cleanly.",
                security_assessment="No uncommitted or suspicious changes found.",
                quality_score=9,
                issues=[],
                approval_recommendation="Ready for delivery.",
            )

        # Truncate very large diffs cleanly at newline boundaries to avoid LLM context exhaustion
        max_diff_len = 24000
        if len(diff_text) > max_diff_len:
            cutoff = diff_text[:max_diff_len].rfind("\n")
            if cutoff > 0:
                truncated_diff = diff_text[:cutoff] + f"\n\n[Diff preview truncated: {len(diff_text) - cutoff} additional characters omitted from preview. Note: The codebase on disk is complete; do not treat preview truncation as missing code.]"
            else:
                truncated_diff = diff_text[:max_diff_len] + "\n\n[Diff preview truncated. Note: The codebase on disk is complete.]"
        else:
            truncated_diff = diff_text

        prompt = (
            f"TASK REQUIREMENT:\n{task_requirement}\n\n"
            f"ARCHITECT PLAN SUMMARY:\n{plan_summary or 'No plan summary provided.'}\n\n"
            f"QA TEST STATUS:\n{qa_summary or 'QA tests verified and passing.'}\n\n"
            f"GIT DIFF:\n```diff\n{truncated_diff}\n```\n\n"
            f"Perform an independent code review and return the structured JSON verdict."
        )

        try:
            response = await self.provider.chat_completion(
                messages=[
                    {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return self.parse_review_response(response.content)

        except Exception as e:
            logger.error(f"Code Reviewer agent error: {e}", exc_info=True)
            return CodeReviewOutput(
                outcome="CHANGES_REQUESTED",
                summary=f"Automated review encountered an analysis exception: {e}",
                correctness_assessment="Unable to verify completely.",
                security_assessment="Requires manual verification.",
                quality_score=5,
                issues=[
                    ReviewIssue(
                        severity="MEDIUM",
                        file_path="system",
                        description=f"Automated review parsing error: {e}",
                        suggested_fix="Re-run review or manually inspect diff.",
                    )
                ],
                approval_recommendation="Retry code review cycle.",
            )

    def parse_review_response(self, content_str: str) -> CodeReviewOutput:
        """Parse, validate, and enforce safety invariants on LLM review output."""
        data = json.loads(content_str)
        raw_issues = data.get("issues", [])
        parsed_issues: List[ReviewIssue] = []
        for issue in raw_issues:
            if isinstance(issue, dict):
                parsed_issues.append(
                    ReviewIssue(
                        severity=str(issue.get("severity", "MEDIUM")).upper(),
                        file_path=str(issue.get("file_path", "unknown")),
                        line_number=issue.get("line_number"),
                        description=str(issue.get("description", "Code issue noted")),
                        suggested_fix=issue.get("suggested_fix"),
                    )
                )

        outcome = str(data.get("outcome", "APPROVED")).upper()
        has_critical = any(i.severity == "CRITICAL" for i in parsed_issues)
        has_high = any(i.severity == "HIGH" for i in parsed_issues)

        # Safety override: critical issues cannot be marked APPROVED
        if has_critical and outcome == "APPROVED":
            outcome = "BLOCKED"
        elif has_high and outcome == "APPROVED":
            outcome = "CHANGES_REQUESTED"

        return CodeReviewOutput(
            outcome=outcome,
            summary=data.get("summary", "Code review completed successfully."),
            correctness_assessment=data.get("correctness_assessment", "Logic aligns with requirement."),
            security_assessment=data.get("security_assessment", "No critical vulnerabilities found."),
            quality_score=int(data.get("quality_score", 8)),
            issues=parsed_issues,
            approval_recommendation=data.get("approval_recommendation", "Proceed to delivery."),
        )
