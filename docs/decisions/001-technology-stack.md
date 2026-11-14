# ADR 001: Technology Stack Selection for DevPilot Foundation

**Status:** Approved  
**Date:** 2026-11-14  
**Context:** Chapter 1 — Foundation and Project Setup  

---

## 1. Context and Problem Statement
DevPilot requires a modern, modular, maintainable full-stack architecture capable of supporting a multi-agent autonomous engineering workflow. The project enforces a strict Free-First principle, local-first development without vendor lock-in, and clear separation of concerns.

## 2. Decision

We adopt the following stack:
1. **Frontend:** Next.js (App Router) with TypeScript and Tailwind CSS.
2. **Backend:** Python (3.14) with FastAPI, Pydantic v2, and Uvicorn.
3. **Database & ORM:** SQLAlchemy 2.0 with Alembic, using SQLite for local development and supporting PostgreSQL through connection string configuration.
4. **LLM Provider:** Groq (Free tier, using `llama-3.3-70b-versatile` or `llama-3.1-8b-instant`) through the official `groq` Python SDK.
5. **Testing Framework:** `pytest` with `pytest-asyncio` and `httpx` for backend; TypeScript verification (`tsc`) and ESLint for frontend.

## 3. Rationale

- **FastAPI:** Offers high-speed asynchronous processing, automatic OpenAPI/Swagger documentation, and Pydantic-based type safety, perfectly suited for agent tool execution and async workflows.
- **Next.js & Tailwind CSS:** Provides a fast, highly customizable UI environment suitable for real-time dashboards, code diffing, and developer workspaces.
- **SQLite / PostgreSQL via SQLAlchemy:** Enables zero-setup local developer experience (SQLite) with zero cost and zero operational friction, while keeping full schema portability to PostgreSQL via SQLAlchemy.
- **Groq:** Confirmed in `PROJECT.md` for fast, cost-free inference on high-capability open models.
- **Free-First Adherence:** All components are open-source (MIT/Apache 2.0/BSD) and all external services run on free tiers.

## 4. Consequences
- **Positive:** Fast development velocity, instant local start, zero cloud cost for Chapter 1.
- **Mitigations:** The Groq integration is strictly isolated in `backend/app/integrations/` to ensure provider portability. Database queries use standard SQLAlchemy constructs to maintain engine agnosticism.
