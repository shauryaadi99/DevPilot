# CHAPTER 4 — QA, CODE REVIEW AND RECOVERY

**Project:** DevPilot  
**Chapter:** 4 of 5  
**Status:** NOT STARTED  
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

- [ ] QA Agent can execute repository-appropriate tests.
- [ ] Actual test results are recorded.
- [ ] Failed tests produce structured reports.
- [ ] Developer receives actionable QA feedback.
- [ ] Retry limits are enforced.
- [ ] Repeated failures can trigger early escalation.
- [ ] Retry state survives workflow interruptions.
- [ ] Failure reports preserve useful diagnostic information.
- [ ] Reviewer examines actual code changes.
- [ ] Reviewer supports all three outcomes.
- [ ] Review correction loops are bounded.
- [ ] Passing QA does not automatically imply reviewer approval.
- [ ] Tests cover retry and recovery behavior.

## 9. REQUIRED FINAL REPORT

Report:
- Test execution architecture.
- QA Agent behavior.
- Reviewer behavior.
- Retry policy.
- Failure detection strategy.
- Checkpoint persistence.
- Security measures.
- Tests and actual results.
- Known limitations.
- Acceptance criteria status.

---

**END OF CHAPTER 4 SPECIFICATION**