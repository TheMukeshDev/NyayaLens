# NyayaLens — API Specification

**Version:** 1.0
**Backend:** FastAPI
**Database:** Supabase Database (PostgreSQL) + pgvector
**Authentication:** Supabase Auth (managed, JWT bearer sessions)
**API Base Path:** `/api/v1`

---

# 1. API Principles

The NyayaLens API follows:

* RESTful resource design
* JSON request/response bodies
* Authentication on protected endpoints
* Server-side authorization
* Pydantic validation
* Consistent error responses
* User-scoped document access
* Secure file handling
* Versioned API routes

---

# 2. Base URL

Development:

```text
http://localhost:8000/api/v1
```

Production:

```text
https://api.<production-domain>/api/v1
```

The production domain must be configured through environment variables.

---

# 3. Response Format

Successful response:

```json
{
  "success": true,
  "data": {},
  "message": null
}
```

Error response:

```json
{
  "success": false,
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "The requested document could not be found."
  }
}
```

Do not expose:

* Stack traces
* Database errors
* Internal file paths
* AI system prompts
* API keys
* Internal service details

---

# 4. Authentication

Authentication is managed by **Supabase Auth** (email/password registration, login, session/JWT management, and logout).

The custom local endpoints below describe the application-facing contract and are implemented by delegating to Supabase Auth.

## POST `/auth/register`

Create a new user.

### Request

```json
{
  "name": "Mukesh Kumar",
  "email": "user@example.com",
  "password": "strong-password"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_123",
      "name": "Mukesh Kumar",
      "email": "user@example.com"
    }
  }
}
```

---

## POST `/auth/login`

Authenticate a user.

### Request

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "access_token": "...",
    "token_type": "bearer",
    "user": {}
  }
}
```

Tokens must never be logged.

---

## POST `/auth/logout`

Invalidate the current session where applicable.

---

## GET `/auth/me`

Return authenticated user information.

### Authentication

Required.

---

# 5. User Endpoints

## GET `/users/me`

Returns the current user's profile.

---

## PATCH `/users/me`

Updates allowed profile fields.

Example:

```json
{
  "name": "Updated Name"
}
```

Sensitive account fields require additional validation.

---

# 6. Document Endpoints

## POST `/documents`

Create a document upload.

### Content Type

```text
multipart/form-data
```

### Request

```text
file=<document>
```

### Response

```json
{
  "success": true,
  "data": {
    "document": {
      "id": "doc_123",
      "filename": "employment-agreement.pdf",
      "status": "UPLOADED"
    }
  }
}
```

---

# 7. Document Security Requirements

Every document request must:

1. Authenticate the user.
2. Verify ownership.
3. Verify document status.
4. Perform the requested operation.
5. Return only authorized data.

Never trust:

```text
user_id
```

provided by the frontend.

The authenticated identity must come from the backend authentication layer.

---

# 8. GET `/documents`

Returns the authenticated user's documents.

### Query Parameters

```text
page
limit
search
type
status
sort
```

Example:

```text
GET /documents?page=1&limit=20&status=READY
```

---

# 9. GET `/documents/{document_id}`

Returns document metadata.

Example:

```json
{
  "success": true,
  "data": {
    "id": "doc_123",
    "filename": "employment-agreement.pdf",
    "document_type": "employment_agreement",
    "status": "READY",
    "page_count": 8,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

---

# 10. DELETE `/documents/{document_id}`

Deletes a user's document.

The operation must trigger appropriate cleanup of:

* Supabase Storage (private bucket)
* Extracted text
* Chunks
* Embeddings
* Analysis
* Conversations
* Citations
* Derived data

Deletion should be handled safely and consistently with the retention policy.

---

# 11. GET `/documents/{document_id}/status`

Returns processing status.

```json
{
  "status": "ANALYZING",
  "progress": 75,
  "message": "Analyzing document clauses"
}
```

Allowed states:

```text
UPLOADED
VALIDATING
PROCESSING
EXTRACTING
ANALYZING
READY
FAILED
```

---

# 12. Document Content

## GET `/documents/{document_id}/sections`

Returns detected sections.

---

## GET `/documents/{document_id}/clauses`

Returns detected clauses.

### Query Parameters

```text
type
search
page
limit
```

---

## GET `/documents/{document_id}/clauses/{clause_id}`

Returns:

* Clause metadata
* Original text
* Simplified explanation
* Source page
* Section
* Related attention items

---

# 13. Summary API

## GET `/documents/{document_id}/summary`

Returns generated summary.

Example:

```json
{
  "document_type": "Employment Agreement",
  "purpose": "...",
  "parties": [],
  "key_terms": [],
  "obligations": [],
  "important_conditions": []
}
```

---

# 14. Attention API

## GET `/documents/{document_id}/attention`

Returns attention items.

Example:

```json
{
  "items": [
    {
      "id": "att_123",
      "title": "Termination Notice",
      "level": "HIGH",
      "category": "termination",
      "explanation": "...",
      "source": {
        "section": "8. Termination",
        "page": 6
      }
    }
  ]
}
```

---

# 15. Q&A API

## POST `/documents/{document_id}/ask`

Ask a question about the document.

### Request

```json
{
  "question": "What happens if I leave the company?"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "answer": "The agreement specifies a 90-day notice period.",
    "evidence_state": "DOCUMENT-GROUNDED",
    "citations": [
      {
        "id": "cit_123",
        "section": "8. Termination",
        "page": 6,
        "chunk_id": "chunk_18"
      }
    ]
  }
}
```

---

# 16. Q&A Evidence States

Allowed values:

```text
DOCUMENT-GROUNDED
GENERAL-INFORMATION
INSUFFICIENT-EVIDENCE
```

The API must not return an answer as document-grounded unless supporting evidence was retrieved and validated.

---

# 17. Conversation API

## GET `/documents/{document_id}/conversations`

Returns conversation history.

---

## POST `/documents/{document_id}/conversations`

Creates a conversation.

---

## GET `/conversations/{conversation_id}/messages`

Returns messages.

---

# 18. Citation API

## GET `/citations/{citation_id}`

Returns validated citation information.

Example:

```json
{
  "section": "8. Termination",
  "page": 6,
  "source_text": "...",
  "document_id": "doc_123"
}
```

The API must verify that the authenticated user owns the associated document.

---

# 19. Comparison API

## POST `/comparisons`

Create a comparison.

### Request

```json
{
  "document_a_id": "doc_123",
  "document_b_id": "doc_456"
}
```

The backend must verify ownership/access to **both** documents.

---

## GET `/comparisons/{comparison_id}`

Returns comparison metadata and status.

---

## GET `/comparisons/{comparison_id}/changes`

Returns detected changes.

Example:

```json
{
  "changes": [
    {
      "type": "MODIFIED",
      "category": "termination",
      "title": "Notice Period",
      "before": "30 days",
      "after": "90 days",
      "importance": "HIGH"
    }
  ]
}
```

---

# 20. Action API

## GET `/actions`

Returns user's actions.

Filters:

```text
status
priority
document_id
```

---

## POST `/actions`

Create an action.

```json
{
  "document_id": "doc_123",
  "title": "Review termination clause",
  "priority": "HIGH"
}
```

---

## PATCH `/actions/{action_id}`

Update:

```text
title
status
priority
```

Allowed statuses:

```text
TODO
IN_PROGRESS
COMPLETED
DISMISSED
```

---

## DELETE `/actions/{action_id}`

Delete an action.

---

# 21. Professional Questions API

## POST `/documents/{document_id}/questions/generate`

Generates questions for discussion with a qualified professional.

Example response:

```json
{
  "questions": [
    {
      "question": "Should I clarify how the notice period applies during probation?",
      "source": {
        "section": "8",
        "page": 6
      }
    }
  ]
}
```

---

# 22. Report API

## POST `/documents/{document_id}/reports`

Creates a report-generation job.

---

## GET `/reports`

Lists reports owned by the user.

---

## GET `/reports/{report_id}`

Returns report metadata.

---

## GET `/reports/{report_id}/download`

Returns a secure, short-lived download mechanism.

Never expose public permanent document URLs.

---

# 23. Health API

## GET `/health`

Returns application health.

```json
{
  "status": "ok"
}
```

This endpoint must not expose infrastructure secrets.

---

# 24. Error Codes

Standard errors include:

```text
AUTH_REQUIRED
INVALID_CREDENTIALS
FORBIDDEN
USER_NOT_FOUND
DOCUMENT_NOT_FOUND
DOCUMENT_ACCESS_DENIED
INVALID_FILE
FILE_TOO_LARGE
UNSUPPORTED_FILE_TYPE
MALWARE_DETECTED
PROCESSING_FAILED
ANALYSIS_FAILED
INSUFFICIENT_EVIDENCE
INVALID_CITATION
COMPARISON_FAILED
RATE_LIMITED
VALIDATION_ERROR
INTERNAL_ERROR
```

---

# 25. HTTP Status Codes

```text
200 OK
201 Created
202 Accepted
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
413 Payload Too Large
422 Unprocessable Entity
429 Too Many Requests
500 Internal Server Error
503 Service Unavailable
```

---

# 26. Rate Limiting

Rate limits should be applied to expensive endpoints.

Especially:

```text
POST /documents
POST /documents/{id}/ask
POST /comparisons
POST /reports
```

AI-intensive operations should have stricter limits than normal reads.

---

# 27. Pagination

List endpoints should use pagination.

Example:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

---

# 28. API Validation

Pydantic models must validate:

* Request fields
* IDs
* Enums
* String lengths
* File metadata
* Pagination values
* User input

Do not rely only on frontend validation.

---

# 29. API Logging

Safe logs may contain:

```text
request_id
endpoint
method
status_code
latency
user_id_hash
document_id
error_code
```

Do not log:

* Passwords
* Tokens
* Full legal documents
* Full extracted text
* Sensitive prompts
* API keys
* Personal document contents

---

# 30. API Versioning

All public API routes use:

```text
/api/v1
```

Breaking changes require a new API version.

---

# 31. API Security Checklist

Before production:

```text
[ ] Authentication
[ ] Authorization
[ ] Input validation
[ ] Rate limiting
[ ] CORS restrictions
[ ] Secure headers
[ ] HTTPS
[ ] File validation
[ ] Malware scanning
[ ] Safe error handling
[ ] Secure logging
[ ] Secret management
[ ] User/document isolation
[ ] Citation ownership validation
```
