# CHAPTER 2 — REPOSITORY INTELLIGENCE AND PLANNING

**Project:** DevPilot  
**Chapter:** 2 of 5  
**Status:** COMPLETED  
**Depends on:** Chapter 1

---

## 1. OBJECTIVE

Enable users to connect a GitHub repository, submit a software requirement and receive a structured implementation plan generated using actual repository information.

This is the first chapter where DevPilot becomes meaningfully AI-powered.

The main objective is:

**Given a real repository and a natural-language requirement, DevPilot must understand the existing codebase and generate a repository-aware implementation plan.**

No autonomous code modification is permitted in this chapter.

## 2. FUNCTIONAL REQUIREMENTS

### 2.1 GitHub integration

Implement:
- GitHub OAuth or an appropriately approved GitHub App integration.
- Secure authorization flow.
- Repository listing for authorized users.
- Repository selection.
- Repository metadata retrieval.
- Permission and access error handling.

Security requirements:
- Never expose GitHub access tokens to the frontend unnecessarily.
- Never store raw tokens in plaintext.
- Request only the permissions required.
- Respect repository access permissions.
- Do not expose private repository contents to unauthorized users.

### 2.2 Repository access

DevPilot must be able to retrieve repository information safely.

It should collect:
- Repository name.
- Owner.
- Default branch.
- Directory structure.
- Relevant source files.
- Configuration files.
- Dependency manifests.
- Existing documentation.

Use an appropriate repository access mechanism.

Do not assume every repository is a Node.js or Python application.

### 2.3 Repository inspection

Build a repository inspection pipeline.

The inspection system should identify:
- Programming languages.
- Frameworks.
- Build tools.
- Package managers.
- Application entry points.
- API structure.
- Database-related files.
- Testing frameworks.
- Important configuration files.
- Existing coding conventions.

It should distinguish between:
- Confirmed observations.
- Inferences.
- Unknown information.

Do not claim to understand files that were not inspected.

Large repositories must be handled intelligently. Do not indiscriminately send an entire repository to the LLM.

### 2.4 Product Analyst Agent

Responsibilities:
- Interpret the user requirement.
- Identify ambiguous statements.
- Extract functional requirements.
- Extract nonfunctional requirements where relevant.
- Generate acceptance criteria.
- Ask clarification questions when necessary.

Output must be structured rather than an unformatted conversational response.

### 2.5 Architect Agent

Responsibilities:
- Consume the Product Analyst output.
- Consume repository inspection results.
- Understand the existing architecture.
- Identify affected components and files.
- Propose implementation changes.
- Identify dependencies and risks.
- Produce an ordered implementation plan.

The Architect must prefer extending existing patterns instead of introducing unnecessary new architectures.

### 2.6 Implementation plan

The plan should include:

1. Requirement summary.
2. Repository understanding.
3. Confirmed technical observations.
4. Proposed files to create.
5. Proposed files to modify.
6. API or data-contract changes, if required.
7. Implementation steps.
8. Dependencies.
9. Testing strategy.
10. Risks and uncertainties.
11. Acceptance criteria.

Each proposed file modification should explain why it is necessary.

### 2.7 Human approval

Provide a plan review interface.

The user must be able to:
- Approve the plan.
- Reject the plan.
- Request modifications.
- Ask questions about the plan.

Approval must be recorded persistently.

Approving a plan must not trigger code modifications in this chapter.

## 3. AGENT ARCHITECTURE

Introduce only two specialized agents:

1. Product Analyst.
2. Architect.

Do not implement the Developer, QA Engineer or Code Reviewer agents yet.

The agents should return validated structured outputs.

Use Groq for inference.

The integration must:
- Handle API failures.
- Handle malformed model responses.
- Validate outputs against defined schemas.
- Record model and execution metadata where appropriate.
- Avoid treating untrusted repository content as system instructions.

## 4. WORKFLOW

```text
User selects repository
        |
        v
User submits requirement
        |
        v
Repository inspection
        |
        v
Product Analyst Agent
        |
        v
Requirement analysis
        |
        v
Architect Agent
        |
        v
Implementation plan
        |
        v
Human review
        |
        +---- Request changes
        |
        +---- Reject
        |
        +---- Approve
```

No transition to code modification is allowed.

## 5. PERSISTENCE REQUIREMENTS

Persist the information necessary to:
- Identify the connected repository.
- Identify the submitted task.
- Store repository metadata.
- Store inspection results or references.
- Store structured requirements.
- Store the implementation plan.
- Store approval decisions.
- Track agent execution status.

Database schema changes must be documented and migrated safely.

Do not invent table structures without examining the existing database design.

## 6. USER INTERFACE REQUIREMENTS

Create:
- GitHub connection interface.
- Repository selection interface.
- New task submission interface.
- Repository inspection status.
- Agent execution timeline.
- Requirement analysis view.
- Implementation plan view.
- Plan approval controls.

The interface should make clear what DevPilot has inspected and what it has inferred.

## 7. OUT OF SCOPE

Do not implement:
- Autonomous file modification.
- Developer Agent.
- QA Agent.
- Code Reviewer Agent.
- Automatic test execution on user repositories.
- Automatic Git commits.
- Automatic pull requests.

These belong to later chapters.

## 8. ACCEPTANCE CRITERIA

- [x] User can authorize GitHub access.
- [x] Authorized repositories can be listed.
- [x] User can select a repository.
- [x] Repository metadata can be retrieved.
- [x] Repository inspection works on supported repository types.
- [x] Unsupported or incomplete repository information is reported honestly.
- [x] Product Analyst generates structured requirements.
- [x] Architect produces a repository-aware plan.
- [x] Plans distinguish facts from assumptions.
- [x] User can approve, reject or request changes.
- [x] Approval decisions persist.
- [x] No source code is modified by DevPilot.
- [x] Tests cover the repository inspection and planning workflow.

## 9. REQUIRED FINAL REPORT

Report:
- GitHub integration approach.
- Permissions requested.
- Repository inspection strategy.
- Agent architecture.
- Structured output schemas.
- Database changes.
- UI changes.
- Tests and actual results.
- Security considerations.
- Known limitations.
- Acceptance criteria status.

---

**END OF CHAPTER 2 SPECIFICATION**