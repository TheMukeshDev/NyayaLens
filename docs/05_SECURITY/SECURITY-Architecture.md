# NyayaLens — Security Architecture

Canonical security architecture. Source of truth: `../03_TECH/System-Architecture.md` sections 48-53, 58-59, 78.

---

# 1. Security Architecture Overview

```text
                         INTERNET
                             │
                           HTTPS
                             │
                             ▼
                    ┌─────────────────┐
                    │   Next.js Web   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    FastAPI      │
                    │ Auth + ACL      │
                    └────────┬────────┘
                             │
┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
     Supabase Database   Supabase Storage    AI
              │                               │
              ▼                               ▼
     pgvector (Supabase)               Validation
```

---

# 2. Security Requirements

Mandatory:

```text
HTTPS
Authentication
Server-side authorization
Private storage
File validation
Malware scanning
Rate limiting
CORS restrictions
Secure headers
Secret management
Safe logging
Input validation
Output validation
```

---

# 3. File Security

Uploaded files are untrusted.

```text
Upload
 ↓
Size Validation
 ↓
MIME Validation
 ↓
File Structure Validation
 ↓
Malware Scan
 ↓
Private Storage
 ↓
Processing
```

Never execute uploaded content.

---

# 4. Storage Security

Never create permanently public document URLs.

Use:

```text
Private object (Supabase Storage private bucket)
        ↓
Authorization
        ↓
Short-lived signed URL
```

when direct browser access is necessary.

---

# 5. Data Isolation

Every query must be scoped to the authenticated user.

Example:

```text
document.owner_id == current_user.id
```

and:

```text
chunk.document.owner_id == current_user.id
```

This is mandatory for:

```text
Document access
RAG
Comparison
Reports
Actions
```

---

# 6. Rate Limiting

Apply limits to:

```text
Login
Upload
AI questions
Document analysis
Comparison
Report generation
```

The exact limits can be tuned after load testing.

---

# 7. AI Boundaries

Do not send unrelated documents or unnecessary user information to an AI provider.

```text
NyayaLens Backend
       │
       │ Relevant document evidence
       ▼
     LLM API
       │
       ▼
   AI Response
       │
       ▼
 Citation Validation
       │
       ▼
     Browser
```

The selected provider's current data-retention and training policies must be reviewed before production deployment.

---

# 8. Prompt Injection Protection

Apply input validation and prompt isolation:

```text
Input Validation
       ↓
Prompt Safety
       ↓
Retrieval
       ↓
LLM
       ↓
Structured Output Validation
       ↓
Citation Validation
       ↓
Safety Check
       ↓
User
```

---

# 9. Logging

Log:

```text
Request ID
Endpoint
Status
Duration
Job ID
Error category
```

Do NOT log:

```text
Full legal document
Passwords
Tokens
API keys
Sensitive document text
Private prompts
```

---

# 10. Audit Events

Track important events:

```text
LOGIN
LOGOUT
DOCUMENT_UPLOAD
DOCUMENT_VIEW
DOCUMENT_DELETE
ANALYSIS_REQUEST
AI_QUESTION
COMPARISON_CREATED
REPORT_CREATED
```

Use audit metadata rather than storing unnecessary document content.

---

# 11. Environment Configuration

Development:

```text
.env.local
```

Backend:

```text
.env
```

Production:

```text
Cloud secret/environment manager
```

Never commit secrets. Repository should contain only `.env.example`.

---

# 12. CORS

Development may allow `localhost`.

Production should allow only the deployed frontend domain.

Do not use unrestricted production CORS.

---

# 13. Threat Model

Threats:

```text
T1 — Unauthorized document access
T2 — Malicious file upload
T3 — Prompt injection
T4 — Cross-user retrieval
T5 — Cross-document retrieval
T6 — Credential leakage
T7 — API abuse
T8 — Hallucinated citations
T9 — Sensitive logging
T10 — Broken access control
```

Mitigation:

```text
Authentication
Authorization
Private storage
File validation
Malware scanning
RAG filtering
Prompt isolation
Rate limiting
Secret management
Citation validation
Safe logging
```

---

# 14. Legal Safety

AI output should be classified as:

```text
Document Evidence
+
AI Interpretation
```

The system should never silently transform interpretation into legal fact.

Use:

```text
Based on the document...
```

instead of:

```text
The law definitely says...
```

unless the source has actually been verified.

---

# 15. AI Cost Management

Avoid unnecessary model calls.

Use:

```text
Cached analysis
Cached embeddings
RAG
Token limits
Request limits
Deduplication
```

---

# 16. Failure Handling

## AI failure

```text
AI unavailable
 ↓
Document remains safe
 ↓
Analysis = FAILED
 ↓
Retry
```

## Processing failure

```text
Processing failed
 ↓
Document retained
 ↓
Error shown
 ↓
Retry available
```

## Report failure

```text
Report generation failed
 ↓
Analysis remains available
```

---

# 17. Deployment Security Checklist

Verify before production:

```text
HTTPS
Production environment variables
CORS
Authentication
File uploads
AI pipeline
Secret management
Safe logging
Rate limiting
Prompt injection protection
```

---

# 18. Definition of Security Done

```text
☐ HTTPS enabled
☐ Authentication working
☐ Server-side authorization tested
☐ Private storage configured
☐ File validation enforced
☐ Malware scanning configured
☐ Rate limiting implemented
☐ CORS restricted
☐ Secure headers set
☐ Secrets removed from repository
☐ Safe logging implemented
☐ Prompt injection protection implemented
☐ Citation validation implemented
☐ Audit events tracked
```