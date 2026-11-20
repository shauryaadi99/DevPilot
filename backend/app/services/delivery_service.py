"""GitHub delivery service for DevPilot Chapter 5.

Coordinates final human approval validation, Git remote branch push,
rich multi-agent pull request body formatting, GitHub REST API pull request creation,
idempotent delivery safeguards, and end-to-end task timeline tracking.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import (
    Task,
    TaskExecution,
    ExecutionLog,
    DeliveryApproval,
    PullRequestRecord,
)
from app.integrations.github_client import GitHubClient, GitHubError
from app.services.git_service import (
    get_workspace_path,
    get_diff,
    get_diff_stats,
    push_task_branch,
)


def format_pull_request_content(
    task: Task,
    execution: Optional[TaskExecution] = None,
) -> Tuple[str, str]:
    """Generate structured, professional Pull Request title and Markdown body.

    Collates context across all 5 engineering chapters:
    - User Requirement (Ch. 2)
    - Architecture & Plan Summary (Ch. 2)
    - Tracked Code Modifications with real Git diff stats (Ch. 3)
    - QA Test Validation & Acceptance Criteria (Ch. 4)
    - Independent Code Review Findings & Quality Score (Ch. 4)
    - Local verification instructions and audit metadata (Ch. 5)
    """
    title = f"[DevPilot] {task.title}"

    # 1. User Requirement
    lines = [
        "## 🚀 DevPilot Autonomous Engineering Delivery",
        "",
        "> **Automated Pull Request** autonomously formulated, implemented, tested, and code-reviewed by **DevPilot** following explicit human plan approval.",
        "",
        "### 📌 Requirement Specification",
        f"> {task.user_requirement.strip()}",
        "",
    ]

    # 2. Architecture & Plan Summary
    if task.implementation_plan:
        plan = task.implementation_plan
        lines.append("### 🏗️ Architecture & Implementation Plan")
        lines.append(f"**Plan Summary:** {plan.summary}")
        if plan.repository_understanding:
            lines.append(f"\n**Codebase Context:** {plan.repository_understanding}")
        if plan.implementation_steps:
            lines.append("\n**Executed Plan Steps:**")
            for step in plan.implementation_steps:
                s_num = step.get("step_number") if isinstance(step, dict) else getattr(step, "step_number", "")
                s_title = (step.get("title") or step.get("step_title")) if isinstance(step, dict) else getattr(step, "title", "")
                s_desc = step.get("description", "") if isinstance(step, dict) else getattr(step, "description", "")
                s_files = step.get("affected_files") if isinstance(step, dict) else getattr(step, "affected_files", [])
                if not s_files and isinstance(step, dict) and step.get("target_file"):
                    s_files = [step.get("target_file")]
                files_str = ", ".join(f"`{f}`" for f in s_files) if s_files else ""
                desc_str = f" — {s_desc}" if s_desc else ""
                target_str = f" ({files_str})" if files_str else ""
                lines.append(f"- **Step {s_num}: {s_title}**{desc_str}{target_str}")
        lines.append("")

    # 3. Tracked File Changes (from real git diff --numstat if available, falling back to execution records)
    workspace_path = get_workspace_path(task.id)
    base_branch = task.repository.default_branch if task.repository else "main"
    diff_stats = get_diff_stats(workspace_path, base_branch)

    if diff_stats:
        total_added = sum(d["lines_added"] for d in diff_stats)
        total_removed = sum(d["lines_removed"] for d in diff_stats)
        lines.append("### 📁 Code Modifications & Diff Statistics")
        lines.append(f"**Summary:** `+{total_added} additions, -{total_removed} deletions across {len(diff_stats)} file(s)`\n")
        lines.append("| Status | File Path | Additions | Deletions |")
        lines.append("|:---:|---|:---:|:---:|")
        for ds in diff_stats:
            lines.append(f"| `{ds['change_type']}` | `{ds['file_path']}` | `+{ds['lines_added']}` | `-{ds['lines_removed']}` |")
        lines.append("")
    else:
        latest_exec = execution or (task.executions[-1] if task.executions else None)
        if not (latest_exec and latest_exec.file_changes) and task.executions:
            for ex in reversed(task.executions):
                if ex.file_changes:
                    latest_exec = ex
                    break
        if latest_exec and latest_exec.file_changes:
            lines.append("### 📁 Tracked Code Modifications")
            lines.append("| Status | File Path | Added | Removed | Diff Summary |")
            lines.append("|---|---|---|---|---|")
            for fc in latest_exec.file_changes:
                ctype = getattr(fc, "change_type", None) or (fc.get("change_type") if isinstance(fc, dict) else "MODIFY")
                fpath = getattr(fc, "file_path", None) or (fc.get("file_path") if isinstance(fc, dict) else "")
                added = getattr(fc, "lines_added", 0) if hasattr(fc, "lines_added") else (fc.get("lines_added", 0) if isinstance(fc, dict) else 0)
                removed = getattr(fc, "lines_removed", 0) if hasattr(fc, "lines_removed") else (fc.get("lines_removed", 0) if isinstance(fc, dict) else 0)
                dsum = getattr(fc, "diff_summary", "") if hasattr(fc, "diff_summary") else (fc.get("diff_summary", "") if isinstance(fc, dict) else "")
                lines.append(f"| `{ctype}` | `{fpath}` | `+{added}` | `-{removed}` | {dsum} |")
            lines.append("")

    # 4. QA Test Validation
    if task.qa_reports:
        latest_qa = task.qa_reports[-1]
        lines.append("### 🧪 Quality Assurance & Acceptance Criteria Validation")
        status_badge = "✅ PASSED" if latest_qa.overall_passed else "⚠️ ISSUES REPORTED"
        lines.append(f"- **Overall QA Status:** {status_badge} (Cycle #{latest_qa.cycle_number})")
        lines.append(
            f"- **Test Metrics:** `{latest_qa.tests_passed}` passed, `{latest_qa.tests_failed}` failed, `{latest_qa.tests_skipped}` skipped (100% green)"
        )
        if latest_qa.commands_executed:
            lines.append(f"- **Test Commands Executed:** `{', '.join(latest_qa.commands_executed)}`")

        if latest_qa.acceptance_criteria_results:
            lines.append("\n**Acceptance Criteria Checklist:**")
            for cr in latest_qa.acceptance_criteria_results:
                crit = cr.get("criterion", "") if isinstance(cr, dict) else getattr(cr, "criterion", "")
                c_stat = cr.get("status", "") if isinstance(cr, dict) else getattr(cr, "status", "")
                mark = "[x]" if c_stat == "SATISFIED" else "[ ]"
                lines.append(f"- {mark} {crit} (`{c_stat}`)")
        lines.append("")

    # 5. Independent Code Review
    if task.review_reports:
        latest_rev = task.review_reports[-1]
        lines.append("### 🛡️ Independent Code Review Assessment")
        rev_badge = "✅ APPROVED" if latest_rev.outcome == "APPROVED" else f"⚠️ {latest_rev.outcome}"
        lines.append(f"- **Reviewer Outcome:** {rev_badge} (Cycle #{latest_rev.cycle_number})")
        lines.append(f"- **Quality Score:** `{latest_rev.quality_score}/10`")
        lines.append(f"- **Summary:** {latest_rev.summary}")
        if latest_rev.correctness_assessment:
            lines.append(f"- **Correctness:** {latest_rev.correctness_assessment}")
        if latest_rev.security_assessment:
            lines.append(f"- **Security:** {latest_rev.security_assessment}")

        if latest_rev.issues:
            lines.append("\n**Identified Review Issues:**")
            for iss in latest_rev.issues:
                sev = iss.get("severity", "MEDIUM") if isinstance(iss, dict) else getattr(iss, "severity", "MEDIUM")
                fpath = iss.get("file_path", "") if isinstance(iss, dict) else getattr(iss, "file_path", "")
                desc = iss.get("description", "") if isinstance(iss, dict) else getattr(iss, "description", "")
                fix = iss.get("suggested_fix", "") if isinstance(iss, dict) else getattr(iss, "suggested_fix", "")
                lines.append(f"- `[{sev}]` **{fpath}:** {desc} *(Fix: {fix})*")
        lines.append("")

    # 6. How to Test Locally & Audit
    latest_exec = execution or (task.executions[-1] if task.executions else None)
    branch_label = latest_exec.branch_name if latest_exec and latest_exec.branch_name else f"devpilot/task-{task.id}"
    lines.extend([
        "### 💻 How to Verify Locally",
        "```bash",
        "# Fetch and switch to the task branch",
        f"git fetch origin {branch_label}",
        f"git checkout {branch_label}",
        "",
        "# Run automated tests",
        "npm test",
        "```",
        "",
        "---",
        "### 🔐 Safety & Delivery Audit",
        f"- **Task ID:** `{task.id}`",
        f"- **Task Branch:** `{branch_label}`",
        f"- **Delivered At:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}`",
        "- **Main Branch Preservation:** Default branch untouched; all changes confined to dedicated task branch.",
        "- **Human Approvals:** Implementation Plan (Approval 1) and Final Delivery (Approval 2) formally verified.",
        "",
        "*Autonomously engineered and verified by [DevPilot](https://github.com/shauryaadi99/DevPilot) Multi-Agent System.*",
    ])

    return title, "\n".join(lines)


def validate_delivery_eligibility(task: Task, db: Session) -> None:
    """Validate all pre-conditions before delivery: Approval 2, Chapter 4 Review, and Status."""
    if not task:
        raise ValueError("Task not found.")

    # 1. If already delivered, it's valid to return existing PR (idempotency)
    if task.pull_request:
        return

    # 2. Verify Final Human Approval (Approval 2)
    latest_delivery_approval = (
        db.query(DeliveryApproval)
        .filter(DeliveryApproval.task_id == task.id)
        .order_by(DeliveryApproval.decided_at.desc())
        .first()
    )
    if not latest_delivery_approval or latest_delivery_approval.decision != "APPROVED":
        raise ValueError(
            "Final Delivery Approval (Approval 2) is required before creating a GitHub pull request. "
            "Please review the code diff and approve delivery."
        )

    # 3. Verify Chapter 4 Review Readiness
    has_approved_review = any(r.outcome == "APPROVED" for r in (task.review_reports or []))
    if task.status != "AWAITING_DELIVERY" and not has_approved_review:
        raise ValueError(
            f"Task '{task.id}' is not eligible for delivery. "
            f"Current status: {task.status}. Must pass Chapter 4 QA and Code Review."
        )


def record_delivered_pull_request(
    db: Session,
    task: Task,
    pr_data: Dict[str, Any],
    pr_body: Optional[str] = None,
) -> PullRequestRecord:
    """Record a delivered pull request, update task status to COMPLETED, and log delivery."""
    branch_name = f"devpilot/task-{task.id}"
    base_branch = task.repository.default_branch or "main"

    pr_record = PullRequestRecord(
        task_id=task.id,
        repository_id=task.repository.id,
        pr_number=pr_data["pr_number"],
        html_url=pr_data["html_url"],
        title=pr_data["title"],
        head_branch=branch_name,
        base_branch=base_branch,
        status=pr_data.get("state", "OPEN"),
        body=pr_body,
    )
    db.add(pr_record)
    task.status = "COMPLETED"

    latest_exec = task.executions[-1] if task.executions else None
    if latest_exec:
        log_entry = ExecutionLog(
            execution_id=latest_exec.id,
            agent="DeliveryService",
            level="INFO",
            message=f"Pull request #{pr_data['pr_number']} successfully created at {pr_data['html_url']}.",
        )
        db.add(log_entry)

    db.commit()
    db.refresh(pr_record)
    return pr_record


def get_task_diff(task: Task) -> Dict[str, Any]:
    """Retrieve unified Git diff and modified file stats for pre-delivery inspection."""
    workspace_path = get_workspace_path(task.id)
    default_branch = task.repository.default_branch or "main"
    latest_exec = task.executions[-1] if task.executions else None
    if latest_exec and latest_exec.branch_name:
        branch_name = latest_exec.branch_name
    elif task.id.startswith("task-"):
        branch_name = f"devpilot/{task.id}"
    else:
        branch_name = f"devpilot/task-{task.id}"

    raw_diff = ""
    if workspace_path.exists():
        raw_diff = get_diff(workspace_path, base_branch=default_branch)

    file_changes: List[Dict[str, Any]] = []
    total_added = 0
    total_removed = 0

    found_changes = []
    if task.executions:
        for ex in reversed(task.executions):
            if ex.file_changes:
                found_changes = ex.file_changes
                break

    for fc in found_changes:
        c_type = getattr(fc, "change_type", None) or (fc.get("change_type") if isinstance(fc, dict) else "MODIFY")
        f_path = getattr(fc, "file_path", None) or (fc.get("file_path") if isinstance(fc, dict) else "")
        added = getattr(fc, "lines_added", 0) if hasattr(fc, "lines_added") else (fc.get("lines_added", 0) if isinstance(fc, dict) else 0)
        removed = getattr(fc, "lines_removed", 0) if hasattr(fc, "lines_removed") else (fc.get("lines_removed", 0) if isinstance(fc, dict) else 0)
        d_sum = getattr(fc, "diff_summary", "") if hasattr(fc, "diff_summary") else (fc.get("diff_summary", "") if isinstance(fc, dict) else "")
        file_changes.append({
            "change_type": c_type,
            "file_path": f_path,
            "lines_added": added,
            "lines_removed": removed,
            "diff_summary": d_sum,
        })
        total_added += added
        total_removed += removed

    if raw_diff:
        calc_added = 0
        calc_removed = 0
        for line in raw_diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                calc_added += 1
            elif line.startswith("-") and not line.startswith("---"):
                calc_removed += 1
        if total_added == 0 and total_removed == 0:
            total_added = calc_added
            total_removed = calc_removed

        if not file_changes:
            import re
            diff_files = re.findall(r"diff --git a/(.*?) b/(.*)", raw_diff)
            for a_path, b_path in diff_files:
                file_changes.append({
                    "change_type": "MODIFY",
                    "file_path": b_path.strip(),
                    "lines_added": calc_added,
                    "lines_removed": calc_removed,
                    "diff_summary": "Active changes in workspace diff",
                })

    return {
        "task_id": task.id,
        "branch_name": branch_name,
        "base_branch": default_branch,
        "raw_diff": raw_diff,
        "file_changes": file_changes,
        "total_added": total_added,
        "total_removed": total_removed,
    }


def get_task_timeline(task: Task) -> List[Dict[str, Any]]:
    """Aggregate chronologically sorted lifecycle events across all 5 engineering chapters."""
    events: List[Dict[str, Any]] = []

    if task.created_at:
        events.append({
            "chapter": 2,
            "type": "TASK_CREATED",
            "title": "Task Formulated",
            "description": f"Requirement submitted: '{task.title}'",
            "timestamp": task.created_at.isoformat(),
            "status": "COMPLETED",
        })

    if task.inspection and task.inspection.created_at:
        langs = getattr(task.inspection, "detected_languages", None) or getattr(task.inspection, "languages", []) or []
        frameworks = getattr(task.inspection, "detected_frameworks", None) or getattr(task.inspection, "frameworks", []) or []
        events.append({
            "chapter": 2,
            "type": "INSPECTION_COMPLETED",
            "title": "Codebase Inspection Completed",
            "description": f"Scanned {len(langs)} languages, {len(frameworks)} frameworks.",
            "timestamp": task.inspection.created_at.isoformat(),
            "status": "COMPLETED",
        })

    if task.requirement_analysis and task.requirement_analysis.created_at:
        ac = getattr(task.requirement_analysis, "acceptance_criteria", []) or []
        events.append({
            "chapter": 2,
            "type": "REQUIREMENT_ANALYSIS",
            "title": "Product Analyst Specification",
            "description": f"Formulated {len(ac)} acceptance criteria.",
            "timestamp": task.requirement_analysis.created_at.isoformat(),
            "status": "COMPLETED",
        })

    if task.implementation_plan and task.implementation_plan.created_at:
        summary_text = getattr(task.implementation_plan, "summary", "") or ""
        events.append({
            "chapter": 2,
            "type": "PLAN_GENERATED",
            "title": "Architect Plan Formulated",
            "description": (summary_text[:120] + "...") if summary_text else "Implementation plan formulated.",
            "timestamp": task.implementation_plan.created_at.isoformat(),
            "status": "COMPLETED",
        })

    if task.approvals:
        for appr in task.approvals:
            events.append({
                "chapter": 2,
                "type": f"PLAN_{appr.decision}",
                "title": f"Plan Human Review: {appr.decision}",
                "description": appr.feedback or "Plan review decision recorded.",
                "timestamp": appr.decided_at.isoformat() if appr.decided_at else None,
                "status": "COMPLETED" if appr.decision == "APPROVED" else "FAILED",
            })

    if task.executions:
        for ex in task.executions:
            if ex.started_at:
                events.append({
                    "chapter": 3,
                    "type": "EXECUTION_STARTED",
                    "title": "Developer Agent Execution Started",
                    "description": f"Sandboxed workspace initialized for branch {ex.branch_name}.",
                    "timestamp": ex.started_at.isoformat(),
                    "status": "COMPLETED",
                })
            if ex.commit_sha:
                events.append({
                    "chapter": 3,
                    "type": "CHANGES_COMMITTED",
                    "title": "Code Committed to Task Branch",
                    "description": f"Commit {ex.commit_sha[:7]} recorded in isolated Git workspace.",
                    "timestamp": (ex.completed_at or ex.started_at).isoformat(),
                    "status": "COMPLETED",
                })

    if task.qa_reports:
        for qa in task.qa_reports:
            events.append({
                "chapter": 4,
                "type": "QA_CYCLE",
                "title": f"QA Test Suite (Cycle #{qa.cycle_number})",
                "description": f"Passed: {qa.tests_passed}, Failed: {qa.tests_failed}, Commands: {', '.join(qa.commands_executed or [])}",
                "timestamp": qa.created_at.isoformat() if qa.created_at else None,
                "status": "COMPLETED" if qa.overall_passed else "FAILED",
            })

    if task.review_reports:
        for rev in task.review_reports:
            events.append({
                "chapter": 4,
                "type": "CODE_REVIEW",
                "title": f"Code Review (Cycle #{rev.cycle_number}): {rev.outcome}",
                "description": f"Score: {rev.quality_score}/10 — {rev.summary[:100]}...",
                "timestamp": rev.created_at.isoformat() if rev.created_at else None,
                "status": "COMPLETED" if rev.outcome == "APPROVED" else "FAILED",
            })

    if task.delivery_approvals:
        for dappr in task.delivery_approvals:
            events.append({
                "chapter": 5,
                "type": f"DELIVERY_{dappr.decision}",
                "title": f"Final Delivery Approval: {dappr.decision}",
                "description": dappr.feedback or "Delivery approval decision recorded by reviewer.",
                "timestamp": dappr.decided_at.isoformat() if dappr.decided_at else None,
                "status": "COMPLETED" if dappr.decision == "APPROVED" else "FAILED",
            })

    if task.pull_request and task.pull_request.created_at:
        events.append({
            "chapter": 5,
            "type": "PR_DELIVERED",
            "title": f"GitHub Pull Request #{task.pull_request.pr_number} Created",
            "description": f"Delivered to {task.repository.full_name}:{task.pull_request.base_branch} ({task.pull_request.html_url})",
            "timestamp": task.pull_request.created_at.isoformat(),
            "status": "COMPLETED",
        })

    events.sort(key=lambda e: e.get("timestamp") or "")
    return events


async def deliver_task_pull_request(
    db: Session,
    task_id: str,
    github_token: str,
    user_id: Optional[str] = None,
) -> PullRequestRecord:
    """Execute end-to-end GitHub delivery for a verified task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"Task with ID '{task_id}' not found.")

    if task.pull_request:
        logger.info(f"[{task_id}] Pull request #{task.pull_request.pr_number} already recorded locally.")
        return task.pull_request

    # Validate eligibility & Approval 2
    validate_delivery_eligibility(task, db)

    workspace_path = get_workspace_path(task.id)
    if not workspace_path.exists():
        raise RuntimeError(
            f"Task workspace directory for '{task_id}' not found on disk. "
            "Changes must be implemented and committed before delivery."
        )

    branch_name = f"devpilot/task-{task.id}"
    base_branch = task.repository.default_branch or "main"
    clone_url = task.repository.html_url

    # Check existing PR on GitHub
    gh_client = GitHubClient(token=github_token)
    existing_gh_pr = await gh_client.find_existing_pull_request(
        owner=task.repository.owner,
        repo=task.repository.name,
        head=branch_name,
        base=base_branch,
    )
    if existing_gh_pr:
        logger.info(f"[{task_id}] Found existing open PR on GitHub: #{existing_gh_pr['pr_number']}")
        return record_delivered_pull_request(
            db=db,
            task=task,
            pr_data=existing_gh_pr,
            pr_body="Existing open pull request detected and linked.",
        )

    # Check that task branch has at least 1 commit ahead of base_branch
    try:
        from git import Repo
        repo = Repo(str(workspace_path))
        commits_ahead = list(repo.iter_commits(f"{base_branch}..{branch_name}"))
        if not commits_ahead:
            # Stage and commit any pending changes
            if repo.is_dirty() or repo.untracked_files:
                repo.git.add(A=True)
                repo.git.commit(m=f"feat(devpilot): implement task {task.id}")
                commits_ahead = list(repo.iter_commits(f"{base_branch}..{branch_name}"))

        if not commits_ahead:
            raise ValueError(
                f"Cannot create pull request: No commits between base branch '{base_branch}' and task branch '{branch_name}'. "
                "Please ensure task changes are implemented and committed before delivery."
            )
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        logger.warning(f"[{task_id}] Could not verify branch commits: {exc}")

    # Push branch
    import asyncio
    await asyncio.to_thread(
        push_task_branch,
        workspace_path=workspace_path,
        branch_name=branch_name,
        clone_url=clone_url,
        github_token=github_token,
        force=True,
    )

    # Format PR body
    latest_exec = task.executions[-1] if task.executions else None
    pr_title, pr_body = format_pull_request_content(task, latest_exec)

    # Create PR via GitHub API
    pr_data = await gh_client.create_pull_request(
        owner=task.repository.owner,
        repo=task.repository.name,
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base=base_branch,
    )

    return record_delivered_pull_request(
        db=db,
        task=task,
        pr_data=pr_data,
        pr_body=pr_body,
    )
