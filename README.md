# NyayaLens

**Understand. Review. Act.**

A responsible GenAI legal document assistant that transforms complex documents into understandable information, evidence-backed answers, review priorities, comparisons, checklists, and professional consultation questions.

> NyayaLens provides AI-assisted legal information and document-review assistance. It does not provide legal advice, legal representation, or guarantee a legal outcome. For important decisions, consult a qualified legal professional.

## Repository Structure

```
nyayalens/
│
├── frontend/          # Next.js website (App Router, TS, Tailwind, ESLint)
├── backend/           # FastAPI backend (uv-managed, SQLAlchemy, Alembic)
├── docs/              # Technical product documentation (see DOCS/)
├── DOCS/              # Full documentation suite (product, UX, tech, AI, security, testing)
├── db/initdb/         # PostgreSQL init scripts (pgvector extension)
├── tests/             # Shared / evaluation test artifacts
├── .github/workflows/ # CI / CD
├── README.md
├── SECURITY.md
├── RESPONSIBLE_AI.md
├── LICENSE
├── .gitignore
├── .editorconfig
├── .env.example
└── docker-compose.yml
```

Note: `DOCS/` and `docs/` refer to the same directory on Windows (the canonical name is `DOCS/`).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (React) + TypeScript + Tailwind CSS + ESLint |
| Backend | FastAPI + Pydantic + SQLAlchemy + Alembic (uv) |
| Database | PostgreSQL + pgvector (Docker) |
| Storage | Private object storage (planned) |
| AI | LLM API + embeddings + OCR (planned, providers TBD) |

## Prerequisites

- Node.js 20.9+ (developed against 24 LTS)
- Python 3.10+ (developed against 3.14)
- [uv](https://docs.astral.sh/uv/) for the Python environment
- Docker Desktop with WSL2 backend

## Quick Start

### Database (Docker)

```powershell
docker compose up -d
docker compose exec postgres psql -U nyayalens -d nyayalens -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Backend

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --reload
# http://localhost:8000/health
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
# http://localhost:3000
```

## Documentation

The full documentation suite lives in `DOCS/` and is indexed in `DOCS/README.md`:

- `DOCS/01_PRODUCT` — problem statement, vision, PRD, personas, stories, metrics, privacy
- `DOCS/02_UX` — information architecture, user flows, screen specs, UI/UX, design system
- `DOCS/03_TECH` — system architecture, API spec, database schema, deployment
- `DOCS/04_AI` — AI architecture, RAG, citations, prompts, evaluation
- `DOCS/05_SECURITY` — security architecture, responsible AI
- `DOCS/06_TESTING` — test plan and test cases

## Status

Phase 1 foundation: scaffolding + infrastructure wiring only. No business features implemented yet.

## License

TBD.