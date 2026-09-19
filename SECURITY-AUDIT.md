# NyayaLens — Security Audit

**Date:** 2026-09-19
**Scope:** Security-only review of the repository as it exists in the working tree.
**Method:** Source inspection + execution of the hermetic backend test suite
(`cd backend && .venv/Scripts/python.exe -m pytest -q` → **251 passed**) and
targeted runtime probes against the auth layer. No live Supabase project,
Postgres instance, or AI provider was available, so anything that requires the
deployed database/storage/browser could be inspected but **not exercised** —
those items are marked `NOT TESTED`, never `PASS`.

> Honesty rule applied throughout: a control is `PASS` only when it was verified
> by running code (tests or a runtime probe) **or** is a pure-static property
> that cannot be violated at runtime (e.g. "no `dangerouslySetInnerHTML` in the
> source"). Database/RLS/storage/browser-imposed controls are `NOT TESTED`.

---

## 1. Results summary

| # | Control | Status |
|---|---------|--------|
| 1 | Authentication | **PASS** |
| 2 | Authorization | **PASS** |
| 3 | IDOR (user A vs user B data) | **PASS** |
| 4 | Supabase RLS (application tables) | **NOT TESTED** |
| 5 | Storage RLS (private bucket) | **NOT TESTED** |
| 6 | Service-role key exposure | **PASS** |
| 7 | Environment variables / secret files | **FAIL → FIXED** |
| 8 | CORS | **PASS** |
| 9 | CSRF (where applicable) | **PASS (not applicable by design)** |
| 10 | XSS | **PASS** |
| 11 | SQL injection | **PASS** |
| 12 | File upload validation | **PASS** |
| 13 | Path traversal | **PASS** |
| 14 | Malicious files (malware / decompression bombs) | **FAIL** |
| 15 | Prompt injection | **PASS (design + unit), NOT TESTED vs live model** |
| 16 | RAG isolation | **PASS (app layer), NOT TESTED against live DB** |
| 17 | Citation validation | **PASS** |
| 18 | Rate limiting | **FAIL** |
| 19 | Error leakage | **PASS** |
| 20 | Logging hygiene | **PASS** |
| 21 | Sensitive data exposure | **FAIL (minor, owner-only)** |
| 22 | AI provider key handling | **PASS** |

Verification checklist requested by the task:

| Claim | Result |
|-------|--------|
| User A cannot access User B data | **PASS** (tests, §3) |
| Frontend cannot access service-role credentials | **PASS** for source + built bundle; git history **NOT TESTED** (§6) |
| Legal documents are not public | **PASS** by inspection; live bucket **NOT TESTED** (§5, §21) |
| AI keys are backend-only | **PASS** (§6, §22) |
| No full legal documents appear in logs | **PASS** by inspection + unit tests; runtime log sink **NOT TESTED** (§20) |

---

## 2. Authentication — PASS

Evidence:

- `backend/app/core/auth.py` verifies Supabase access tokens offline with
  HS256 only (`algorithms=["HS256"]`), requiring `exp` and `sub`, and requires
  `sub` to be a UUID. Invalid/expired/missing tokens raise 401 and the message
  never reveals why.
- `backend/tests/test_auth.py` passes: no token → 401 `AUTH_REQUIRED`; valid
  → 200; tampered/expired/wrong-secret/malformed → 401 `INVALID_CREDENTIALS`.
- Runtime probe (executed): a token shaped like the public Supabase `anon` key
  (signed with the project secret but **without** a `sub` claim) is **rejected**,
  and an `alg=none` token is **rejected**. This closes the obvious "use the
  public anon key as a bearer token" and algorithm-confusion paths.
- Passwords/MFA/password reset are owned by Supabase Auth; the backend never
  stores or logs credentials.

Hardening notes (not vulnerabilities): the verifier does not check the `aud`
or `iss` claims, and `role` from the token is recorded but not used for any
authorization decision (there are no admin endpoints; all access is
ownership-scoped).

## 3. Authorization & IDOR — PASS

Every business endpoint depends on `get_current_user`; only `/health` and
`/api/v1/ping` are unauthenticated. Identity always comes from the verified
token, never from the request body (`backend/app/api/routes/*.py`).

Ownership is enforced in the service/repository layer. Because the backend uses
the Supabase **service-role** client (which bypasses RLS), this application-level
scoping is the primary boundary:

- `BaseRepository._table(user_id)` refuses to build an owner-scoped query
  without a `user_id` (`backend/app/repositories/base.py`).
- `DocumentRepository.get_by_id_and_user`, `.transition`, `.find_duplicate`
  filter by `user_id`; `DocumentService._require_owned` raises
  `DocumentNotFoundError` (404) rather than 403, so existence is not leaked.
- Comparisons verify ownership of **both** documents before comparing.
- Action Center verifies document ownership; actions/reports are fetched with
  the owner predicate.
- Q&A retrieval and citation resolution pass the token-derived `user_id`.

Tests that actually exercise cross-user access (and pass):

- `backend/tests/test_documents.py` — cross-user read/status → 404, no
  existence leak.
- `backend/tests/test_comparison.py` — creating a comparison with another
  user's document → 404.
- `backend/tests/test_action_center.py` — user B cannot generate/read/download
  user A's report (404) and sees an empty report list.
- `backend/tests/test_qa.py` — a model-cited chunk belonging to another user is
  dropped; only the caller's chunk is returned.
- `backend/tests/test_retrieval.py` — retrieval never returns another user's
  chunks even when the content is near-identical.

## 4. Supabase RLS — NOT TESTED

Cannot be exercised without the deployed Postgres instance. Inspection of
`supabase/migrations/20260917000100_rls_policies.sql`:

- RLS is enabled on every application table (`users`, `user_preferences`,
  `documents`, `sections`, `clauses`, `document_chunks`, `analyses`,
  `attention_items`, `conversations`, `messages`, `citations`, `comparisons`,
  `comparison_changes`, `actions`, `reports`, `audit_logs`).
- Policies derive ownership from `auth.uid()` only; there are no policies keyed
  on client-supplied ids.
- `audit_logs` has RLS enabled with **no** policies and
  `revoke all ... from authenticated, anon` — service-role only.
- `document_chunks` was tightened in `20260917000300_embeddings.sql` to require
  both `user_id = auth.uid()` and `is_document_owner(document_id)`.
- `public.match_documents` is `security invoker` with `set search_path = public`
  and filters by an explicit `user_id` passed by the server; even if a client
  called it directly with someone else's `user_id`, RLS would still restrict
  rows to `auth.uid()`.
- `public.ensure_embedding_index` is `security definer` and is revoked from
  `public`/`authenticated` (service-role/DB-owner only).

**Residual risk / to verify on a live project:** that the migrations above were
actually applied (not merely present), that no additional permissive policy was
added out-of-band, and that `auto_expose_new_tables` behavior does not expose
future tables. Recommend an automated RLS integration test that mints two real
sessions and asserts cross-user reads return zero rows.

## 5. Storage RLS — NOT TESTED

`supabase/migrations/20260917000200_storage_legal_documents.sql` creates the
`legal-documents` bucket with `public = false`, a 20 MiB limit and an allowlist
of document MIME types, and adds per-owner policies on `storage.objects` keyed
on `(storage.foldername(name))[2] = auth.uid()::text`. Object keys are
`users/{user_id}/documents/{document_id}/...`, so path-derived ownership is
enforced by RLS as defense-in-depth. There are **no anon policies**.
The backend produces only short-lived signed URLs (`SIGNED_URL_EXPIRES_SECONDS`
default 900; report downloads 30 min) and never a permanent public URL.

Marked `NOT TESTED` because it requires the live Supabase Storage API to verify
the bucket is private and that a second user cannot download another user's
object. **This is the highest-value missing test.**

## 6. Service-role key & AI keys exposure — PASS

- The service-role key is read only in the backend
  (`backend/app/core/config.py`, `backend/app/core/supabase.py`); it is never a
  `NEXT_PUBLIC_*` variable.
- The frontend's Supabase clients use only the publishable anon key
  (`frontend/lib/supabase/client.ts`, `server.ts`). No frontend source under
  `frontend/app`, `frontend/lib`, or `frontend/components` references
  `SERVICE_ROLE`, `LLM_API_KEY`, or `EMBEDDING_API_KEY`.
- Built-bundle scan (`frontend/.next`): the only `sb_secret*` occurrence is the
  Supabase library's own key-prefix check (`e.startsWith("sb_secret_")`), not a
  key value. No `service_role`/`SERVICE_ROLE` material was found in the bundle.
- `backend/tests/test_llm_provider.py::test_keys_never_exposed_through_api_contract`
  asserts the generated OpenAPI document contains no `llm_api_key`,
  `embedding_api_key`, or `service_role_key` (passing).

**Not tested:** git history / CI secret stores (no `.git` directory is present
in this checkout), so historical accidental commits could not be ruled out.

## 7. Environment variables — FAIL (fixed)

**Finding (confirmed):** the root `.gitignore` contained an explicit
un-ignore for `.env.local`, and `backend/.gitignore` ignored only `.env`.
Together these made it possible to commit a `backend/.env.local` (or a root
`.env.local`) containing `SUPABASE_SERVICE_ROLE_KEY`, `LLM_API_KEY`, and
`EMBEDDING_API_KEY` — exactly the files a developer is likely to create
locally.

**Fix applied:**

- `.gitignore` — removed `!.env.local` and added a comment; templates only
  (`.env.example`, `.env.local.example`) remain committable.
- `backend/.gitignore` — now ignores `.env` **and** `.env.*`, with
  `!.env.example` allowed.

Note: a real root `.env` exists in the working tree (Supabase URL/anon key and a
DB connection string). It is covered by the `.env` ignore rule; it is a local
development file and was not modified.

## 8. CORS — PASS

`backend/app/main.py` configures `CORSMiddleware` with
`allow_origins=settings.cors_origin_list` (an explicit comma-separated
allowlist, default `http://localhost:3000,http://127.0.0.1:3000`) and
`allow_credentials=True`. There is no wildcard origin, so credentialed
cross-origin requests are not open to arbitrary sites.

Hardening note: `Settings` requires non-placeholder Supabase/AI credentials in
production but does **not** require `CORS_ORIGINS` to be non-localhost, so a
misconfigured production deploy could retain the localhost list (fails closed —
it would simply reject the real origin). Consider enforcing this in the
production validator.

## 9. CSRF — PASS (not applicable by design)

The backend API authenticates with a `Bearer` token in the `Authorization`
header (`frontend/lib/api/shared.ts`), not with cookies, so browsers will not
attach credentials cross-site and classic CSRF does not apply. Supabase session
cookies are used only for Next.js SSR/session refresh; Next.js Server Actions
(`frontend/app/**/actions.ts`) inherit the framework's same-origin protections,
and the only server action mutates the caller's own session (`signOut`). The
login redirect target is validated against open redirects
(`frontend/app/login/actions.ts::safeNext`).

## 10. XSS — PASS

- No `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function`, or
  `document.write` anywhere in the frontend source (verified by search).
- Document/AI output is rendered as React text nodes (e.g.
  `frontend/components/ask/ask-view.tsx`, `.../analysis/summary-view.tsx`), so
  it is escaped by React.
- The downloadable report is generated as `text/plain; charset=utf-8` and
  served via a signed object URL; it is not rendered as HTML.
- The backend sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, and a restrictive `Permissions-Policy`
  (`backend/app/core/security.py`). Note: no CSP is set; the frontend serves
  JSON-consuming client components, so CSP is a defense-in-depth improvement,
  not a demonstrated hole.

## 11. SQL injection — PASS

There is no string-built SQL from user input. Persistence uses the Supabase
PostgREST client with parameterized builders. The only raw SQL is inside
migration-defined functions:

- `match_documents` takes typed parameters (`vector`, `int`, `uuid`) and
  composes no SQL from them.
- `ensure_embedding_index(dim integer)` uses `format(... %s, dim)` but `dim` is
  a validated `integer` (rejected when `<= 0`) and the function is revoked from
  `public`/`authenticated`, so it is not client-reachable.

## 12. File upload validation — PASS

`backend/app/services/file_validation.py` enforces, server-side and independent
of client-supplied headers:

- extension allowlist (configurable) **and** magic-byte match
  (`%PDF-`, `PK\x03\x04`, `\xff\xd8\xff`, PNG signature) — a renamed executable
  or spoofed `Content-Type` is rejected;
- non-empty content and a size cap (`MAX_UPLOAD_SIZE_MB`, default 20);
- filename sanitization (basename only, strips path separators/control chars,
  neutralizes Windows reserved names, length-caps).

Duplicate uploads are rejected per-user by SHA-256. Tests in
`backend/tests/test_storage.py` and `test_documents.py` pass.

## 13. Path traversal — PASS

`sanitize_filename` reduces any client path (`C:\...`, `/etc/passwd.pdf`,
`../../lib/x.pdf`) to a bare basename; storage object keys are built only from
server-generated UUIDs (`users/{user_id}/documents/{document_id}/original`),
never from the filename. Verified by parametrized tests.

## 14. Malicious files — FAIL

- **No malware/AV scanning is implemented**, although `SECURITY.md` describes
  "malware scan" as part of the design (`MALWARE_DETECTED` error code exists but
  is never raised). Uploaded files are stored and later parsed regardless of
  intent. This is the main confirmed gap here.
- **No decompression-bomb guard.** DOCX (a ZIP) is parsed by `python-docx` and
  PDF by `pypdf` with no expansion/object-count limits. A 20 MiB upload can
  expand to far more in memory during parsing.
- Partially mitigated: images are decoded via Pillow before OCR (only RGB/L
  pixels reach tesseract), magic-byte validation blocks type spoofing, and the
  pipeline fails honestly rather than inventing text.

Recommend: run uploads through an AV scanner (or document the accepted risk), and
bound DOCX/PDF extraction (max uncompressed size / page / object limits).

## 15. Prompt injection — PASS (design + unit); live model NOT TESTED

- `backend/app/ai/prompts/core.py` establishes a strict hierarchy (system rules
  > task/RULES > user question > document text), explicitly labels uploaded
  documents as **untrusted data**, instructs the model to ignore instructions
  embedded in documents, and requires abstention over guessing.
- Document content is only ever placed inside an `<evidence>` fence in the
  **user** message; instructions live in the system message / labelled sections
  (`backend/app/ai/prompts/prompts.py`). The system prompt is immutable and
  shared by all tasks.
- Model output is schema-validated (`parse_structured_content`) and any
  failure → abstention, never a fabricated answer.
- Not tested: behaviour against a live adversarial model/endpoint. The
  structural separation and abstention path are verified by unit tests
  (`test_prompts.py`, `test_qa.py`, `test_action_center.py`).

## 16. RAG isolation — PASS (app layer); live DB NOT TESTED

Retrieval always injects the token-derived `user_id` into
`public.match_documents(p_user_id => ...)`, and the SQL function filters
`dc.user_id = p_user_id` in addition to RLS. `test_retrieval.py`
(`TestCrossUserIsolation`) and `test_qa.py` prove that near-identical documents
owned by another user are never returned. Confirming the *database* side of this
is the same live-RLS test recommended in §4.

## 17. Citation validation — PASS

`backend/app/ai/validators/citations.py` only accepts a cited chunk if it was in
the retrieved set **and** resolves via `CitationRepository.owned_chunks`, which
queries `document_chunks` filtered by `user_id` **and** `document_id`; the
resolver additionally re-checks both ids and requires section + page metadata.
Fabricated, cross-document, or cross-user citations are dropped, and a
"document-grounded" answer with zero surviving citations is converted to an
abstention. `test_qa.py` verifies both the drop and the abstention.

## 18. Rate limiting — FAIL

- There is **no HTTP-layer or per-user rate limiting** on the API. The
  `RATE_LIMITED` error code exists but is never used, and there is no
  middleware/dependency enforcing request budgets on upload, ask, compare,
  action-center, or report endpoints.
- The only throttling present is **outbound provider** throttling
  (`backend/app/ai/transport.py::RequestThrottle`), which defaults to
  `0 = unlimited` (`LLM_MAX_REQUESTS_PER_MINUTE`,
  `EMBEDDING_MAX_REQUESTS_PER_MINUTE`) and exists to protect upstream cost, not
  to protect the API.
- Supabase Auth applies its own limits to sign-in/sign-up (see
  `supabase/config.toml`), but that does not cover the backend endpoints.

Recommend a per-user/IP limiter at the reverse proxy or an app-level dependency
(bucket by user id + route), plus non-zero AI request budgets in production.

## 19. Error leakage — PASS

`backend/app/core/errors.py` funnels all failures through one envelope with
generic messages; unhandled exceptions log server-side and return
`INTERNAL_ERROR` with no stack trace. Validation errors expose only field
location + message (truncated to 20). Cross-user access returns 404, not 403, so
existence is not disclosed. `backend/tests/test_errors.py` asserts responses
contain no `Traceback`, no `app/` paths, and no test JWT secret.

## 20. Logging hygiene — PASS

- `backend/app/core/logging.py` emits structured JSON and whitelists only
  `request_id, method, path, status_code, duration_ms, error_code` (plus the
  log message). Query strings (e.g. the `user_context` parameter) are not
  logged — only the URL path.
- Reviewed every `logger.*` call site in `backend/app`: they log ids, counts,
  status and generic error text. Document content, prompts, tokens and API keys
  are not logged. Storage/LLM/embedding error classes carry generic messages.
- Report generation logs only the report id.
- Not tested: the production log sink/retention. Tracebacks are logged with
  `exc_info`; Python tracebacks contain code lines, not local variable values,
  so document text is not expected to appear — but this was not observed on a
  live run.

## 21. Sensitive data exposure — FAIL (minor, owner-only)

- The RLS migration comment states "storage_key and audit_logs are NOT exposed
  to clients", but `documents` (and `reports`) are granted table-level
  `select` to `authenticated`, and the RLS policy grants the owner the whole
  row — including `storage_key`. A signed-in user can therefore read their own
  `storage_key` through the anon-key/RLS path. This is **owner-only** (no
  cross-user access) and the value is derived from ids the user already knows,
  so there is no privilege gain; it is a policy/documentation mismatch, not a
  data breach. `audit_logs` is correctly revoked.
- The API projection (`DocumentOut`) correctly omits `storage_key`; this matters
  only for the direct-to-Supabase path.
- A real Supabase DB connection string and anon key are present in the local
  (gitignored) root `.env`. The anon key is public by design; the DB URL is a
  local secret and is now reliably ignored by the §7 fix.

Recommendation (not applied — requires a new DB migration and live validation):
`revoke select (storage_key) on public.documents, public.reports from authenticated;`
and update the migration comment. Left as a documented finding to avoid shipping
an unverified schema change from an audit that had no database to test against.

## 22. AI provider key handling — PASS

- `backend/app/core/config.py` holds `llm_api_key` / `embedding_api_key` as
  backend settings only; the frontend never reads them.
- Keys are sent only as `Authorization: Bearer` to the configured
  OpenAI-compatible endpoint over HTTPS, are never written to logs, and are not
  included in any error message or in the OpenAPI document (tested).
- Providers are constructed server-side (`build_llm_provider`,
  `build_embedding_provider`) from settings; no key is ever returned to a
  client.
- `Settings` refuses to start in production without non-placeholder Supabase
  and AI credentials.

---

## 3. Confirmed issues found and action taken

| # | Issue | Severity | Action |
|---|-------|----------|--------|
| 7 | `.env.local` un-ignored (root) and `backend/.gitignore` missing `.env.*`, enabling accidental commit of service-role/AI keys | High (secret leak) | **Fixed** in `.gitignore` and `backend/.gitignore` |
| 18 | No API rate limiting / per-user request budgets | Medium | Reported, **not fixed** (feature-sized; needs a deliberate design) |
| 14 | No malware scanning; no DOCX/PDF decompression bounds | Medium | Reported, **not fixed** |
| 21 | `documents.storage_key` / `reports.storage_key` selectable by owner vs. migration comment | Low | Reported, **not fixed** (needs a verified migration) |
| 4, 5 | RLS and Storage RLS could not be executed here | — | Reported as **NOT TESTED** with concrete test recommendations |

No unrelated features were added.

---

## 4. Recommended verification work (to convert NOT TESTED → PASS)

1. **RLS integration test** against a real project/agent with two sessions:
   assert cross-user `select` on `documents`, `sections`, `clauses`,
   `document_chunks`, `analyses`, `attention_items`, `actions`, `reports`,
   `comparisons`, and `match_documents` returns zero rows, and that
   `audit_logs` is unreadable.
2. **Storage integration test**: confirm `legal-documents` is private, that a
   second user's signed-in session cannot list/download another user's object,
   and that signed URLs expire.
3. **Secret-history scan** (gitleaks/trufflehog) over full git history and CI
   secret stores.
4. **Upload abuse test**: oversized body, DOCX zip bomb, malformed PDF, and
   macro-bearing files, plus confirming a transport-level request-size cap.
5. **Adversarial prompt-injection test** with a live model (instructions
   embedded in a document must not alter output or leak the system prompt).
6. **Rate-limit test** once a limiter exists (per-user and per-IP).
