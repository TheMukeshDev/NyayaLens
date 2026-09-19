# NyayaLens — Test Report

**Date:** 2026-09-19
**Rule applied:** a result is `PASS` only if the command was actually executed and succeeded. Anything without an executable harness, credentials, or service is `NOT EXECUTED` — never inferred.

---

## Backend — `cd backend && .venv/Scripts/python.exe -m pytest -o addopts="" -q`

`251 passed, 2 warnings in 18.88s`

| Category | Test file(s) | Status |
|---|---|---|
| Unit tests (all 251) | all `tests/test_*.py` | **PASS** |
| API tests | `test_health.py` (5), `test_errors.py` (5), `test_documents.py` (16), `test_qa.py` (18), `test_comparison.py` (19), `test_action_center.py` (21) | **PASS** |
| Authentication | `test_auth.py` (6: no token, valid, tampered, wrong secret, expired, malformed) | **PASS** |
| Authorization | `test_documents.py::TestAccessControl`, `test_comparison.py` (other-user 404), `test_action_center.py` (cross-user report), `test_qa.py::TestCrossUserIsolation` | **PASS** |
| Upload | `test_documents.py`, `test_storage.py` (38), `test_processing.py` (11) | **PASS** |
| Extraction | `test_processing.py` (11) | **PASS** |
| RAG | `test_retrieval.py` (10) | **PASS** |
| Citation | `test_qa.py` (`test_grounded_answer_with_only_fabricated_citations_abstains`, cross-user chunk rejection) | **PASS** |
| Comparison | `test_comparison.py` (19) | **PASS** |
| Prompt construction | `test_prompts.py` (69) | **PASS** |
| LLM/embedding providers | `test_llm_provider.py` (25) | **PASS** |
| Static analysis (supplementary) | `ruff check .` → `All checks passed!` | **PASS (after fix)** |
| Type checking (supplementary) | `mypy app` → `Success: no issues found in 90 source files` | **PASS (after fix)** |

> Supplementary note: `ruff` and `mypy` are configured in `pyproject.toml` but are **not** part of CI (CI runs only `pytest`). They initially reported **10 ruff E501** and **4 mypy** errors, all in `app/ai/action_center/service.py` (+1 test line). These were pre-existing (not introduced by this session). Fixed; re-run is green and the 251 tests still pass.

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
| Component tests | — | no `vitest`/`jest`/`@testing-library` and no test script in `frontend/package.json` | **NOT EXECUTED** |
| Accessibility tests | — | no `axe`/`jest-axe`/Playwright a11y runner configured | **NOT EXECUTED** |

`tests/README.md` claims frontend component/unit/E2E tests live under `frontend/`, but no harness or test files exist there.

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

| Step | Status | Notes |
|---|---|---|
| Landing | **PASS** | Executed against the running dev server (`http://localhost:55067/`): full page renders (accessibility snapshot), React hydrates (`__reactFiber$` present), the nav menu toggles `aria-expanded false→true` with a 6-link panel. |
| signup | **NOT EXECUTED** | No E2E framework configured. Would create a real user in the configured Supabase project (unwanted side effect) — not run without approval. |
| login | **NOT EXECUTED** | Same; also no backend. |
| upload | **NOT EXECUTED** | Backend needs `SUPABASE_SERVICE_ROLE_KEY` (still a placeholder) → Supabase client unavailable → endpoint would 500. |
| processing | **NOT EXECUTED** | Requires the worker + live DB + storage. |
| document overview | **NOT EXECUTED** | Requires an authenticated session and processed document. |
| summary | **NOT EXECUTED** | Requires processed document + LLM. |
| Q&A | **NOT EXECUTED** | Requires processed document + embeddings + LLM. |
| comparison | **NOT EXECUTED** | Requires two processed documents. |
| action center | **NOT EXECUTED** | Requires processed document + LLM. |
| report | **NOT EXECUTED** | Requires a READY report in private storage. |

An auth-gate behaviour was verified live: `/dashboard` and `/upload` both redirect to `/login?next=…` when signed out.

---

## Fixes applied

| Issue | Fix | Verification |
|---|---|---|
| `app/ai/action_center/service.py`: 9× E501 (lines >100) + 4 mypy errors (`item` reused for `dict` then `MonetaryTerm`; unguarded slice of `Any | None`) | Wrapped long lines/strings (implicit concatenation, output unchanged); renamed the monetary loop variable to `term`; guarded `original_text` with `isinstance(..., str)` before slicing | `ruff check .` → All checks passed; `mypy app` → no issues; `pytest` → 251 passed |
| `tests/test_action_center.py`: 1× E501 | Split the assertion string via implicit concatenation (same string) | `ruff` + `pytest` green |

No test failures were found in the executable suite.

---

## What would make the NOT EXECUTED rows runnable

1. **Database/RLS**: `docker compose up -d` (or `supabase start`) with pgvector, apply the migrations, and add two-user RLS integration tests.
2. **Storage RLS**: a live bucket test asserting user B cannot list/download user A's object and that signed URLs expire.
3. **Frontend component/a11y**: add Vitest + Testing Library (+ `axe`) and wire a `test` script.
4. **E2E**: add Playwright with a seeded test user and a backend configured with real `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_JWT_SECRET` and an LLM endpoint.
5. **Live-model AI**: provider credentials to test grounding/abstention against a real model.
