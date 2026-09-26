# NyayaLens

**Understand. Review. Act.**

A responsible GenAI legal document assistant that transforms complex documents into understandable information, evidence-backed answers, review priorities, comparisons, checklists, and professional consultation questions.

> NyayaLens provides AI-assisted legal information and document-review assistance. It does not provide legal advice, legal representation, or guarantee a legal outcome. For important decisions, consult a qualified legal professional.

## Repository Structure

```
nyayalens/
│
├── frontend/          # Next.js website (App Router, TS, Tailwind CSS, ESLint, Vitest, Playwright)
├── backend/           # FastAPI backend (uv-managed, Pydantic, Supabase-native)
├── supabase/          # Supabase project config, SQL migrations, seed data
├── docs/              # Full documentation suite (product, UX, tech, AI, security, testing)
├── db/                # Optional local PostgreSQL/pgvector sandbox (legacy docker-compose)
├── tests/             # Reserved for shared/evaluation test artifacts
├── .github/workflows/ # CI
├── README.md
├── SECURITY.md
├── RESPONSIBLE_AI.md
├── .gitignore
├── .editorconfig
├── .env.example
└── docker-compose.yml
```

The canonical documentation directory is `docs/` (indexed in `docs/README.md`); a Windows checkout may display it as `DOCS/` because the filesystem is case-insensitive.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (React) + TypeScript + Tailwind CSS + ESLint |
| Backend | FastAPI + Pydantic (uv) — Supabase-native, no SQLAlchemy/Alembic |
| Database | Supabase Postgres + pgvector (owned via `supabase/migrations`) |
| Storage | Private Supabase Storage bucket (`legal-documents`) |
| AI | Configurable LLM + embeddings providers (OpenAI-compatible) + OCR (Tesseract) |
| Auth | Supabase Auth (backend verifies access tokens offline) |

The `docker-compose.yml` Postgres service is an optional legacy/sandbox only; the running application uses Supabase.

## Prerequisites

- Node.js 20.9+ (developed against 24 LTS)
- Python 3.10+ (developed against 3.14)
- [uv](https://docs.astral.sh/uv/) for the Python environment (or the pre-created `backend/.venv`)
- A Supabase project (URL, anon key, service-role key, JWT secret)
- Tesseract OCR installed locally only when processing scanned-image PDFs

## Quick Start

### Backend

```powershell
cd backend
cp .env.example .env        # fill in your Supabase project values
uv sync                     # or: .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
uv run uvicorn app.main:app --reload
# http://localhost:8000/health
```

Apply the SQL migrations (`supabase/migrations`) to your project via the Supabase CLI:

```powershell
supabase db push           # run from the repo root (uses supabase/config.toml)
```

Document processing runs in a separate worker — start it to move uploaded documents through extraction → analysis → READY:

```powershell
cd backend
uv run python -m app.workers.document_worker --ensure-embedding-index  # once, after configuring embeddings
uv run python -m app.workers.document_worker                            # process pending documents
```

### Frontend

```powershell
cd frontend
cp .env.local.example .env.local   # fill in NEXT_PUBLIC_* browser-safe values
npm install
npm run dev
# http://localhost:3000
```

For the split Vercel deployment, set the frontend project root to `frontend/`
and configure only these frontend variables:

```text
NEXT_PUBLIC_DEMO_MODE=true
NEXT_PUBLIC_API_URL=https://nyaya-lens-ruby.vercel.app
```

The demo login is:

```text
Email: demo@nyayalens.com
Password: NyayaDemo2026!
```

The backend project root is `backend/` and must separately define its Supabase
server credentials and `CORS_ORIGINS=https://nyayalen.vercel.app`. Never copy
backend secrets into the frontend Vercel project. Set `NEXT_PUBLIC_DEMO_MODE`
to `false` only after replacing the placeholder/stale Supabase URL and anon key
with values from the active Supabase project.

## Documentation

The full documentation suite lives in `docs/` (indexed in `docs/README.md`):

- `docs/01_PRODUCT` — problem statement, vision, PRD, personas, stories, metrics, privacy
- `docs/02_UX` — information architecture, user flows, screen specs, UI/UX, design system
- `docs/03_TECH` — system architecture, API spec, database schema, testing, API validation
- `docs/04_AI` — AI architecture, RAG, citations, prompts, evaluation
- `docs/05_SECURITY` — security architecture, responsible AI
- `docs/06_TESTING` — test plan and test cases

## Status

Implemented and verified (commit `55447b7` era, CI green):

- Secure **document upload** (validation, private storage, RLS, deduplication, audit log).
- **Document processing pipeline**: PDF/DOCX/OCR extraction → sections → clauses → entities → chunking → embeddings (pgvector).
- **Document understanding**: plain-language summary, clause analysis, attention areas, Q&A with backend-validated citations, two-document comparison, Action Center, professional questions, and review reports.
- **Honest AI abstention**: when the AI provider is not configured or has no grounded evidence, the system says so instead of fabricating content.
- **Tests**: 260+ backend tests (pytest) and 40 frontend tests (Vitest + axe) plus a Playwright E2E journey; build and lint clean in CI.

Run `pytest` (backend) and `npm test` / `npm run lint` / `npm run build` (frontend) to verify locally.

## License

TBD — no license file has been selected yet.