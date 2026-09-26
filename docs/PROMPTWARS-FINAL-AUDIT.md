# NyayaLens — PromptWars Final Audit

**Audit date:** 2026-09-19
**Repo:** github.com/TheMukeshDev/NyayaLens (branch `main`)
**Commit audited:** `55447b7` — single commit ("feat: add storage for legal documents with RLS policies"), working tree clean
**Method:** direct source inspection of every layer (backend, frontend, Supabase migrations, tests, CI, docs) plus local execution of the backend suite, frontend suite, lint, and production build; GitHub Actions run `35439274575` verified green.

This audit evaluates the **actual implementation**. Nothing in this report is inferred from documentation; every claim below cites a file that was read or a command that was run.

---

## 0. Component verification checklist

| Item | Verdict | Evidence |
|---|---|---|
| GitHub repository | **PASS** | `TheMukeshDev/NyayaLens` exists on GitHub; one commit; CI run `35439274575` green (frontend 39s, backend 13s) |
| README | **FAIL** | `README.md:90` still says "No business features implemented yet"; `README.md:40-41` labels storage and AI as "(planned)"; `README.md:42` omits disabled endpoints; references `RESPONSIBLE_AI.md`, `LICENSE`, `DOCS/README.md` that do not exist; documents a local-Postgres docker path no longer required |
| Frontend | **PASS** | Real Next.js app; `npm run build` green (17 routes + proxy), `npm run lint` clean, `npm test` 39 passed; only anon key used (`lib/supabase/client.ts`) |
| Backend | **PASS** | Real FastAPI app; 251 tests passing locally (22.0s, 2 library deprecation warnings only) |
| Supabase | **PASS** | 5 real migrations (schema, RLS, storage, embeddings, actions.source) + `seed.sql`; project ref appears in gitignored `.env` only, never in the repo |
| RLS | **PASS** | RLS enabled on every exposed table; owner-scoped policies only (`rls_policies.sql`), audit_logs has zero client policies |
| Storage | **PASS** | Private `legal-documents` bucket, path-derived per-owner policies, no anon policies, short-lived signed URLs only (`storage_legal_documents.sql`, `services/storage/supabase.py`) |
| Authentication | **NOT TESTED** (live) | Backend verifies Supabase JWT offline (`core/auth.py`); no Supabase sign-in flow is exercised end-to-end anywhere; requires `SUPABASE_JWT_SECRET` which is unset in the tree's env templates |
| Document processing | **PASS** (pipeline) / **PARTIAL** (ops) | Real extract→sections→clauses→entities→chunks pipeline (pypdf / python-docx / tesseract OCR); but processing is only driven by a **manual CLI poller** (`workers/document_worker.py`) with no scheduler/queue |
| AI | **PASS** (mechanism) / **NOT TESTED** (live) | Real LLM/embedding providers with a strict abstention model; no keys are configured anywhere, so live generation is not exercised |
| RAG | **PASS** (mechanism) / **NOT TESTED** (live) | pgvector retrieval, ownership-scoped in SQL, HNSW index via `ensure_embedding_index` (manual step); default dev provider is a documented deterministic hashing provider |
| Citations | **PASS** | Backend-resolved from retrieved chunks only, owner+document+section+page required; anti-fabrication tests pass |
| Comparison | **PASS** | Deterministic change detection + optional LLM explanation; ownership gate on both documents; tests pass |
| Action Center | **PASS** | Deterministic review checklist from attention items, traceable follow-ups, important dates, professional questions; tests pass |
| Report | **PASS** | Assembled review report stored as private object, downloaded only via signed URL; tests pass |
| Accessibility | **PARTIAL** | Skip-link, aria labels, focus management, reduced-motion, axe tests on 8 components all real; no automated coverage of authenticated pages; `ACCESSIBILITY-AUDIT.md` is stale |
| Security | **PASS** (with caveats) | See §2 |
| Tests | **PASS** | 251 backend (hermetic) + 39 frontend tests green locally; E2E harness exists but runs against a mock and is not executed in CI or in this audit (**NOT TESTED**) |

---

## 1. Problem Statement Alignment — **PASS** (with gaps)

The problem statement (`docs/01_PRODUCT/Problem-Statement.md`) targets responsible AI legal-document assistance. Every core capability maps to real code:

- Plain-language understanding — `ai/analysis/service.py` (summary, clause extraction, attention), persisted and honest.
- Evidence-backed answers — `ai/qa/service.py` full pipeline with validated citations.
- Version comparison — `ai/comparison/service.py` (deterministic ADDED/REMOVED/MODIFIED/UNCHANGED).
- Next steps / checklist / professional questions — `ai/action_center/service.py`.
- Important dates and monetary terms — deterministic extraction (`document_processing/entities.py`).

**Gap:** the *surfacing* of analysis is incomplete — the backend does not implement `GET /documents` (list) or `GET /documents/{id}/summary|attention|clauses`, which the frontend calls. The analysis data is generated and stored, `get_understanding()` exists (`ai/analysis/service.py:295`), but no HTTP route serves it. In a live deployment those pages would render their honest "not available" empty states, so a core part of the product story cannot currently be completed end-to-end.

---

## 2. Security — **PASS** (with caveats)

Verified green:
- **No committed secrets.** `git show HEAD:.env` → absent; `git ls-files` contains only `.env.example`, `backend/.env.example`, `frontend/.env.local.example`. The one commit has no history to leak secrets. Real values exist only in gitignored local `.env` / `.env.local` files.
- **No service-role key in the frontend.** Only `NEXT_PUBLIC_*` anon-key clients (`lib/supabase/client.ts`, `server.ts`, `proxy.ts`); grep for `service_role`/`SERVICE_ROLE` in `frontend/` returns only the doc comment in `.env.local.example`.
- **Service-role key backend-only** (`core/supabase.py`, `core/config.py:50-51`), with owner-scoping enforced in repository code (`repositories/base.py`).
- **RLS** owner-scoped on all tables; helper functions non-recursive (`rls_policies.sql`).
- **Private storage** with path-derived ownership and signed URLs only.
- **Hardened error envelope, no stack traces/secrets** (`core/errors.py`), token verification offline with strict claims (`core/auth.py`), CORS restricted, security headers middleware, JWT handling never logs secrets — all covered by passing tests.

Caveats (documented, not silent):
- `SECURITY.md:29` claims "malware scan" is implemented — it is not. `services/file_validation.py` validates extension/magic bytes/size/filename only. The repo's own `SECURITY-AUDIT.md` row 14 is honest about this (FAIL); the top-level `SECURITY.md` overstates it.
- `rls_policies.sql:480-494` grants table-level CRUD to `authenticated` (including the `documents.storage_key` column) while the comment claims column-level tightness; `storage_key` is an internal path, not a secret, but the comment overstates the grant model.
- The committed `.freebuff/` agent-log directory should be moved out of the repo or gitignored.

---

## 3. Accessibility — **PASS** (foundation) — verification partial

- Present and real: skip link + `#main-content` (`ui/skip-link.tsx`), labeled fields with `aria-describedby`/`aria-invalid`, `role="log"` + `aria-live` conversation, focus-trapping `Dialog` with Escape, focus-visible outlines, `prefers-reduced-motion` handling, AA contrast token.
- `tests/a11y.test.tsx` runs axe-core on 8 components; `tests/axe.ts` honestly disables only `color-contrast` (jsdom cannot compute it).
- **NOT TESTED:** authenticated workspace pages have no automated a11y coverage (no live Supabase session), and the E2E suite does not run axe. This is disclosed in `ACCESSIBILITY-AUDIT.md`, which is otherwise stale (it denies the test harness that now exists — the subtree was added after that audit).

---

## 4. Code Quality — **PASS**

- Backend: typed (`mypy strict` configured), modular services/repositories/Prompts, consistent error handling, honest "never fabricate" design, schema-validated outputs. Ruff-flavored formatting.
- Frontend: TypeScript, separated API layer (`lib/api/{shared,client,server}.ts`), consistent component conventions.
- `npm run lint` clean locally (CI also lint+build green).
- Negative evidence found: `.freebuff/` committed cruft; the FastAPI `_IncludedRouter` output (normal for this FastAPI build) produced no user-visible problem; deprecation warnings come from library internals, not project code.

---

## 5. Efficiency — **NOT TESTED**

The architecture is sound (pgvector HNSW planned via `ensure_embedding_index`, retrieval bounded to `top_k 8-12`, embedding batching, LLM/embedding timeouts + retries + throttles). But:
- The HNSW vector index is **not created automatically**; it requires a manual worker invocation with a known embedding dimension.
- The shipped default embedding provider is deterministic hashing (dev/hermetic), not a semantic model.
- No load/performance benchmarks or latency measurements exist anywhere.

Without any measured performance evidence this criterion cannot be marked PASS, and the design is good enough that FAIL would be wrong, so it is **NOT TESTED**.

---

## 6. Testing — **PASS** (core) — CI completeness partial

- **Backend:** 251 tests, all passing locally (verified by running `pytest`). Hermetic (fake Supabase/LLM/OCR/transport — no network or DB), substantive (cross-user isolation, citation anti-fabrication, injection fencing, abstention, secret non-leakage, storage, prompts). No skips/xfails.
- **Frontend:** 39 vitest tests passing locally (verified by running `npm test`), incl. axe a11y.
- **E2E:** real Playwright suite (`frontend/e2e/journey.spec.ts`, full signup→report journey) but against a **mock** server (`e2e/mock-server.mjs`) — does not validate real-API compatibility and is **NOT TESTED** here (not executed in this audit).
- **CI (**`.github/workflows/ci.yml`**):** runs backend pytest + frontend lint/build only. Frontend unit tests, E2E, `tsc --noEmit`, ruff, and mypy are **not** in CI.
- `TEST-REPORT.md` — backend numbers are accurate (matches the 251/frontend-39 runs), but lines 49-52 and 96-105 claim **no vitest/axe/Playwright harness exists**, which is false for the committed tree. It under-reports rather than fabricates, but it is stale and contradictory.

---

## 7. Responsible AI — **PASS**

Genuinely strong and verified in code, not just docs:
- Abstention everywhere the model cannot answer: no evidence → `INSUFFICIENT-EVIDENCE` **without calling the LLM**; LLM unconfigured/unavailable/fails schema validation → controlled abstention reasons; never a guess (`ai/qa/service.py`, `ai/analysis/service.py`, `ai/action_center/service.py`, `ai/comparison/service.py`).
- Explicit no-legal-advice framing in prompts (`ai/prompts/core.py`) and visible disclaimers in the UI and the generated report.
- No "legal score", no safe/illegal verdict, no outcome promises (report and schemas).
- Dates and monetary amounts come from deterministic extraction, not the model.
- `docs/05_SECURITY/RESPONSIBLE-AI.md` commitments match the code.

---

## 8. Evidence grounding — **PASS**

- Retrieval is pgvector cosine search **inside a SQL ownership filter** (`match_documents`, `repositories/citations.py`, `ai/rag/retrieval.py`), with a relevance floor (`retrieval_min_similarity=0.35`), a second-chance concept-query pass, and reranking.
- Answers marked `GENERAL_INFORMATION` only when appropriate; otherwise grounded.
- **Live model quality is NOT TESTED** (no keys configured, no eval harness) — the mechanism is real, its quality unmeasured.

---

## 9. Citation reliability — **PASS**

- Citations are validated backend-side from the **retrieved chunk set only** (`ai/validators/citations.py`): existence, document membership, ownership, section + page metadata all required; unverifiable citations are dropped; if none survive, the service abstains.
- Comparison citations resolve to the exact persisted clause on the correct side.
- Tests assert fabricated/cross-document citations never surface.
- **Live evaluation of citation accuracy is NOT TESTED** (targets in `docs/04_AI/CITATION-Strategy.md` are labelled targets, not measured results).

---

## 10. User experience — **FAIL** (end-to-end)

The UI itself is well built and honest (real pages, graceful empty states, real API layer, no fake data). However, as shipped it cannot deliver its core journey:

- Dashboard and the summary/attention/clauses pages call endpoints the backend does not implement (`GET /documents`, `/documents/{id}/summary|attention|clauses`), so a live deployment renders "not available" states for the primary analysis surfacing.
- No process automatically advances documents past `UPLOADED` (the worker is a manual CLI); no queue/scheduler.
- No LLM/embedding keys or JWT secret are configured anywhere, so in any deployed instance AI features abstain and authenticated API calls fail unless an operator supplies env vars.

The markdown baseline, component quality, progressive disclosure, and accessibility affordances are good; the **end-to-end product flow is not currently functional**, which is why this criterion fails.

---

## A. What is actually complete

1. **Secure Supabase foundation** — 5 real migrations: schema, complete owner-scoped RLS, private storage bucket with per-user policies, pgvector embeddings layer, actions source column; plus a demo seed.
2. **Real backend business logic** — JWT auth verification, upload + validation, PDF/DOCX/OCR extraction, section/clause detection, entity extraction, chunking, embedding abstraction, pgvector retrieval, grounded Q&A with citation validation, two-document comparison, Action Center, professional questions, review-report generation, audit logging.
3. **Real frontend** — marketing + auth + workspace pages, working upload/status/ask/compare/actions/reports/settings wiring, honest empty and error states, anon-key-only Supabase clients, a11y affordances.
4. **Substantive tests** — 251 backend + 39 frontend tests, all passing, hermetic, asserting real security/honesty behavior.
5. **Green CI + build** — GitHub Actions green; production build and lint clean.
6. **Integrity guarantees** — no committed secrets, no service-role key in the frontend, no fake AI answers, no fake citations, no fabricated statistics, no local PostgreSQL runtime dependency, no duplicate project or frontend/backend.

## B. What is partially complete

1. **Analysis surfacing** — data is produced and persisted, but `GET /documents`, `/summary`, `/attention`, `/clauses` endpoints are missing (UI degrades honestly).
2. **Ops/deployment** — processing worker is manual, no scheduler, no Dockerfiles/manifests, CORS dev-only.
3. **Configuration for live operation** — no JWT secret / LLM / embedding env anywhere (intentional abstention, but nothing to verify live behavior).
4. **CI completeness** — frontend unit + E2E, `tsc`, ruff, mypy not run in CI.
5. **Accessibility verification depth** — component axe tests real; authenticated pages uncovered.
6. **Documentation accuracy** — README, `main.py` docstring, `TEST-REPORT.md`, `ACCESSIBILITY-AUDIT.md`, `SECURITY.md` (malware-scan claim) are stale or contradictory.
7. **RLS grant model** — table-level grants to `authenticated` expose `storage_key` column despite a comment implying column-level tightness.

## C. What is missing

1. Document-list and analysis-read endpoints (`GET /documents`, `/summary`, `/attention`, `/clauses`).
2. Automated document-processing trigger (scheduler/queue/worker deployment).
3. Malware/virus scanning (claimed in `SECURITY.md`, not implemented).
4. Evaluation harness and dataset (present only as plans in `docs/04_AI/`; `tests/` is reserved).
5. Production deployment artifacts (Dockerfiles, hosting/URL/CORS config).
6. Conversation/message API (schema exists; no routes).
7. `LICENSE`, `RESPONSIBLE_AI.md`, `DOCS/README.md` — referenced by README, absent.

## D. Critical issues

1. **Core feature gap:** The frontend calls list/summary/attention/clauses endpoints that the backend never implements — the product's headline analysis view cannot be reached in a real deployment (only in E2E via the mock server).
2. **No automatic processing:** documents stay in `UPLOADED` forever unless an operator manually runs the CLI worker; nothing reproduces this automatically.
3. **Not runnable end-to-end as configured:** no JWT secret, LLM URL/model/key, or embedding provider values anywhere, so auth can 401 and every AI feature abstains without operator configuration.
4. **Stale/false documentation in the submission:** README claims "no business features", `TEST-REPORT.md` denies the frontend test harness that exists, `SECURITY.md` overstates malware scanning — these will mislead evaluators.

## E. Submission checklist

Before submitting:
1. **Close the API gap** — implement `GET /api/v1/documents` and `GET /documents/{id}/summary|attention|clauses` (services already exist: `DocumentRepository` listing + `DocumentUnderstandingService.get_understanding()`), or explicitly gate/hide the affected UI.
2. **Wire processing into ops** — document (and ideally automate) running `python -m app.workers.document_worker`; add a `--ensure-embedding-index` step to any deployment runbook.
3. **Provide real runtime env** — supply JWT secret + LLM/embedding config for a staging environment, or clearly state the app runs in "abstention mode" without them.
4. **Fix stale docs** — update README (status/tech-stack/missing-file references), `main.py` docstring, `TEST-REPORT.md` frontend/E2E rows, `ACCESSIBILITY-AUDIT.md`, and `SECURITY.md` (remove the unverified malware-scan claim or implement one).
5. **Extend CI** — add `npm test`, E2E, `tsc --noEmit`, and backend `ruff`/`mypy` to `.github/workflows/ci.yml`.
6. **Minor hygiene** — remove `.freebuff/` from the repo or gitignore it; align the RLS grant comment with the actual table-level grants (or restrict `storage_key`); add the missing `LICENSE`/`RESPONSIBLE_AI.md` files the README references.
7. **Mandatory security re-check before push** — run a comprehensive secret scan on the final diff; the real Supabase URL/anon key/DB password currently live only in gitignored `.env` / `frontend/.env.local` and must stay that way.

---

## F. Remediation status (addendum — second pass, 2026-09-19)

| # | Issue | Status | Evidence |
|---|-------|--------|----------|
| 1 | API gap (`GET /api/v1/documents`, `GET /documents/{id}/summary\|attention\|clauses`) | **DONE** | New routes `backend/app/api/routes/documents.py` + `analysis.py`; `18` new tests in `backend/tests/test_document_reads.py`; dashboard comment updated. Response shapes match the frontend TS contract (`DocumentListData`, `{items}` for attention/clauses, `Partial<UnderstandingSummary>`). |
| 2 | Worker not wired into ops | **DONE** | `document_worker.py` gains `--interval N` (continuous poll, graceful SIGINT/SIGTERM); runbook added to `docs/03_TECH/DEPLOYMENT.md` §11 (`--ensure-embedding-index` once, then `--interval` under a supervisor; exactly one worker per project). |
| 3 | No runtime env / abstention mode | **DONE (documentation)** | `DEPLOYMENT.md` §7 documents the exact variable set and states the abstention behaviour when AI vars are unset; `README.md` Quick Start covers `.env` filling. Live env provisioning still requires your secrets. |
| 4 | Stale docs | **DONE** | `README.md` rewritten (status/tech-stack/structure); `main.py` docstring updated; `TEST-REPORT.md` refreshed to 269 backend + 39 frontend + 4 E2E; `ACCESSIBILITY-AUDIT.md` tooling/recommendations updated; `SECURITY.md` malware-scan claim corrected. |
| 5 | CI coverage | **DONE** | `.github/workflows/ci.yml` now runs `npm test`, `npx tsc --noEmit`, Playwright E2E, `ruff check .`, `mypy app`. |
| 6 | Hygiene | **DONE** | `.freebuff/` untracked + gitignored; RLS grant comment in `supabase/migrations/20260917000100_rls_policies.sql` now describes the actual table-level grants honestly; `RESPONSIBLE_AI.md` and `docs/README.md` created. `LICENSE` intentionally left as "TBD" (owner decision). |
| 7 | Security re-check | **DONE** | Regression: backend `269 passed`; `ruff check .` clean; `mypy app` clean (91 files); frontend lint/build clean, Vitest 39 passed, Playwright E2E 4 passed; secret scan over the full diff returned no matches; secrets remain only in gitignored `.env` / `frontend/.env.local`. |

---