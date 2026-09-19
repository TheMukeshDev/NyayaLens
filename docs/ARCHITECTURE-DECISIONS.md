# NyayaLens — Architecture Decisions

**Status:** Canonical / Source of truth
**Scope:** Decisions that reconcile the `docs/` requirements set with the mandated hosted platform (Supabase) for the hackathon MVP.
**Version:** 1.0

---

# 1. Audit Summary

## 1.1 Duplicate Documents

No full-file duplicates were found. Two overlaps were identified:

1. `docs/05_SECURITY/SECURITY-Architecture.md` restates `System-Architecture.md` sections 48–53, 58–59, 78 almost verbatim (it declares itself the canonical security copy of that file). This is intentional but should be kept in sync.
2. `docs/04_AI/RAG-Architecture.md` re-describes the RAG pipeline also present in `AI-Architecture.md` and `System-Architecture.md` (top-K, chunking, vector search). Complementary, not conflicting, except where noted in §1.4.

Product-layer docs (`PRD.md`, `Product-Vision.md`, `Problem-Statement.md`, `User-Stories.md`, `FEATURE-REQUIREMENTS.md`, `Success-Metrics.md`) intentionally overlap at an abstract level and are consistent in scope.

## 1.2 Filename Case Conflicts

The actual on-disk filenames use inconsistent casing, and several differ from the canonical names referenced in output docs and in this task:

| Referenced-as | On-disk file |
| --- | --- |
| Personas.md | `docs/01_PRODUCT/PERSONA.md` |
| Feature-Requirements.md | `docs/01_PRODUCT/FEATURE-REQUIREMENTS.md` |
| User-Flows.md | `docs/02_UX/USER-Flows.md` |
| Information-Architecture.md | `docs/02_UX/INFORMATION-ARCHITECTURE.md` |
| Design-System.md | `docs/02_UX/DESIGN-System.md` |
| Deployment.md | `docs/03_TECH/DEPLOYMENT.md` |
| Prompt-Strategy.md | `docs/04_AI/PROMPT-Strategy.md` |
| Citation-Strategy.md | `docs/04_AI/CITATION-Strategy.md` |
| AI-Evaluation.md | `docs/04_AI/AI-EVALUATION.md` |
| Evaluation-Dataset.md | `docs/04_AI/EVALUATION-DATASET.md` |
| Security-Architecture.md | `docs/05_SECURITY/SECURITY-Architecture.md` |
| Privacy.md | `docs/01_PRODUCT/PRIVACY.md` |
| Responsible-AI.md | `docs/05_SECURITY/RESPONSIBLE-AI.md` |
| Test-Cases.md | `docs/06_TESTING/TEST-CASES.md` |

Broken cross-reference found: `docs/04_AI/AI-EVALUATION.md` (line 331) points to `docs/06_TESTING/Evaluation-Dataset.md`, but the actual file is `docs/04_AI/EVALUATION-DATASET.md`. **Action:** update the reference to `docs/04_AI/EVALUATION-DATASET.md`.

Recommendation: normalize all filenames to a single case convention (PascalCase matching `USER-Flows.md` / `AI-EVALUATION.md` only if done uniformly; otherwise lowercase). Case conflicts matter on case-sensitive Linux CI.

## 1.3 Conflicting Functional-Requirement Numbering

Two different FR numbering schemes exist:

- `PRD.md` §32 uses `FR-01` … `FR-16`.
- `FEATURE-REQUIREMENTS.md` uses `FR-001` … `FR-022`.

Contents substantially overlap (auth, upload, processing, summary, Q&A, comparison, reports). **Action:** adopt `FEATURE-REQUIREMENTS.md` (`FR-001` … `FR-022`) as the canonical requirement IDs; map `PRD.md` to them or remove the duplicate numbering.

## 1.4 Conflicting Requirements (DB / Auth / AI / Storage / API)

Resolved to canonical decisions in the sections below.

| Area | Conflict | Canonical Decision |
| --- | --- | --- |
| Database | Local/Docker PostgreSQL (16+), self-hosted | Supabase Database (PostgreSQL), managed (§2) |
| Auth | Custom token/session auth, bcrypt/Argon2id + JWT `users.password_hash` | Supabase Auth (§3) |
| Storage | Private object storage w/ S3-style env vars (`STORAGE_*`) and local `STORAGE_PRIVATE_DIR` | Supabase Storage, private buckets + signed URLs (§4) |
| Vector search | Self-hosted pgvector extension | Supabase Database + pgvector (§2, §6) |
| RAG top-K | `System-Architecture.md` Top K = 5; `RAG-Architecture.md` Top K = 8–12; `Database-Schema.md` LIMIT 8 | See §7 unresolved question 1 |
| Attention levels | `PRD.md`: 4 levels (High Attention / Review / Informational / No Immediate Concern); `Database-Schema.md` + `DESIGN-System.md`: 3 levels (LOW/MEDIUM/HIGH); `PRD.md` §29 example JSON uses `"attention_level": "review"` | See §7 unresolved question 2 |
| API | Base path `/api/v1`, envelope `{success, data, message}` consistent across all docs | Maintained unchanged (§8) |

---

# 2. Database Decision

**Decision:** Use **Supabase Database** (managed PostgreSQL) as the single primary database.

- Keeps PostgreSQL semantics and SQL (do not describe Supabase as non-PostgreSQL).
- Stores all relational application data: users (profile mirror), documents, sections, clauses, chunks, analysis, attention areas, conversations, messages, citations, comparisons, actions, reports, audit events.
- **pgvector** is provided/enabled by Supabase Database and is the canonical vector store for document/clause/chunk embeddings (`VECTOR(1536)` reference dimension; must match the deployed embedding model).
- SQLAlchemy/Alembic remain the application data layer; connection uses `SUPABASE_DB_URL` (and `SUPABASE_DB_DIRECT_URL` where pooling is not desired). Supabase-provided connection pooling is used in production.
- Backups, point-in-time recovery, encryption at rest, and HA are owned by Supabase.

Rationale: removes self-hosted PostgreSQL/docker-compose Postgres operations, aligning with the hackathon deployment target while preserving all documented SQL-schema requirements.

---

# 3. Authentication Decision

**Decision:** Use **Supabase Auth** for all identity and session management.

- Supabase Auth owns: registration, login, logout, email verification, password recovery, hashing (bcrypt internally), JWT session tokens, token refresh, and password policy.
- The application `users` table (`Database-Schema.md` §5.1) becomes a profile/metadata mirror that links to the Supabase Auth user ID; `password_hash` / `is_verified` are owned by Supabase Auth and should not be stored or managed by the application.
- The API contract in `API-Specification.md` §4 (`/auth/register`, `/auth/login`, etc.) remains the application-facing contract but is implemented by delegating to Supabase Auth; the backend validates Supabase JWTs.
- Tokens must never be logged. Authorization remains application-side (`owner_id == current_user`) and must not be delegated to the frontend.

---

# 4. Storage Decision

**Decision:** Use **Supabase Storage** for all file persistence.

- All legal documents, processed files, and generated PDF reports are stored in **private Supabase Storage buckets**.
- Direct browser access uses server-side authorization + short-lived signed URLs only; no permanently public URLs, no public buckets for private legal documents.
- Supabase Storage object keys follow the documented hierarchy `users/{user_id}/documents/{document_id}/...`.
- File deletion must clean up Supabase Storage objects consistently with database soft-delete and the retention policy.

Replaces: `STORAGE_ENDPOINT` / `STORAGE_BUCKET` / `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` env vars and the local `STORAGE_PRIVATE_DIR` fallback. Supabase Storage credentials are provided via `SUPABASE_URL`, `SUPABASE_ANON_KEY` (user-scoped), and `SUPABASE_SERVICE_ROLE_KEY` (server-side only).

---

# 5. AI Decision

**Decision:** Keep the AI architecture as documented in `docs/04_AI/*`; no changes to prompts, citation validation, or evidence states.

Canonical AI stack:

- LLM API with structured outputs and document-grounded generation.
- Embeddings stored in Supabase Database via pgvector.
- Grounded answers with mandatory citation validation (never fabricated citations).
- Evidence states: `DOCUMENT-GROUNDED`, `GENERAL-INFORMATION`, `INSUFFICIENT-EVIDENCE`.
- Attention analysis uses "Areas Requiring Attention" language, never a numeric legal-risk score.
- Human-review recommendations for high-consequence or ambiguous matters; the product is not an AI lawyer.

Decision: evaluation rigor is unchanged (`AI-EVALUATION.md`, `EVALUATION-DATASET.md`, `Success-Metrics.md`).

---

# 6. RAG Decision

**Decision:** Use RAG with pgvector (Supabase Database) as the retrieval engine.

- Pipeline (canonical): Question → Query Embedding → Vector Search (pgvector) → Metadata Filtering (must scope to `owner_id`) → Evidence Set → Prompt Builder → LLM → Citation Validation.
- Chunking preserves legal meaning (section/clause/sub-clause/paragraph boundaries), ~500–1,000 tokens with modest overlap; vector index + metadata filtering + cached embeddings; never send the full document to the LLM.
- Metadata filtering is a critical security boundary preventing cross-user/cross-document retrieval.

---

# 7. Unresolved Questions

1. **RAG top-K value.** Sources disagree: `System-Architecture.md` §30 = 5, `RAG-Architecture.md` = 8–12, `Database-Schema.md` SQL = `LIMIT 8`. Recommend picking a single canonical value (default: 8) in `ARCHITECTURE-DECISIONS` and normalizing the three docs, then tune after evaluation of the dataset.

2. **Attention-level taxonomy.** `PRD.md` defines four levels (High Attention / Review / Informational / No Immediate Concern), while `Database-Schema.md` and `DESIGN-System.md` define three (LOW / MEDIUM / HIGH) and `PRD.md` example JSON uses `"attention_level": "review"`. Recommend a single taxonomy (either map 4→3 in the DB schema with display as 4, or extend the enum to 4). Must be resolved before schema migration and UI implementation.

3. **Repo-layout listings still reference `docker-compose.yml`** (`PRD.md` §65, `System-Architecture.md` §78). Since local Docker PostgreSQL is replaced by Supabase, decide whether to remove `docker-compose.yml` from the documented repository structure or retain it solely for backend-image concerns.

4. **`AI-EVALUATION.md` broken reference** to `docs/06_TESTING/Evaluation-Dataset.md`; actual file is `docs/04_AI/EVALUATION-DATASET.md`.

5. **`users.password_hash` field.** Documented in `Database-Schema.md` but superseded by Supabase Auth; confirm removal from the schema in favor of a `supabase_uid` FK mirror.

---

# 8. API Decision

**Decision:** Preserve the documented API contract unchanged except where noted.

- Base path `/api/v1`; backend FastAPI.
- Response envelope: success `{"success": true, "data": {}, "message": null}`; error `{"success": false, "error": {"code", "message"}}`.
- No stack traces, DB errors, internal paths, AI prompts, or API keys in responses.
- Endpoints implement Supabase Auth delegation for auth operations; all document/analysis/comparison/report endpoints authenticate via Supabase JWT and authorize by `owner_id`.

---

# 9. Security Decisions

- **HTTPS** required in production; CORS restricted to the deployed frontend domain (localhost allowed in dev only).
- **Private storage** only; short-lived signed URLs for browser access (§4).
- **Server-side authorization**: every query scoped to `owner_id`; optionally reinforce with PostgreSQL Row-Level Security (Supabase-native support).
- **Secrets**: never committed; repository contains only `.env.example`. Production secrets live in the deployment secret manager. `SUPABASE_SERVICE_ROLE_KEY` is server-side only; never a `NEXT_PUBLIC_*` variable.
- **File security** pipeline: size → MIME → structure validation → malware scan → private storage → processing; never execute uploads.
- **Prompt injection**: document text untrusted; system instructions isolated; structured-output validation + citation validation.
- **Safe logging / audit events**: request ID, endpoint, status, duration, job ID, error category; never log full documents, passwords, tokens, API keys, private prompts.
- **Rate limiting** on login, upload, AI questions, document analysis, comparison, report generation (tune after load testing).
- **Threat model** T1–T10 from `SECURITY-Architecture.md` remains canonical.
- **AI boundaries**: send only relevant evidence to the LLM; review provider data-retention/training policies before production; never transform AI interpretation into legal fact silently.

---

# 10. Rejected Alternatives

- **Local PostgreSQL / Docker PostgreSQL (self-hosted)** — rejected: requires infrastructure management and secret/backup ownership that the hackathon should not bear; Supabase Database provides PostgreSQL + pgvector + backups + HA.
- **Self-hosted Vector DB (e.g., Milvus, Weaviate, Pinecone-only)** — rejected: pgvector inside Supabase Database is sufficient for MVP scale and preserves the documented SQL/embedding model.
- **Custom authentication (bcrypt/Argon2id + JWT, `users.password_hash`, `AUTH_SECRET`)** — rejected in favor of Supabase Auth (managed identity, sessions, password policy, verification).
- **S3-compatible object storage or local filesystem (`STORAGE_*`, `STORAGE_PRIVATE_DIR`)** — rejected in favor of Supabase Storage private buckets with signed URLs.
- **Non-PostgreSQL databases (MongoDB, Firebase, etc.)** — rejected; not a fit for the documented relational + pgvector schema.
- **No vector search / pure LLM context** — rejected; RAG with validated citations is a product requirement.

---

# 11. Canonical Stack (Summary)

```text
Frontend:     Next.js + React + TypeScript + Tailwind CSS + shadcn/ui
Backend:      Python + FastAPI + Pydantic + SQLAlchemy + Alembic
Database:     Supabase Database (PostgreSQL) + pgvector
Auth:         Supabase Auth (JWT bearer sessions)
Storage:      Supabase Storage (private buckets, signed URLs)
AI:           LLM API (structured outputs, document-grounded) + embeddings (pgvector)
OCR:          OCR service/library appropriate to deployment environment
RAG:          Supabase pgvector + metadata filtering (owner-scoped) + citation validation
Deployment:   Next.js hosting + FastAPI container; no local/Docker PostgreSQL
```

---

# 12. Definition of Done

The architecture decisions are implemented when:

- [ ] Supabase Database connected (`SUPABASE_DB_URL`), pgvector enabled, Alembic migrations run
- [ ] Supabase Auth integrated (register, login, logout); backend validates Supabase JWTs
- [ ] Supabase Storage private buckets configured; document deletion removes objects
- [ ] RAG uses pgvector; every retrieval scoped to `owner_id`
- [ ] Top-K and attention-level taxonomy conflicts resolved (§7 Q1/Q2)
- [ ] `AI-EVALUATION.md` reference fixed; `docker-compose.yml` repo-layout decision resolved (§7 Q3/Q4)
- [ ] `users.password_hash` removed; `supabase_uid` mirror decision confirmed (§7 Q5)
- [ ] No local/Docker PostgreSQL, self-hosted pgvector, custom JWT, or S3/local-file storage references remain in `docs/`