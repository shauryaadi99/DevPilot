# DevPilot

DevPilot is an AI-powered autonomous software engineering platform. It enables developers to connect a repository, describe software requirements in natural language, and delegate the engineering workflow to a controlled team of specialized AI agents.

This project is built following a rigorous, chapter-by-chapter approach adhering to the master specifications in `PROJECT.md`.

---

## Current Status: Chapter 1 — Foundation and Project Setup

Chapter 1 establishes a modular, maintainable foundation:
- **Backend:** FastAPI (Python) with modular routing, structured logging, centralized error handling, and health endpoints.
- **Frontend:** Next.js (TypeScript, App Router) with Tailwind CSS, providing a modern engineering workspace shell.
- **Database:** SQLAlchemy 2.0 ORM with Alembic migration support (SQLite for local zero-config, PostgreSQL-ready).
- **LLM Foundation:** Isolated Groq provider integration module adhering to the free-first philosophy.

---

## Project Structure

```text
DevPilot/
├── .gitignore
├── .env.example              # Root environment variable template
├── README.md                 # Project guide and startup instructions
├── PROJECT.md                # Master source of truth
├── docs/                     # Architectural decisions and chapter specs
│   ├── architecture/
│   ├── decisions/
│   └── chapters/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/              # API routes (/health, /api/v1/...)
│   │   ├── core/             # Configuration and logging
│   │   ├── db/               # SQLAlchemy models and session management
│   │   ├── integrations/     # Groq LLM integration
│   │   └── main.py           # Application entrypoint
│   ├── tests/                # Automated pytest suite
│   ├── requirements.txt      # Production dependencies
│   └── requirements-dev.txt  # Testing and development tools
└── frontend/                 # Next.js frontend application
    ├── src/
    │   ├── app/              # Next.js App Router
    │   ├── components/       # Workspace layout and UI elements
    │   └── lib/              # API client and utilities
    └── package.json          # Frontend scripts and dependencies
```

---

## Prerequisites

- **Python:** 3.11+ (Python 3.14 verified)
- **Node.js:** 20.x or 24.x (Node 24.x verified) with `npm`
- **Groq API Key:** Free tier key from [Groq Console](https://console.groq.com/keys)

---

## Quickstart Guide

### 1. Environment Setup

Create `.env` files from `.env.example`:

```bash
# In project root:
cp .env.example .env

# In backend directory:
cp .env.example backend/.env

# In frontend directory:
cp .env.example frontend/.env.local
```

Configure your `GROQ_API_KEY` in `backend/.env`.

---

### 2. Backend Setup & Startup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run the development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify backend health at [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health) or view interactive Swagger docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

### 3. Frontend Setup & Startup

```bash
cd frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the DevPilot workspace.

---

### 4. Running Tests

#### Backend Tests:
```bash
cd backend
pytest
```

#### Frontend Type Checking & Build:
```bash
cd frontend
npm run typecheck
npm run build
```

---

## Documentation

- [Master Project Instructions](PROJECT.md)
- [Chapter 1 Specification](docs/chapters/CHAPTER_1.md)
- [System Architecture](docs/architecture/overview.md)
- [ADR 001: Technology Stack](docs/decisions/001-technology-stack.md)
