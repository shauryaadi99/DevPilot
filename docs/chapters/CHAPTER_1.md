# CHAPTER 1 — FOUNDATION AND PROJECT SETUP

**Project:** DevPilot  
**Chapter:** 1 of 5  
**Status:** COMPLETED  
**Priority:** Critical  
**Depends on:** PROJECT.md

---

## 1. OBJECTIVE

Establish a clean, modular and maintainable foundation for DevPilot.

At the end of this chapter, the application should start successfully, its frontend and backend should communicate, configuration should be secure, and the project should be ready for the introduction of repository intelligence and AI agents in Chapter 2.

This chapter builds the foundation, not the autonomous engineering functionality.

## 2. TECHNOLOGY DECISIONS

Already confirmed:
- LLM provider: Groq.
- Development environment: Antigravity.
- Cost philosophy: Free-first.

Other technology choices must be proposed and approved before implementation.

Recommended baseline for discussion:
- Frontend: Next.js with TypeScript.
- Styling: Tailwind CSS.
- Backend: Python with FastAPI.
- Database: PostgreSQL.
- ORM: SQLAlchemy.
- Local infrastructure: Docker Compose where useful.

Do not treat these recommendations as approved decisions until the user confirms them.

Do not introduce Redis, Celery, Kubernetes or additional infrastructure without a demonstrated requirement.

## 3. FUNCTIONAL REQUIREMENTS

### 3.1 Project initialization
- Establish the root directory structure.
- Initialize frontend and backend applications.
- Configure development scripts.
- Establish dependency management.
- Create environment variable templates.
- Create a .gitignore file.

### 3.2 Frontend foundation
- Establish the application layout.
- Create reusable layout components.
- Create navigation structure.
- Establish a consistent design system.
- Configure API communication with the backend.
- Implement loading, error and empty states where relevant.

The initial interface should resemble a modern AI engineering workspace rather than a generic chatbot.

Do not implement full dashboard functionality yet.

### 3.3 Backend foundation
- Initialize the backend application.
- Establish modular routing.
- Configure request validation.
- Configure centralized error handling.
- Establish configuration management.
- Add health-check endpoints.
- Add structured logging.

### 3.4 Database foundation
- Establish database connectivity.
- Configure the ORM.
- Establish migration management.
- Create the initial database connection test.

Do not prematurely create every future database table. Only create tables required by the approved Chapter 1 implementation.

### 3.5 Groq integration foundation
- Create a dedicated LLM integration module.
- Configure Groq credentials through environment variables.
- Implement a minimal connection test.
- Handle API errors and timeouts.
- Keep provider-specific code isolated.

Do not create the five agents in this chapter.

### 3.6 Developer experience
- Establish consistent formatting and linting.
- Configure basic backend and frontend tests.
- Document local startup instructions.
- Provide clear error messages when required configuration is missing.

## 4. PROPOSED DIRECTORY STRUCTURE

The final structure must be based on the approved stack.

A possible starting structure:

```text
DevPilot/
├── PROJECT.md
├── README.md
├── .gitignore
├── .env.example
├── docs/
│   ├── architecture/
│   ├── decisions/
│   └── chapters/
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── integrations/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
└── docker-compose.yml
```

This is a proposal, not a requirement to create empty folders unnecessarily.

## 5. IMPLEMENTATION SEQUENCE

1. Inspect the existing repository.
2. Read PROJECT.md and this chapter.
3. Present proposed technology choices.
4. Wait for approval of unconfirmed architectural decisions.
5. Initialize the repository structure.
6. Set up the backend.
7. Set up the frontend.
8. Establish frontend-backend communication.
9. Establish database connectivity.
10. Implement the Groq integration foundation.
11. Configure tests, linting and logging.
12. Verify the entire application.
13. Update documentation.

Implement in small, verifiable milestones.

## 6. SECURITY REQUIREMENTS

- Never commit API keys.
- Never hardcode credentials.
- Validate incoming API requests.
- Avoid exposing internal exceptions to users.
- Keep environment-specific configuration outside source code.
- Do not log secrets or sensitive request data.

## 7. OUT OF SCOPE

Do not implement:
- GitHub OAuth.
- Repository cloning.
- Repository analysis.
- AI agents.
- LangGraph workflows.
- Autonomous code modifications.
- Docker-based untrusted code execution.
- QA automation.
- Pull request creation.
- Full authentication system.

These belong to later chapters.

## 8. ACCEPTANCE CRITERIA

Chapter 1 can be marked COMPLETED only when:

- [x] Approved architecture is documented.
- [x] Frontend starts successfully.
- [x] Backend starts successfully.
- [x] Frontend communicates with backend.
- [x] Health-check endpoint works.
- [x] Database connection is verified.
- [x] Migration mechanism works if applicable.
- [x] Groq connection is verified without exposing credentials.
- [x] Environment variables are documented.
- [x] Basic tests pass.
- [x] Startup instructions are documented.
- [x] No unapproved future functionality has been introduced.

## 9. REQUIRED FINAL REPORT

Antigravity must report:

1. What was implemented.
2. Technologies and versions used.
3. Files created.
4. Files modified.
5. Dependencies introduced.
6. Commands used to run the project.
7. Tests executed and actual results.
8. Known limitations.
9. Outstanding issues.
10. Whether every acceptance criterion passed.

Do not mark the chapter complete if any mandatory criterion remains unverified.

---

**END OF CHAPTER 1 SPECIFICATION**