# CHAPTER 4 — QA, CODE REVIEW AND RECOVERY

**Project:** DevPilot  
**Chapter:** 4 of 5  
**Status:** COMPLETED  
**Depends on:** Chapters 1, 2 and 3

---

## 1. OBJECTIVE

Introduce automated quality assurance, code review and controlled recovery mechanisms.

DevPilot must be able to evaluate its own implementation, identify failures, request corrections and stop safely when it cannot make meaningful progress.

This chapter introduces:
- QA Engineer Agent.
- Code Reviewer Agent.

## 2. QA ENGINEER AGENT

### Responsibilities

The QA Agent must:
- Understand task acceptance criteria.
- Identify relevant test commands.
- Execute approved tests within the isolated workspace.
- Inspect test results.
- Identify failing tests.
- Analyze relevant logs.
- Report reproducible failures where possible.
- Provide structured feedback to the Developer.

### Test categories

Support appropriate tests based on the repository:

- Unit tests.
- Integration tests.
- Build checks.
- Linting.
- Type checking.
- Relevant acceptance tests.

Do not assume every repository uses the same test framework.

### QA output

Produce a structured report containing:
- Task ID.
- Test execution ID.
- Commands executed.
- Tests passed.
- Tests failed.
- Tests skipped.
- Exit codes.
- Relevant logs.
- Failure summaries.
- Acceptance criteria status.

Never fabricate successful test results.

## 3. DEVELOPER-QA FEEDBACK LOOP

Implement a controlled feedback loop:

```text
Developer
    |
    v
QA Engineer
    |
    +---- PASS ----> Code Reviewer
    |
    +---- FAIL ----> Failure Analysis
                         |
                         v
                     Developer
                         |
                         v
                        QA
```

### Retry policy

Use a configurable retry limit.

Recommended initial default: maximum 3 Developer-QA cycles.

This is a starting policy and must remain configurable.

### Repeated-failure detection

Track:
- Failure signatures.
- Relevant error messages.
- Affected files.
- Previous fixes.
- Test results.
- Whether the failure changed or disappeared.

If the same failure repeatedly occurs without meaningful improvement, stop early.

Do not treat every failure as identical merely because the overall test suite remains unsuccessful.

### Retry exhaustion

When the retry limit is reached:
- Stop automatic execution.
- Preserve the current task branch.
- Preserve logs and diffs.
- Generate a failure report.
- Explain what was attempted.
- Explain what remains unresolved.
- Offer the user a controlled decision to continue or stop.

Do not silently discard changes.

## 4. CODE REVIEWER AGENT

### Responsibilities

The Reviewer must independently examine the implemented changes.

Review:
- Correctness.
- Potential bugs.
- Security concerns.
- Error handling.
- Code quality.
- Maintainability.
- Existing project conventions.
- Unnecessary changes.
- Acceptance criteria coverage.

### Reviewer independence

The Reviewer must not blindly trust the Developer's explanation.

It must inspect the actual diff and relevant surrounding code.

### Review outcomes

The Reviewer may return:

1. APPROVED
2. CHANGES_REQUESTED
3. BLOCKED

Each result must contain supporting explanations.

### Review feedback loop

If changes are requested:

```text
Code Reviewer
      |
      v
Changes Requested
      |
      v
Developer
      |
      v
QA
      |
      v
Code Reviewer
```

Use bounded retries for review corrections too.

Do not allow an unlimited Developer-Reviewer cycle.

## 5. LANGGRAPH WORKFLOW

Use the approved orchestration architecture to coordinate:
- Developer.
- QA Engineer.
- Code Reviewer.

Persist relevant state, including:
- Retry counters.
- Failure history.
- QA results.
- Review results.
- Task status.
- Checkpoint information.

A server restart must not silently reset retry counters or repeat destructive operations.

## 6. SECURITY AND QUALITY REQUIREMENTS

- Run tests in isolated execution environments.
- Restrict tool permissions.
- Validate all agent outputs.
- Treat repository content and test output as untrusted data.
- Prevent secrets from appearing in reports.
- Never claim that passing tests proves the application is bug-free.
- Never automatically approve security-sensitive changes solely on the basis of an LLM review.

## 7. OUT OF SCOPE

Do not implement:
- Final GitHub pull request creation.
- New unrelated agent roles.
- Production deployment.
- Unlimited autonomous debugging.

These belong to Chapter 5 or are explicitly prohibited.

## 8. ACCEPTANCE CRITERIA

- [x] QA Agent can execute repository-appropriate tests.
- [x] Actual test results are recorded.
- [x] Failed tests produce structured reports.
- [x] Developer receives actionable QA feedback.
- [x] Retry limits are enforced.
- [x] Repeated failures can trigger early escalation.
- [x] Retry state survives workflow interruptions.
- [x] Failure reports preserve useful diagnostic information.
- [x] Reviewer examines actual code changes.
- [x] Reviewer supports all three outcomes.
- [x] Review correction loops are bounded.
- [x] Passing QA does not automatically imply reviewer approval.
- [x] Tests cover retry and recovery behavior.

## 9. REQUIRED FINAL REPORT

### 1. Test Execution & Repository-Aware Discovery Architecture
- **Ecosystem Fingerprinting**: `QAEngineerAgent.detect_ecosystem()` inspects `package.json`, lockfiles, Python configuration, and actual file trees (`*.py`, `*.js`, `*.ts`).
- **Strict Language Isolation**: Prohibits Python test runners (`pytest`, `unittest`) on JavaScript/TypeScript repositories. Checks for presence of actual `test_*.py` / `*_test.py` before scheduling Python runners.
- **Monorepo Deduplication**: Prevents duplicate test executions by checking if parent `package.json` scripts orchestrate subprojects (`npm --prefix backend`, `npm run test:backend`).
- **Pre-Flight Bootstrapping**: Inspects `node_modules/` presence; automatically installs required dependencies before invoking test runners.
- **Categorization**: Distinguishes `CODE_REGRESSION` from `ENVIRONMENT_ERROR` (e.g. missing binary) and `NO_TESTS_FOUND`.

### 2. QA Agent Behavior & Diagnostic Synthesis
- Executes detected tests in the isolated workspace.
- Parses Jest bullet formats (`●`, `FAIL`), Pytest summaries, and exit codes.
- Computes SHA-256 deterministic failure signatures from test identifiers and error types.
- Evaluates requirement acceptance criteria against test outcomes.
- Formulates high-precision, surgical feedback targeting only affected application files without hallucinating unrelated language files.

### 3. Code Reviewer Behavior
- Inspects actual committed Git diffs (`git diff main...HEAD` or `HEAD~1`) on the task branch.
- Evaluates code across Correctness, Security, Code Quality (1-10 scale), and Convention adherence.
- Classifies reviews into `APPROVED`, `CHANGES_REQUESTED`, or `BLOCKED` (auto-blocks on `CRITICAL` severity).

### 4. Bounded Feedback Loops & Stall Detection
- **Developer-QA Loop**: Bounded at max 3 cycles.
- **Developer-Reviewer Loop**: Bounded at max 2 cycles.
- **Deterministic Stall Detection**: If two consecutive cycles yield identical failure signatures, the engine halts immediately (`QA_FAIL_STALLED`), preventing infinite loops and token waste.

### 5. Checkpoint Persistence & Recovery
- Integrated into LangGraph `StateGraph` compiled with `AsyncCompatiblePostgresSaver`.
- Execution state, retry counters (`qa_cycle`, `review_cycle`), failure history, and reports persist across server restarts.
- Resuming an interrupted workflow skips already-completed Developer steps and proceeds directly to QA / Review.

### 6. Verification Results
- 22/22 unit and flow tests passing in `backend/tests/`:
  - `test_qa_engineer.py`: 10 passed (Node.js, monorepo deduplication, strict JS isolation, pytest, env errors, failure signatures)
  - `test_code_reviewer.py`: 3 passed (Critical blocking, high severity changes requested, clean approved)
  - `test_qa_review_flow.py`: 9 passed (Full LangGraph routing, retry bounds, stall detection, delivery transition)
- Frontend build clean: `tsc --noEmit` and `npm run build` exiting with code 0.

---

**END OF CHAPTER 4 SPECIFICATION**