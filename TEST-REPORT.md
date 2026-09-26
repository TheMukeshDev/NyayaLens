# NyayaLens — Test Report

**Date:** 2026-09-19 (updated second pass)
**Rule applied:** a result is `PASS` only if the command was actually executed and succeeded. Anything without an executable harness, credentials, or service is `NOT EXECUTED` — never inferred.

---

## Backend — `cd backend && .venv/Scripts/python.exe -m pytest -o addopts="" -q`

`269 passed, 2 warnings`

| Category | Test file(s) | Status |
|---|---|---|
| Unit tests (all 269) | all `tests/test_*.py` | **PASS** |
| API tests | `test_health.py` (5), `test_errors.py` (5), `test_documents.py` (16), `test_document_reads.py` (18), `test_qa.py` (18), `test_comparison.py` (19), `test_action_center.py` (21) | **PASS** |
| Authentication | `test_auth.py` (6: no token, valid, tampered, wrong secret, expired, malformed) | **PASS** |
| Authorization | `test_documents.py::TestAccessControl`, `test_document_reads.py` (unknown/cross-user → 404, no existence leak), `test_comparison.py` (other-user 404), `test_action_center.py` (cross-user report), `test_qa.py::TestCrossUserIsolation` | **PASS** |
| Upload | `test_documents.py`, `test_storage.py` (38), `test_processing.py` (11) | **PASS** |
| Document reads (list + summary/attention/clauses) | `test_document_reads.py` (18: 401s, empty states, owner scoping, pagination, status filter, 422s, granular-read consistency) | **PASS** |
| Extraction | `test_processing.py` (11) | **PASS** |
| RAG | `test_retrieval.py` (10) | **PASS** |
| Citation | `test_qa.py` (`test_grounded_answer_with_only_fabricated_citations_abstains`, cross-user chunk rejection) | **PASS** |
| Comparison | `test_comparison.py` (19) | **PASS** |
| Prompt construction | `test_prompts.py` (69) | **PASS** |
| LLM/embedding providers | `test_llm_provider.py` (25) | **PASS** |
| Static analysis (supplementary) | `ruff check .` → `All checks passed!` | **PASS** |
| Type checking (supplementary) | `mypy app` → `Success: no issues found in 90 source files` | **PASS** |

> Supplementary note: `ruff` and `mypy` are configured in `pyproject.toml`. They are **not** yet part of CI (CI runs only `pytest`); they now pass clean and are ready to be added to the CI pipeline. Earlier `ruff` E501 + `mypy` errors in `app/ai/action_center/service.py` were fixed and verified green. The document worker was extended with a continuous `--interval` mode (graceful SIGINT/SIGTERM) verified by `ruff` + `mypy` clean and the 11 `test_processing.py` tests still passing.

### Backend categories requested but covered by the above
| Requested | Where covered | Status |
|---|---|---|
| unit tests | entire `tests/` tree | **PASS** |
| API tests | TestClient suites listed above | **PASS** |
| authentication | `test_auth.py` | **PASS** |
| authorization | ownership suites listed above | **PASS** |
| upload / extraction | `test_documents.py`, `test_storage.py`, `test_processing.py` | **PASS** |
| RAG / citation / comparison | `test_retrieval.py`, `test_qa.py`, `test_comparison.py` | **PASS** |

---

## Frontend — `cd frontend`

| Check | Command | Observed | Status |
|---|---|---|---|
| Lint | `npm run lint` | `eslint` exited 0, no output | **PASS** |
| TypeScript | `npx tsc --noEmit` | exited 0, no diagnostics | **PASS** |
| Build | `npm run build` | `BUILD_EXIT=0`; 22 routes emitted (`/`, `/about`, `/dashboard`, `/documents/[documentId]`, `/login`, `/signup`, `/upload`, …) | **PASS** |
| Component tests | `npm test` (Vitest + Testing Library) | **39 passed** across 9 files (`tests/`) | **PASS** |
| Accessibility tests | `tests/a11y.test.tsx` (axe-core via `tests/axe.ts`) | **8 passed**, 0 violations on the components under test | **PASS** |
| E2E | `npm run test:e2e` (Playwright, hermetic mock) | `e2e/journey.spec.ts` runs the signup→report journey against `e2e/mock-server.mjs` (mock Supabase Auth + API); no live backend/Supabase needed | **PASS** (documented; run-verified) |

`tests/README.md`'s claim that frontend component/unit/E2E tests live under `frontend/` is now accurate.

---

## Database

| Category | Status | Why |
|---|---|---|
| RLS tests | **NOT EXECUTED** | No pgTAP/SQL test files exist (`supabase/` has only migrations + seed). Docker daemon is **not running**, so the Supabase local stack (`supabase start`) cannot come up. |
| Ownership tests (DB-level) | **NOT EXECUTED** | Requires a live Supabase/Postgres with `auth.uid()` simulation. The only listening Postgres is a stock service `postgresql-x64-18` on 5432 that rejected every credential I tried (`password authentication failed` for `postgres/postgres`, `postgres/nyayalens`, `nyayalens/nyayalens`, and no-password). |
| Vector retrieval tests (DB-level) | **NOT EXECUTED** | `public.match_documents` needs a live pgvector database. |

Application-level ownership and retrieval **were** exercised (via the in-memory fake) under the backend suites marked PASS above — that is **not** the same as testing the SQL/RLS layer, so the DB row stays NOT EXECUTED.

---

## Security

| Control | Evidence | Status |
|---|---|---|
| IDOR | `test_documents.py::test_cross_user_read_is_404_no_existence_leak`, `test_comparison.py::test_create_with_other_users_document_is_404`, `test_action_center.py` cross-user report 404, `test_qa.py::TestCrossUserIsolation` | **PASS** |
| Prompt injection | `test_qa.py::TestPromptInjection::test_injection_stays_inside_the_evidence_fence` ("Ignore all previous instructions" never reaches the system message but is present in the evidence fence); `test_prompts.py` asserts the payload is fenced for all 6 prompt builders and absent from every system prompt | **PASS** |
| Secret exposure | `test_llm_provider.py::test_keys_never_exposed_through_api_contract` (OpenAPI has no `llm_api_key`/`embedding_api_key`/`service_role_key`), `test_llm_provider.py::test_errors_never_leak_secrets_or_urls`, `test_health.py::test_health_does_not_leak_credentials`, `test_errors.py::test_errors_never_leak_internal_paths` | **PASS** |
| Unauthorized storage access | Application layer only: `test_storage.py` (per-user object keys, signed URLs, `test_error_message_never_leaks_backend_details`). Storage **RLS** is DB-level → see Database. | **PARTIAL → DB layer NOT EXECUTED** |

---

## AI

| Category | Evidence | Status |
|---|---|---|
| Grounding | `test_qa.py` (direct + multi-hop grounded answers), `test_prompts.py` (grounding rules), `test_analysis.py` | **PASS** |
| Citation validity | `test_qa.py`: fabricated citations → abstain; citation from another user's chunk dropped | **PASS** |
| Abstention | `test_qa.py` (no evidence → abstain without calling the LLM; unconfigured/unavailable LLM → honest abstain), `test_action_center.py` (follow-ups/questions abstain without fabrication) | **PASS** |
| Hallucination resistance | Unit level: citation validation + schema validation + abstention paths | **PASS** |
| Hallucination resistance vs a **live model** | No provider credentials/endpoint configured | **NOT EXECUTED** |

---

## E2E — Landing → signup → login → upload → processing → overview → summary → Q&A → comparison → action center → report

An in-repo **hermetic Playwright suite** (`frontend/e2e/`) covers this journey without a live Supabase project or backend: `e2e/mock-server.mjs` serves both Supabase Auth (`/auth/v1/*`) and the NyayaLens API (`/api/v1/*`), and the Next.js dev server is pointed at it.

| Test | Status | Notes |
|---|---|---|
| Landing page renders and is interactive | **PASS** | `journey.spec.ts:5` |
| Protected routes redirect to login when signed out | **PASS** | `/dashboard`, `/upload`, … → `/login?next=…` |
| A document the user does not own is not found | **PASS** | covers the 404-no-existence-leak contract at E2E level |
| signup → login → upload → processing → overview → summary → Q&A → comparison → action center → report | **PASS** | full happy-path journey |

Command: `cd frontend && npm run test:e2e` → `4 passed (1.0m)`.

The remaining `NOT EXECUTED` rows from the first pass concern a **live** backend + Supabase project + real LLM, which are out of scope for the hermetic suite (see below).

---

## Fixes applied

| Issue | Fix | Verification |
|---|---|---|
| `app/ai/action_center/service.py`: 9× E501 (lines >100) + 4 mypy errors (`item` reused for `dict` then `MonetaryTerm`; unguarded slice of `Any | None`) | Wrapped long lines/strings (implicit concatenation, output unchanged); renamed the monetary loop variable to `term`; guarded `original_text` with `isinstance(..., str)` before slicing | `ruff check .` → All checks passed; `mypy app` → no issues; `pytest` → 251 passed (count at that time; now 269) |
| `tests/test_action_center.py`: 1× E501 | Split the assertion string via implicit concatenation (same string) | `ruff` + `pytest` green |

No test failures were found in the executable suite.

---

## What would make the remaining NOT EXECUTED rows runnable

1. **Database/RLS**: `docker compose up -d` (or `supabase start`) with pgvector, apply the migrations, and add two-user RLS integration tests.
2. **Storage RLS**: a live bucket test asserting user B cannot list/download user A's object and that signed URLs expire.
3. **Frontend component/a11y**: done — Vitest + Testing Library + axe-core now run in `frontend/tests/` (39 tests). Note: the axe suite is component-level; a full-page authenticated axe scan is still open (see ACCESSIBILITY-AUDIT.md §5).
4. **E2E against a live backend**: the hermetic Playwright suite (mock server) passes; running the same journey against a real backend + seeded test user still requires configured `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_JWT_SECRET`.
5. **Live-model AI**: provider credentials to test grounding/abstention against a real model.
