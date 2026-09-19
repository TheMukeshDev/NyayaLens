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

Deploy on a platform supporting Next.js.

The frontend should use environment variables for:

```text
NEXT_PUBLIC_API_URL
```

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

Example:

```text
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres
LLM_API_KEY=
EMBEDDING_API_KEY=
OCR_API_KEY=
CORS_ORIGINS=
```

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

Use:

```text
Alembic
```

Deployment flow:

```text
Build
 ↓
Run migrations
 ↓
Start application
 ↓
Health check
```

Migrations must be reviewed before production execution.

---

# 11. Background Workers

Document processing should not block normal API requests.

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

For MVP, a simple worker architecture is sufficient.

Do not introduce unnecessary distributed infrastructure.

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
[ ] Malware scanning
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
