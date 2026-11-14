# DEVPILOT — MASTER PROJECT INSTRUCTIONS

**Project:** DevPilot  
**Document:** PROJECT.md  
**Purpose:** Master source of truth for all development work  
**Development approach:** Chapter-by-chapter implementation using Antigravity

---

# 1. PROJECT OVERVIEW

DevPilot is an AI-powered autonomous software engineering platform.

It allows users to connect a GitHub repository, describe a software requirement in natural language, and delegate the engineering workflow to a controlled team of specialized AI agents.

DevPilot should be capable of:

1. Understanding user requirements.
2. Inspecting an existing codebase.
3. Creating an implementation plan.
4. Requesting human approval.
5. Implementing approved changes.
6. Running tests and validating functionality.
7. Diagnosing and fixing failures.
8. Reviewing code changes.
9. Requesting final human approval.
10. Creating a GitHub pull request.

DevPilot must behave like a controlled software engineering system, not an ordinary chatbot.

# 2. CORE DEVELOPMENT PRINCIPLES

These principles are mandatory throughout the project.

## 2.1 Chapter-based development

The project is divided into five chapters.

- Implement only the chapter explicitly requested.
- Do not begin implementing future chapters.
- Do not skip unfinished requirements from earlier chapters.
- Complete the current chapter's deliverables before declaring it finished.
- Keep the application functional after every chapter.

## 2.2 No hallucinated implementation

Antigravity must NEVER:

- Invent API endpoints, database tables or business requirements.
- Assume a feature exists without inspecting the code.
- Assume a dependency is installed without verifying it.
- Invent environment variables, credentials or configuration.
- Make up test results.
- Claim that functionality works without testing it.
- Silently replace an existing implementation with a different architecture.
- Introduce unnecessary libraries or services.
- Invent missing project requirements.

If information is missing:

1. Inspect the existing project and documentation.
2. Check whether the answer can be established from existing code.
3. If it cannot, clearly explain what is missing.
4. Ask the user for clarification before making a consequential decision.

Never present an assumption as an established fact.

## 2.3 Inspect before modifying

Before writing code:

- Inspect the existing folder structure.
- Read relevant source files.
- Inspect package and dependency files.
- Check existing architecture and naming conventions.
- Understand the current implementation.
- Identify files that will be modified.

Do not rewrite existing files simply because a different implementation is easier.

## 2.4 Minimal and focused implementation

- Implement only what the requested chapter requires.
- Avoid premature abstractions.
- Avoid unnecessary microservices.
- Avoid unnecessary dependencies.
- Do not refactor unrelated functionality.
- Prefer simple, maintainable solutions.

## 2.5 Practical learning

The project will be developed through practical implementation.

When introducing a new technology:

- Explain what it does.
- Explain why DevPilot needs it.
- Explain where it is being used.
- Keep explanations connected to the actual implementation.

Do not turn implementation tasks into unrelated tutorials.

# 3. LOCKED PROJECT DECISIONS

The following decisions are already established.

| Decision | Status |
|---|---|
| Project name | DevPilot |
| LLM provider | Groq |
| Maximum specialized agents | 5 |
| Development environment | Antigravity |
| Development approach | Practical, chapter-based |
| Cost philosophy | Free-first |
| Human approval | Required at important checkpoints |

These decisions must not be changed without explicit user approval.

## 3.1 LLM integration

Groq is the selected LLM provider.

- Use Groq for agent inference.
- Prefer available free-tier models.
- Do not introduce paid LLM providers without explicit approval.
- Keep LLM integration modular so that changing providers in the future remains possible.
- Never hardcode API keys.

## 3.2 Cost constraints

DevPilot should be built using free tools and free tiers wherever practical.

Before introducing a new service or dependency:

- Check whether it is free for the intended usage.
- Identify relevant usage limitations.
- Prefer local development solutions.
- Ask before introducing a dependency that requires payment.

Do not claim that a service is completely free without verifying its current pricing and limits.

# 4. SPECIALIZED AGENTS

DevPilot must have no more than five specialized agents.

### 1. Product Analyst Agent

Responsible for:
- Understanding requirements.
- Identifying ambiguity.
- Asking clarification questions.
- Creating functional requirements.
- Defining acceptance criteria.

### 2. Architect Agent

Responsible for:
- Inspecting the repository.
- Understanding the existing architecture.
- Identifying affected files.
- Creating implementation plans.
- Defining technical dependencies and contracts.

### 3. Developer Agent

Responsible for:
- Implementing approved changes.
- Creating, editing and deleting files.
- Following existing project conventions.
- Reporting modifications.

### 4. QA Engineer Agent

Responsible for:
- Running tests.
- Validating acceptance criteria.
- Identifying failures.
- Producing diagnostic reports.
- Providing actionable feedback to the Developer.

### 5. Code Reviewer Agent

Responsible for:
- Reviewing code changes.
- Identifying bugs and security issues.
- Checking maintainability.
- Verifying consistency with project conventions.
- Approving or requesting changes.

Do not create additional specialized agents without explicit approval.

Tools such as GitHub integration, filesystem access, terminal execution and Docker are capabilities, not additional agents.

# 5. REQUIRED ENGINEERING WORKFLOW

The intended workflow is:

User Requirement
    |
    v
Product Analyst
    |
    v
Architect
    |
    v
Implementation Plan
    |
    v
Human Approval
    |
    v
Developer
    |
    v
QA Engineer
    |
    +---- Failure ----> Developer
    |                       |
    |                       v
    |                      QA
    |
    v
Code Reviewer
    |
    +---- Changes Required ----> Developer
    |
    v
Final Human Approval
    |
    v
GitHub Pull Request

Important rules:

- Never implement a plan before its required approval.
- Never push changes to the main branch automatically.
- Use isolated task branches.
- Keep QA and code review responsibilities separate.
- Bound automatic retry loops.
- Stop and report failures when retry limits are reached.
- Never claim that passing tests guarantees bug-free or secure software.

# 6. HUMAN APPROVAL AND SAFETY

Two important human approval checkpoints are required.

### Approval 1: Implementation plan

The user must review and approve the implementation plan before code modifications begin.

### Approval 2: Final delivery

The user must approve the completed changes before DevPilot creates or submits a GitHub pull request.

Additional safety requirements:

- Never expose secrets in logs.
- Never store raw access tokens in plaintext.
- Never execute untrusted repository code directly on the application server.
- Use isolated execution environments.
- Apply timeouts and resource limits.
- Restrict filesystem and network access wherever practical.
- Preserve the main branch.

# 7. FIVE DEVELOPMENT CHAPTERS

## CHAPTER 1 — FOUNDATION AND PROJECT SETUP

Objective: Establish the application foundation.

Expected areas:
- Project architecture.
- Folder structure.
- Frontend setup.
- Backend setup.
- Database foundation.
- Configuration management.
- Groq integration foundation.
- Logging and health checks.
- Basic application shell.

Completion criteria:
- Application starts successfully.
- Frontend and backend communicate.
- Configuration is handled securely.
- Basic health checks work.
- Initial documentation is available.

## CHAPTER 2 — REPOSITORY INTELLIGENCE AND PLANNING

Objective: Enable DevPilot to understand an existing repository and generate an implementation plan.

Expected areas:
- GitHub integration.
- Repository selection.
- Repository access and inspection.
- Codebase analysis.
- Product Analyst Agent.
- Architect Agent.
- Structured implementation plans.
- Human plan approval.

Completion criteria:
- User can connect a repository.
- DevPilot can inspect its actual contents.
- DevPilot can generate a repository-aware plan.
- User can approve or reject the plan.
- No code modifications happen before approval.

## CHAPTER 3 — AUTONOMOUS DEVELOPMENT ENGINE

Objective: Enable DevPilot to implement approved plans.

Expected areas:
- Developer Agent.
- Git operations.
- Task branches.
- Filesystem tools.
- Controlled code modification.
- Execution sandbox.
- Change tracking.

Completion criteria:
- DevPilot can implement an approved task.
- Changes remain isolated from the main branch.
- Modifications can be inspected.
- Unsafe execution is prevented.

## CHAPTER 4 — QA, CODE REVIEW AND RECOVERY

Objective: Enable DevPilot to validate, diagnose and review its own changes.

Expected areas:
- QA Engineer Agent.
- Test execution.
- Acceptance-criteria validation.
- Failure diagnosis.
- Bounded retry mechanism.
- Repeated-failure detection.
- Code Reviewer Agent.
- Structured review reports.

Completion criteria:
- Tests can be executed and results recorded.
- QA failures can be returned to the Developer.
- Retry loops cannot continue indefinitely.
- Reviewer can request changes.
- Unresolved failures generate useful reports.

## CHAPTER 5 — GITHUB DELIVERY AND PRODUCTION READINESS

Objective: Complete the end-to-end user experience.

Expected areas:
- Dashboard.
- Project workspace.
- Task workspace.
- Live agent activity.
- Logs and execution timeline.
- Code diffs.
- Test reports.
- Approval interfaces.
- GitHub pull request creation.
- Authentication and access control.
- Security hardening.
- Deployment and documentation.

Completion criteria:
- A user can complete the full workflow.
- Live progress is visible.
- Code changes can be reviewed.
- Final approval is required.
- GitHub pull requests are created correctly.
- End-to-end tests pass.

# 8. ANTIGRAVITY EXECUTION PROTOCOL

Whenever a chapter is assigned, follow this protocol.

### Step 1: Read the instructions

Read PROJECT.md completely.

Read the requested chapter document.

Read any relevant architecture and decision documents.

### Step 2: Inspect the actual project

Inspect the existing repository before proposing modifications.

Do not assume the repository is in its expected state.

### Step 3: Identify the scope

Clearly identify:

- What needs to be implemented.
- What already exists.
- What needs modification.
- What is explicitly out of scope.
- Any missing information or blockers.

### Step 4: Present the implementation approach

Before significant implementation, provide a concise plan containing:

- Files to create.
- Files to modify.
- Dependencies required.
- Implementation sequence.
- Tests to perform.
- Potential risks.

If a consequential decision is not specified, ask before proceeding.

### Step 5: Implement incrementally

- Work in small logical steps.
- Follow existing conventions.
- Avoid unrelated changes.
- Keep code readable and modular.
- Do not silently skip requirements.

### Step 6: Verify the implementation

Run relevant tests and checks.

Report:
- Commands executed.
- Actual results.
- Failures.
- Known limitations.
- Requirements not completed.

If a test could not be executed, explicitly say so.

### Step 7: Update documentation

Update relevant documentation and record important architectural decisions.

Do not overwrite previous decisions without approval.

### Step 8: Report chapter status

Use one of these statuses:

- NOT STARTED
- IN PROGRESS
- BLOCKED
- COMPLETED

Only mark a chapter COMPLETED when its completion criteria have actually been verified.

# 9. SCOPE CONTROL

When the user requests a particular chapter:

- Work only within that chapter.
- Do not begin later chapters.
- Do not add unrequested features.
- Do not perform broad architectural redesigns.
- Do not change locked decisions.
- Do not skip required work to make the chapter appear complete.

If a later chapter requires a small foundational change, explain the dependency first and obtain approval when it changes scope.

# 10. DOCUMENTATION AND ARCHITECTURAL DECISIONS

Keep the following documentation updated:

- PROJECT.md: Master project instructions.
- docs/chapters/: Detailed chapter requirements.
- docs/architecture/: Architecture and system design.
- docs/decisions/: Important technical decisions.

Record important decisions with:
- Decision.
- Reason.
- Alternatives considered.
- Consequences.

Never silently change an established architectural decision.

# 11. DEFINITION OF DONE

A feature is not complete merely because code has been written.

Before declaring work complete:

1. Requirements are implemented.
2. Relevant tests have been executed.
3. Actual test results are reported.
4. Existing functionality has not been unnecessarily broken.
5. Security implications have been considered.
6. Documentation is updated.
7. Known limitations are disclosed.

A chapter is complete only when its own completion criteria are verified.

---

# FINAL INSTRUCTION

PROJECT.md is the master source of truth for DevPilot.

Follow it throughout development.

Prioritize correctness, transparency, maintainability and controlled implementation over speed.

Do not hallucinate missing information.

Do not make consequential decisions on behalf of the user.

Do not implement future chapters without authorization.

If something is unclear, stop and ask.

**Build DevPilot one verified chapter at a time.**