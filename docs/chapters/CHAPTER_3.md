# CHAPTER 3 — AUTONOMOUS DEVELOPMENT ENGINE

**Project:** DevPilot  
**Chapter:** 3 of 5  
**Status:** NOT STARTED  
**Depends on:** Chapters 1 and 2

---

## 1. OBJECTIVE

Enable DevPilot to implement an approved software engineering plan inside an isolated repository workspace.

At the end of this chapter, DevPilot should be capable of taking an approved plan and making actual code changes without modifying the repository's main branch.

The Developer Agent is introduced in this chapter.

## 2. CORE REQUIREMENTS

### 2.1 Approved-plan enforcement

The Developer Agent must only execute a plan that has been approved.

Before execution, verify:
- Task exists.
- Repository is correctly associated with the task.
- Plan exists.
- Plan approval is recorded.
- Task is not cancelled.
- Execution permissions are valid.

Do not rely on frontend-only approval checks.

Enforce approval on the backend.

### 2.2 Git workspace management

Implement controlled Git operations.

Required capabilities:
- Clone or prepare repository workspace.
- Inspect current branch.
- Create task-specific branches.
- Check working tree status.
- Read diffs.
- Stage changes where required.
- Commit changes when authorized by workflow.

Use a predictable task branch naming convention.

Never directly modify the main or default branch.

### 2.3 Developer Agent

Responsibilities:
- Interpret approved implementation steps.
- Identify required files.
- Read relevant files before modification.
- Make focused changes.
- Create new files when necessary.
- Update existing files carefully.
- Explain modifications.
- Report implementation progress.

The Developer must not arbitrarily change the approved plan.

If implementation requires a substantial deviation:
- Stop.
- Explain the issue.
- Present the proposed alternative.
- Obtain approval where necessary.

### 2.4 Filesystem tools

Provide restricted tools for:
- Listing directories.
- Reading files.
- Creating files.
- Editing files.
- Deleting files.
- Inspecting changes.

Each tool must validate paths.

Prevent:
- Directory traversal.
- Access outside the task workspace.
- Accidental modification of protected files.
- Unrestricted filesystem access.

### 2.5 Execution sandbox

Generated or repository-provided code must not execute directly on the DevPilot application server.

Implement isolated execution using an appropriately secured sandbox.

Consider:
- Container isolation.
- CPU and memory limits.
- Execution timeouts.
- Restricted filesystem access.
- Network restrictions.
- No inherited application secrets.
- Process cleanup.
- Workspace isolation.

Do not assume a basic Docker container alone guarantees complete security.

Document the threat model and known limitations.

### 2.6 Change tracking

Record:
- Files created.
- Files modified.
- Files deleted.
- Relevant diffs.
- Developer Agent execution status.
- Tool execution outcomes.
- Task branch.
- Implementation errors.

Maintain enough information to understand what changed and why.

### 2.7 Workflow orchestration

Introduce LangGraph if approved as the orchestration framework.

The workflow must support:
- Shared task state.
- Agent execution.
- Tool invocation.
- Conditional routing.
- Error handling.
- Checkpointing.
- Interruptions for human approval.

Do not let agents operate as independent, uncontrolled loops.

## 3. DEVELOPER AGENT TOOL POLICY

The Developer Agent must only use explicitly granted tools.

Every tool must:
- Validate input.
- Enforce workspace boundaries.
- Return structured results.
- Handle errors.
- Record important actions.

Destructive actions must have stricter validation.

Never allow arbitrary unrestricted shell access from the LLM.

## 4. IMPLEMENTATION SEQUENCE

1. Inspect existing Chapter 1 and 2 implementations.
2. Review approved architecture and plan schemas.
3. Design task workspace management.
4. Implement task-specific Git branches.
5. Implement restricted filesystem tools.
6. Implement Developer Agent.
7. Integrate the orchestration workflow.
8. Add isolated execution infrastructure.
9. Implement progress and change tracking.
10. Test normal, failure and cancellation scenarios.
11. Update architecture documentation.

## 5. FAILURE HANDLING

Handle:
- Repository clone failures.
- Missing files.
- Invalid paths.
- Git conflicts.
- Permission failures.
- Groq API failures.
- Malformed agent output.
- Tool execution failures.
- Sandbox timeouts.
- Resource exhaustion.
- Task cancellation.

Do not silently ignore failures.

A failed operation must be reported accurately.

## 6. OUT OF SCOPE

Do not implement:
- Full QA retry workflow.
- Code Reviewer Agent.
- Final PR creation.
- Production deployment.
- Unlimited autonomous retries.

These belong to later chapters.

## 7. ACCEPTANCE CRITERIA

- [ ] Approved plans can be executed.
- [ ] Unapproved plans are rejected by the backend.
- [ ] Task-specific Git branches are created.
- [ ] Main branch remains untouched.
- [ ] Developer Agent can read repository files.
- [ ] Developer Agent can create and edit files.
- [ ] Filesystem access is restricted.
- [ ] Changes are tracked.
- [ ] Execution is isolated.
- [ ] Timeouts and resource limits work.
- [ ] Failures are reported accurately.
- [ ] Task cancellation is handled safely.
- [ ] Tests verify branch isolation and workspace security.

## 8. REQUIRED FINAL REPORT

Report:
- Git integration design.
- Developer Agent responsibilities.
- Available tools.
- Filesystem security.
- Sandbox implementation and limitations.
- Workflow orchestration.
- Files modified.
- Tests executed.
- Actual test results.
- Remaining risks.
- Acceptance criteria status.

---

**END OF CHAPTER 3 SPECIFICATION**