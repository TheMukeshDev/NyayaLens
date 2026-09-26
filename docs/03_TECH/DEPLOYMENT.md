# NyayaLens — Deployment Specification

**Version:** 1.0

---

# 1. Deployment Objective

NyayaLens should be deployed as a secure web application consisting of:

```text
Web Frontend
+
API Backend
+
Supabase Database (PostgreSQL + pgvector)
+
Supabase Storage (private buckets)
+
AI Services
```

---

# 2. Production Architecture

```text id="7s3e5q"
                    Internet
                       │
                       ▼
                  HTTPS / CDN
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
Next.js Web          FastAPI API
             │                   │
             │          ┌────────┼─────────┐
             │          ▼        ▼         ▼
             │   Supabase DB  Supabase   AI APIs
             │   PostgreSQL    Storage
             │   + pgvector
             │
             └───────────────┐
                             ▼
                           User
```

---

# 3. Frontend Deployment

Recommended:

```text
Next.js
```

Deploy on a platform supporting Next.js. The production setup is **Vercel**, as
a project whose **Root Directory is `frontend/`**, from the same repository as
the backend. Two projects, one repo:

```text
Vercel project "nyayalen"      -> Root Directory: frontend/
Vercel project "nyaya-lens-api" -> Root Directory: backend/
```

The frontend should use environment variables for:

```text
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_API_URL
```

`NEXT_PUBLIC_*` values are inlined into the client bundle **at build time**, so
they must be present in the project's build environment, not only at runtime.

If `NEXT_PUBLIC_API_URL` is left empty, the browser instead calls the
same-origin path `/backend/api/v1/...` and `next.config.ts` proxies it to
`API_PROXY_TARGET`. That fallback needs no CORS configuration and is useful
when the backend origin is not yet known, but every request then pays a
server-side hop, so set `NEXT_PUBLIC_API_URL` for production.

Never expose private backend secrets through `NEXT_PUBLIC_*` variables.

---

# 4. Backend Deployment

Backend:

```text
Python
FastAPI
```

Deploy using:

```text
Docker
```

Recommended production process:

```text
Build Docker Image
  ↓
Run FastAPI
  ↓
Health Check
  ↓
Deploy
```

## 4.1 Serverless deployment (Vercel)

The FastAPI app is also deployable to Vercel as a **Python function**, with
**Root Directory `backend/`**. This is the cheapest way to run the API and needs
no container hosting, but it changes three things:

1. **The app must be importable as an ASGI callable.** `backend/api/[[...path]].py`
   is a standard-library bridge: it forwards the incoming Vercel request to the
   FastAPI app (`app.main:app`) and streams the response back. No third-party
   server adapter is required.
2. **There is no long-lived process.** No in-process scheduler, no background
   worker thread, no connection kept warm between requests. Everything must be
   reachable from an HTTP request. See §11.
3. **Configuration comes from environment variables only.** `backend/vercel.json`
   pins the function (`maxDuration: 60`, 1 GB memory) and declares the scheduled
   processing drain. `backend/.python-version` pins the runtime to the same
   Python version CI uses.

Required production environment variables for the backend project:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
FRONTEND_URL
BACKEND_URL
CORS_ORIGINS           # the frontend's public origin
CRON_SECRET            # REQUIRED in production; see §11
ENVIRONMENT=production
```

Startup validation fails fast when a production deployment is missing a secret,
so a misconfigured deploy returns a clear 5xx instead of failing silently on
the first authenticated request.

### Function limits to design around

* **Request body size.** Vercel rejects large request bodies (about 4.5 MB).
  The upload path therefore never streams a file through the API — see §6.1.
* **Execution time.** A single invocation may run for at most `maxDuration`
  seconds. Long document processing is started per document and polled, not
  held open in one request.
* **Ephemeral filesystem.** Nothing may be written to disk and expected to
  survive between invocations; all durable state lives in Supabase.

### Health check

`GET /health` is exposed both at `/api/v1/health` and, via a rewrite in
`backend/vercel.json`, at `/health` so it can be pointed at directly.


---

# 5. Database

Use:

```text
Supabase Database (PostgreSQL)
+
pgvector
```

Production database requirements:

* Encryption in transit (Supabase provides TLS)
* Encryption at rest
* Automated backups (Supabase manages)
* Restricted network access
* Strong credentials
* Migration management
* Connection pooling (Supabase provides)

---

# 6. Storage

Legal documents must be stored in **private** Supabase Storage buckets.

Requirements:

```text
Private bucket (Supabase Storage)
No public access
Server-side authorization
Short-lived signed URLs where required
Encryption
Lifecycle/retention rules
```

Do not place uploaded legal documents inside the public frontend assets directory.

---

# 7. Environment Variables

The canonical template is the repository-root `.env.example` (mirrored at
`backend/.env.example`); every variable below is documented there. Key values:

```text
SUPABASE_URL=
SUPABASE_ANON_KEY=            # browser-safe, NEXT_PUBLIC_ in the frontend
SUPABASE_SERVICE_ROLE_KEY=    # backend-only, bypasses RLS
SUPABASE_JWT_SECRET=          # used to verify Supabase Auth access tokens
LLM_PROVIDER=                 # openai-compatible
LLM_MODEL=
LLM_API_URL=
LLM_API_KEY=                  # backend-only
EMBEDDING_PROVIDER=           # deterministic (dev) | openai-compatible (prod)
EMBEDDING_MODEL=
EMBEDDING_API_URL=
EMBEDDING_API_KEY=            # backend-only
CORS_ORIGINS=                 # exactly the deployed frontend origin(s)
CRON_SECRET=                  # guards the scheduled processing drain (§11)
API_PROXY_TARGET=             # frontend-only, server-side; see §3
```

Runtime behaviour when AI variables are unset: the API still serves all
endpoints, but AI-producing features abstain honestly (no fabricated output)
and the embedding provider falls back to the deterministic dev provider.

Secrets must exist only in deployment secret management.

Never commit them to Git.

---

# 8. Environment Separation

Maintain separate:

```text
Development
Staging
Production
```

Each environment should have separate:

* Database
* Storage
* Credentials
* API keys
* Configuration

---

# 9. Docker

Backend Docker image should:

* Use a minimal production base image
* Run as a non-root user where practical
* Install only required dependencies
* Avoid development secrets
* Define a health check
* Use environment-based configuration

---

# 10. Database Migrations

Schema is owned as SQL migrations under `supabase/migrations/`, applied with
the Supabase CLI (no alembic/alembic_botgen — the API is Supabase-native):

```text
supabase db push            # applies supabase/migrations/ to the linked project
```

Deployment flow:

```text
Build
 ↓
Apply migrations (supabase db push)
 ↓
Start application
 ↓
Health check
```

Migrations (which also enable RLS and grants) must be reviewed before
production execution.

---

# 11. Background Workers

Document processing must not block normal API requests.

Architecture:

```text
Upload API
 ↓
Create Job
 ↓
Queue / Worker
 ↓
Document Processing
 ↓
Database Update
 ↓
READY
```

The implemented worker is a single process that drains `UPLOADED` documents
through the deterministic pipeline. Operations runbook:

```text
# 1. Once, after the embedding model/dimension is configured:
cd backend
python -m app.workers.document_worker --ensure-embedding-index

# 2. Always-on single worker (see below for process supervisors):
python -m app.workers.document_worker --interval 30
```

- `--interval N` polls forever (sleeping N seconds between batches) and stops
  cleanly on `SIGINT`/`SIGTERM`; omit it for a one-shot cron-style batch.
- Run **exactly one** polling worker per project environment. The pipeline is
  not horizontally scalable while `UPLOADED -> CLAIMING` claims are
  in-flight, so do not treat the worker as a pool.
- Suggested supervisors for the `--interval` mode:
  - systemd unit (`Restart=always`, `ExecStart=… document_worker --interval 30`);
  - cron `@reboot` + a keep-alive wrapper;
  - a container with `restart: unless-stopped` running the backend image.
- Monitor processing failures (`documents.processing_status = FAILED`) and
  alert on a backlog of stuck `UPLOADED` rows.

For MVP, this simple worker architecture is sufficient.

Do not introduce unnecessary distributed infrastructure.

## 11.1 Serverless processing (no long-lived worker)

A serverless host cannot run `--interval` polling, so on Vercel the same pipeline
is driven by requests instead. Two mechanisms, deliberately redundant:

1. **Per-document kick.** The frontend calls
   `POST /api/v1/documents/{id}/process` after a successful upload, and again if
   a document is still `UPLOADED` on the processing screen. The endpoint is
   owner-scoped and refuses any document that is not `UPLOADED`, so retries are
   harmless.
2. **Scheduled drain.** `backend/vercel.json` schedules a cron that calls
   `POST /api/v1/internal/process-documents`, which processes a small batch of
   `UPLOADED` rows (default 3, max 25). This is the safety net for kicks lost to
   a dropped connection, a closed tab or a cold container.

The internal endpoint refuses to start unless `CRON_SECRET` is configured, and
then only accepts the secret Vercel sends with the cron invocation. Combined
with the startup validation in §4.1, a production deployment cannot expose an
unauthenticated way to trigger processing.

Operational notes:

* Cron schedules on Vercel are plan-dependent (Hobby permits one invocation per
  day). If the schedule is rejected, the per-document kick still drives
  processing; only the backlog safety net is lost.
* Each invocation must finish inside `maxDuration`, so keep the batch small.
* The pipeline is still single-consumer while `UPLOADED -> CLAIMING` claims are
  in flight, so overlapping cron and kick invocations must not process the same
  row twice — the claim step is what guarantees this.

OCR caveat: Tesseract is a system binary and is not present on the serverless
runtime. Image-based documents therefore end in `FAILED` with an honest error
rather than fabricated text. PDF and DOCX extraction is unaffected. Deploy the
backend to a container host (Docker, §9) if OCR must work in production.

---

# 12. Health Checks

Backend:

```text
GET /api/v1/health
```

Check:

* Application availability
* Database connectivity where appropriate

Do not expose credentials or infrastructure details.

---

# 13. HTTPS

Production traffic must use HTTPS.

Redirect HTTP to HTTPS where supported.

---

# 14. CORS

Only trusted frontend origins should be allowed.

Example:

```text
https://nyayalens.example
```

Do not use unrestricted:

```text
*
```

for production authenticated APIs.

---

# 15. Secure Headers

Configure appropriate headers including:

```text
Content-Security-Policy
X-Content-Type-Options
Referrer-Policy
Permissions-Policy
Strict-Transport-Security
```

Exact CSP rules should be tested against the deployed application.

---

# 16. Rate Limiting

Apply limits to:

```text
Authentication
Uploads
Q&A
Comparison
Report Generation
```

AI-intensive endpoints should have tighter limits.

---

# 17. Logging

Production logs should capture:

```text
timestamp
request ID
endpoint
status
latency
safe error code
```

Avoid logging:

```text
passwords
tokens
full documents
document text
AI prompts containing private content
API keys
```

---

# 18. Monitoring

Monitor:

* API errors
* Processing failures
* AI failures
* Database health
* Storage errors
* Latency
* Worker failures
* Rate-limit events

---

# 19. Backup Strategy

Database backups should be automated.

At minimum:

```text
Daily backups
+
Point-in-time recovery where supported
```

Test restoration periodically.

---

# 20. File Storage Lifecycle

Document lifecycle:

```text
Upload
 ↓
Private Storage
 ↓
Processing
 ↓
Analysis
 ↓
User Workspace
 ↓
Deletion Request
 ↓
Cleanup
```

Derived data should be handled consistently with the data-retention policy.

---

# 21. CI/CD

Recommended pipeline:

```text
Git Push
 ↓
GitHub Actions
 ↓
Lint
 ↓
Type Check
 ↓
Unit Tests
 ↓
Security Checks
 ↓
Build
 ↓
Deploy
 ↓
Health Check
```

---

# 22. Frontend Checks

Run:

```text
Lint
TypeScript Check
Unit Tests
Component Tests
Build
```

---

# 23. Backend Checks

Run:

```text
Lint
Formatting
Type Check
Unit Tests
API Tests
Database Tests
Security Tests
```

---

# 24. AI Checks

Before deployment:

```text
Retrieval Evaluation
Citation Evaluation
Prompt Injection Tests
Hallucination Tests
Structured Output Tests
Comparison Tests
```

---

# 25. Production Checklist

```text
[ ] HTTPS
[ ] Secure secrets
[ ] Private storage
[ ] Database backups
[ ] Authentication
[ ] Authorization
[ ] CORS
[ ] Rate limiting
[ ] Secure headers
[ ] File validation
[ ] Malware scanning (NOT yet implemented — content validation is size/MIME/structure only)
[ ] Safe logging
[ ] Health checks
[ ] Monitoring
[ ] Database migrations
[ ] AI evaluation
[ ] E2E testing
```

---

# 26. Deployment Rollback

If a deployment fails:

```text
Detect failure
 ↓
Stop rollout
 ↓
Rollback application
 ↓
Verify health
 ↓
Investigate
```

Database migrations must be designed carefully because not all schema changes are safely reversible.

---

# 27. MVP Deployment Strategy

Keep the deployment architecture simple:

```text
Next.js
     +
FastAPI
     +
Supabase Database (managed PostgreSQL + pgvector)
     +
Supabase Storage (private buckets)
     +
LLM/OCR APIs
```

Do not use Kubernetes, service meshes, or a large microservice architecture for the MVP.

---

# 28. Production Principle

> **Deploy the smallest architecture that can securely and reliably demonstrate the complete NyayaLens workflow.**
