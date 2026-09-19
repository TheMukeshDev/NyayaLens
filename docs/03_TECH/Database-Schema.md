# NyayaLens — Database Schema

**Version:** 1.0
**Product:** NyayaLens
**Tagline:** Understand. Review. Act.
**Database:** Supabase Database (PostgreSQL)
**Vector Search:** pgvector (Supabase Database)
**Backend:** FastAPI + SQLAlchemy
**Status:** MVP / Production-Oriented Design

---

## 1. Purpose

This document defines the Supabase Database (PostgreSQL) architecture for NyayaLens.

NyayaLens uses the database to manage:

* User accounts
* Authentication metadata
* Legal documents
* Document processing states
* Extracted sections
* Detected clauses
* Text chunks
* Vector embeddings
* AI analyses
* Attention items
* AI conversations
* AI answers
* Source citations
* Document comparisons
* Detected changes
* Action items
* Generated reports
* Audit/security events

The schema is designed around one critical principle:

> **Every user-owned legal document and every AI operation must remain isolated by authenticated user ownership.**

---

# 2. Database Technology

## 2.1 Primary Database

Supabase Database (managed PostgreSQL).

Recommended version:

```text
PostgreSQL 16+
```

Supabase manages hosting, backups, and High Availability.

## 2.2 Required Extensions

### UUID

Use UUID identifiers for externally exposed records.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

UUID generation:

```sql
gen_random_uuid()
```

### pgvector (Supabase Database)

Used for semantic document retrieval.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Recommended embedding dimension depends on the selected embedding model.

For example:

```text
VECTOR(1536)
```

The exact dimension must match the deployed embedding model.

---

# 3. High-Level Entity Relationship

```text
                    ┌──────────────┐
                    │    users     │
                    └──────┬───────┘
                           │
             ┌─────────────┼──────────────┐
             │             │              │
             ▼             ▼              ▼
       ┌──────────┐  ┌──────────┐  ┌──────────────┐
       │documents │  │ actions  │  │ conversations│
       └────┬─────┘  └──────────┘  └──────┬───────┘
            │                             │
     ┌──────┼──────────┐                  ▼
     │      │          │              ┌──────────┐
     ▼      ▼          ▼              │ messages │
 sections clauses    chunks           └────┬─────┘
                         │                  │
                         ▼                  ▼
embeddings          citations
                          │
                          ▼
                       pgvector (Supabase)

documents
    │
    ├── analyses
    │      │
    │      └── attention_items
    │
    ├── comparisons
    │      │
    │      └── comparison_changes
    │
    └── reports
```

---

# 4. Design Principles

## 4.1 User Isolation

Every user-owned resource must be traceable to an authenticated user.

Example:

```text
users
  ↓
documents.user_id
```

AI retrieval must never search across all documents.

Instead:

```text
WHERE user_id = authenticated_user_id
AND document_id = requested_document_id
```

---

## 4.2 UUID Primary Keys

Use UUIDs rather than sequential integer IDs for externally visible entities.

Advantages:

* Harder to enumerate
* Better for distributed systems
* Safer for public APIs
* Easier future scaling

---

## 4.3 Timestamps

All major entities should contain:

```text
created_at
updated_at
```

Store timestamps in UTC.

---

## 4.4 Soft Deletion

User documents should preferably use:

```text
deleted_at
```

instead of immediately removing database records.

Actual file deletion from Supabase Storage should be handled separately.

---

# 5. Core Tables

---

# 5.1 users

Stores application user information.

> **Supabase Auth** manages authentication identity (email/password, sessions, JWT). The application `users` table mirrors profile metadata and links application records to the Supabase Auth user ID.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    email VARCHAR(320) NOT NULL UNIQUE,

    full_name VARCHAR(150),

    password_hash TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    is_verified BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    last_login_at TIMESTAMPTZ,

    deleted_at TIMESTAMPTZ
);
```

### Fields

| Field         | Type      | Description               |
| ------------- | --------- | ------------------------- |
| id            | UUID      | Unique user ID            |
| email         | VARCHAR   | Login email               |
| full_name     | VARCHAR   | Display name              |
| password_hash | TEXT      | Hashed password           |
| is_active     | BOOLEAN   | Account status            |
| is_verified   | BOOLEAN   | Email verification status |
| last_login_at | TIMESTAMP | Last successful login     |
| created_at    | TIMESTAMP | Account creation          |
| updated_at    | TIMESTAMP | Last update               |
| deleted_at    | TIMESTAMP | Soft deletion             |

### Security

> Authentication password hashing (per Supabase Auth) is the responsibility of Supabase Auth, not the application.

The application must never store plaintext passwords.

If application-level hashing were ever introduced, it should use:

```text
Argon2id
```

or another approved password hashing algorithm.

---

# 5.2 user_preferences

Stores user settings.

```sql
CREATE TABLE user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,

    language VARCHAR(20) NOT NULL DEFAULT 'en',

    theme VARCHAR(20) NOT NULL DEFAULT 'system',

    email_notifications BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

# 6. Document Management

# 6.1 documents

Central table for uploaded legal documents.

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    original_filename TEXT NOT NULL,

    display_name VARCHAR(255),

    mime_type VARCHAR(100) NOT NULL,

    file_size_bytes BIGINT NOT NULL,

    storage_key TEXT NOT NULL,

    document_type VARCHAR(100),

    language VARCHAR(20),

    processing_status VARCHAR(30) NOT NULL DEFAULT 'UPLOADED',

    processing_error TEXT,

    page_count INTEGER,

    checksum_sha256 CHAR(64),

    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    processed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    deleted_at TIMESTAMPTZ
);
```

### Processing Status

Allowed values:

```text
UPLOADED
VALIDATING
PROCESSING
EXTRACTING
ANALYZING
READY
FAILED
```

### Important Security Rule

`storage_key` must never be directly exposed to the browser.

The backend should generate short-lived signed URLs when file access is required.

---

# 6.2 document_versions

Useful when users upload multiple versions of the same document.

```sql
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    version_number INTEGER NOT NULL,

    storage_key TEXT NOT NULL,

    checksum_sha256 CHAR(64),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(document_id, version_number)
);
```

This allows:

```text
Employment Agreement
 ├── Version 1
 ├── Version 2
 └── Version 3
```

---

# 7. Document Structure

# 7.1 sections

Stores logical sections extracted from documents.

```sql
CREATE TABLE sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    section_number VARCHAR(50),

    title TEXT,

    content TEXT NOT NULL,

    page_start INTEGER,

    page_end INTEGER,

    parent_section_id UUID REFERENCES sections(id) ON DELETE SET NULL,

    sequence_number INTEGER NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Example:

```text
Section 1 — Employment
Section 2 — Compensation
Section 3 — Confidentiality
Section 4 — Termination
```

---

# 7.2 clauses

Stores individual legal clauses.

```sql
CREATE TABLE clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    section_id UUID REFERENCES sections(id) ON DELETE SET NULL,

    clause_number VARCHAR(50),

    clause_type VARCHAR(100),

    title TEXT,

    content TEXT NOT NULL,

    page_start INTEGER,

    page_end INTEGER,

    sequence_number INTEGER NOT NULL,

    extraction_confidence NUMERIC(5,4),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Possible clause types

```text
TERMINATION
COMPENSATION
CONFIDENTIALITY
NON_DISCLOSURE
NON_COMPETE
INTELLECTUAL_PROPERTY
LIABILITY
INDEMNIFICATION
DISPUTE_RESOLUTION
GOVERNING_LAW
NOTICE
LEAVE
PROBATION
PAYMENT
DATA_PROTECTION
OTHER
```

---

# 8. RAG / Vector Search

# 8.1 document_chunks

Documents are divided into retrieval-friendly chunks.

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    section_id UUID REFERENCES sections(id) ON DELETE SET NULL,

    clause_id UUID REFERENCES clauses(id) ON DELETE SET NULL,

    chunk_index INTEGER NOT NULL,

    content TEXT NOT NULL,

    page_start INTEGER,

    page_end INTEGER,

    token_count INTEGER,

    metadata JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Example metadata:

```json
{
  "heading": "Termination",
  "page": 6,
  "section": "8",
  "language": "en"
}
```

---

# 8.2 embeddings

Stores vector representations of chunks.

```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    chunk_id UUID NOT NULL UNIQUE
        REFERENCES document_chunks(id) ON DELETE CASCADE,

    embedding VECTOR(1536) NOT NULL,

    model_name VARCHAR(150) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Vector Index

For large datasets:

```sql
CREATE INDEX embeddings_vector_idx
ON embeddings
USING hnsw (embedding vector_cosine_ops);
```

The exact index configuration should be tuned after measuring production retrieval performance.

---

# 9. AI Analysis

# 9.1 analyses

Stores generated document-level AI analysis.

```sql
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    analysis_type VARCHAR(50) NOT NULL,

    model_name VARCHAR(150),

    prompt_version VARCHAR(50),

    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',

    result JSONB,

    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ
);
```

### Analysis types

```text
SUMMARY
CLAUSE_EXTRACTION
ATTENTION_ANALYSIS
ENTITY_EXTRACTION
ACTION_GENERATION
```

---

# 9.2 attention_items

Stores areas requiring user attention.

```sql
CREATE TABLE attention_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,

    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    clause_id UUID REFERENCES clauses(id) ON DELETE SET NULL,

    title VARCHAR(255) NOT NULL,

    description TEXT NOT NULL,

    attention_level VARCHAR(20) NOT NULL,

    category VARCHAR(100),

    recommendation TEXT,

    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Attention Levels

```text
LOW
MEDIUM
HIGH
```

### Important Product Rule

Do not present this as:

```text
LEGAL RISK: 87%
```

or:

```text
THIS CONTRACT IS UNSAFE
```

Instead:

```text
HIGH ATTENTION
Termination clause requires review.
```

---

# 10. AI Conversations

# 10.1 conversations

Stores document-related conversations.

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,

    title VARCHAR(255),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

A conversation can optionally be associated with a specific document.

---

# 10.2 messages

Stores conversation messages.

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    conversation_id UUID NOT NULL
        REFERENCES conversations(id) ON DELETE CASCADE,

    role VARCHAR(20) NOT NULL,

    content TEXT NOT NULL,

    response_type VARCHAR(40),

    model_name VARCHAR(150),

    token_usage JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Roles

```text
USER
ASSISTANT
SYSTEM
```

### Response Types

```text
DOCUMENT_GROUNDED
GENERAL_INFORMATION
INSUFFICIENT_EVIDENCE
```

---

# 11. Citation System

# 11.1 citations

Every document-grounded AI answer should have traceable sources.

```sql
CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,

    chunk_id UUID REFERENCES document_chunks(id) ON DELETE SET NULL,

    section_id UUID REFERENCES sections(id) ON DELETE SET NULL,

    clause_id UUID REFERENCES clauses(id) ON DELETE SET NULL,

    page_start INTEGER,

    page_end INTEGER,

    citation_text TEXT,

    citation_order INTEGER NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Example UI:

```text
AI Answer

The agreement requires a 90-day notice period.

Sources:
[1] Section 8 — Termination
    Page 6
```

---

# 12. Document Comparison

# 12.1 comparisons

Stores comparison jobs.

```sql
CREATE TABLE comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    document_a_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    document_b_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',

    summary TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ,

    CHECK (document_a_id <> document_b_id)
);
```

---

# 12.2 comparison_changes

Stores detected differences.

```sql
CREATE TABLE comparison_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    comparison_id UUID NOT NULL
        REFERENCES comparisons(id) ON DELETE CASCADE,

    change_type VARCHAR(20) NOT NULL,

    category VARCHAR(100),

    old_text TEXT,

    new_text TEXT,

    explanation TEXT,

    importance VARCHAR(20),

    old_clause_id UUID REFERENCES clauses(id) ON DELETE SET NULL,

    new_clause_id UUID REFERENCES clauses(id) ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Change Types

```text
ADDED
REMOVED
MODIFIED
UNCHANGED
```

Example:

```text
TERMINATION NOTICE

Version 1:
30 days

Version 2:
90 days

Change:
MODIFIED

Importance:
HIGH
```

---

# 13. Action Center

# 13.1 actions

Stores recommended user actions.

```sql
CREATE TABLE actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,

    attention_item_id UUID REFERENCES attention_items(id) ON DELETE SET NULL,

    action_type VARCHAR(50) NOT NULL,

    title VARCHAR(255) NOT NULL,

    description TEXT,

    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',

    status VARCHAR(30) NOT NULL DEFAULT 'TODO',

    source JSONB,

    due_date DATE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Action Types

```text
REVIEW_CLAUSE
ASK_PROFESSIONAL
COLLECT_DOCUMENT
VERIFY_INFORMATION
NEGOTIATE_TERM
FOLLOW_UP
```

### Status

```text
TODO
IN_PROGRESS
COMPLETED
DISMISSED
```

---

# 14. Generated Reports

# 14.1 reports

Stores generated report metadata.

```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    report_type VARCHAR(50) NOT NULL,

    storage_key TEXT,

    status VARCHAR(30) NOT NULL DEFAULT 'GENERATING',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ
);
```

Possible report types:

```text
DOCUMENT_REVIEW
SUMMARY
COMPARISON
ACTION_PLAN
```

Generated PDFs should be stored in Supabase Storage (private bucket).

---

# 15. Security & Audit

# 15.1 audit_logs

Tracks security-sensitive operations.

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    action VARCHAR(100) NOT NULL,

    resource_type VARCHAR(50),

    resource_id UUID,

    ip_hash TEXT,

    user_agent TEXT,

    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Examples:

```text
LOGIN_SUCCESS
LOGIN_FAILED
DOCUMENT_UPLOADED
DOCUMENT_DELETED
DOCUMENT_VIEWED
REPORT_GENERATED
COMPARISON_CREATED
ACCOUNT_UPDATED
```

### Privacy

Do not store complete legal documents or sensitive document text in audit logs.

---

# 16. Indexing Strategy

Indexes are essential because NyayaLens will frequently filter by user and document.

## Users

```sql
CREATE UNIQUE INDEX idx_users_email
ON users(email);
```

---

## Documents

```sql
CREATE INDEX idx_documents_user_id
ON documents(user_id);

CREATE INDEX idx_documents_user_status
ON documents(user_id, processing_status);

CREATE INDEX idx_documents_created_at
ON documents(created_at DESC);
```

---

## Sections

```sql
CREATE INDEX idx_sections_document_id
ON sections(document_id);
```

---

## Clauses

```sql
CREATE INDEX idx_clauses_document_id
ON clauses(document_id);

CREATE INDEX idx_clauses_section_id
ON clauses(section_id);

CREATE INDEX idx_clauses_type
ON clauses(document_id, clause_type);
```

---

## Chunks

```sql
CREATE INDEX idx_chunks_document_id
ON document_chunks(document_id);

CREATE INDEX idx_chunks_clause_id
ON document_chunks(clause_id);
```

---

## Conversations

```sql
CREATE INDEX idx_conversations_user_id
ON conversations(user_id);

CREATE INDEX idx_conversations_document_id
ON conversations(document_id);
```

---

## Messages

```sql
CREATE INDEX idx_messages_conversation_id
ON messages(conversation_id);

CREATE INDEX idx_messages_created_at
ON messages(created_at);
```

---

## Actions

```sql
CREATE INDEX idx_actions_user_id
ON actions(user_id);

CREATE INDEX idx_actions_document_id
ON actions(document_id);

CREATE INDEX idx_actions_status
ON actions(user_id, status);
```

---

# 17. Vector Retrieval Query

A typical RAG retrieval operation should look conceptually like:

```sql
SELECT
    dc.id,
    dc.document_id,
    dc.content,
    dc.page_start,
    dc.page_end,
    e.embedding <=> :query_embedding AS distance
FROM document_chunks dc
JOIN embeddings e
    ON e.chunk_id = dc.id
JOIN documents d
    ON d.id = dc.document_id
WHERE
    dc.document_id = :document_id
    AND d.user_id = :authenticated_user_id
    AND d.deleted_at IS NULL
ORDER BY e.embedding <=> :query_embedding
LIMIT 8;
```

The critical security condition is:

```sql
d.user_id = :authenticated_user_id
```

Never trust a `user_id` supplied by the frontend.

---

# 18. Multi-Tenant Security

NyayaLens is logically multi-tenant.

The ownership hierarchy is:

```text
User
 │
 ├── Documents
 │    ├── Sections
 │    ├── Clauses
 │    ├── Chunks
 │    ├── Analyses
 │    └── Attention Items
 │
 ├── Conversations
 │    └── Messages
 │         └── Citations
 │
 ├── Comparisons
 │    └── Changes
 │
 ├── Actions
 │
 └── Reports
```

The backend must enforce this hierarchy.

---

# 19. Authorization Rules

## Rule 1 — Document Access

A user can access a document only if:

```text
document.user_id == authenticated_user.id
```

---

## Rule 2 — Child Resource Access

Never assume that knowing a child resource ID grants access.

For example:

```text
GET /api/clauses/{clause_id}
```

must verify:

```text
clause
 → document
 → user
```

before returning data.

---

## Rule 3 — Conversation Access

Verify:

```text
conversation.user_id == authenticated_user.id
```

and, when document-scoped:

```text
conversation.document_id
```

belongs to the same user.

---

## Rule 4 — Comparison Access

Both documents must belong to the authenticated user.

```text
document_a.user_id == current_user
document_b.user_id == current_user
```

---

# 20. Row-Level Security

For stronger isolation, Supabase Database (PostgreSQL) Row-Level Security can be introduced.

Example:

```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
```

Conceptually:

```sql
CREATE POLICY documents_owner_policy
ON documents
USING (
    user_id = current_setting('app.current_user_id')::uuid
);
```

The FastAPI database layer would set the authenticated user ID for each transaction.

RLS should complement—not replace—application-level authorization.

---

# 21. Data Lifecycle

## Document Upload

```text
User uploads file
       ↓
documents
       ↓
VALIDATING
       ↓
Supabase Storage (private bucket)
       ↓
PROCESSING
       ↓
Text Extraction
       ↓
sections
       ↓
clauses
       ↓
document_chunks
       ↓
embeddings
       ↓
analyses
       ↓
READY
```

---

# 22. Document Deletion

When a user deletes a document:

```text
User
 ↓
DELETE document
 ↓
Mark deleted_at
 ↓
Background cleanup job
 ↓
Delete object-storage file
 ↓
Delete vectors
 ↓
Delete derived records
```

Database cascading relationships should remove dependent structured data where appropriate.

---

# 23. Retention Strategy

NyayaLens should support configurable retention policies.

Potential MVP policy:

```text
User deletes document
        ↓
Soft delete
        ↓
Retention period
        ↓
Permanent deletion
```

Permanent deletion must include:

* Original file
* Extracted text
* Sections
* Clauses
* Chunks
* Embeddings
* AI analyses
* Conversations linked exclusively to that document
* Reports
* Generated artifacts

Do not retain deleted legal documents indefinitely without a documented reason.

---

# 24. Sensitive Data Handling

Legal documents may contain:

* Names
* Addresses
* Salaries
* Contracts
* Identification numbers
* Financial information
* Confidential business information

Therefore:

### Database

Use encryption at rest provided by Supabase Database (managed PostgreSQL).

### Storage (Supabase)

Use:

```text
Private bucket (Supabase Storage)
```

Never:

```text
Public bucket
```

### Network

Use:

```text
TLS/HTTPS
```

### Logs

Never log:

```text
Full document content
Passwords
Access tokens
API keys
Private prompts
Sensitive extracted text
```

---

# 25. AI Data Storage Strategy

Do not store unnecessary copies of the same document text.

Recommended architecture:

```text
Original Document
       ↓
Supabase Storage (private bucket)

Extracted Text
       ↓
Supabase Database (PostgreSQL)

Chunks
       ↓
Supabase Database (PostgreSQL)

Embeddings
       ↓
pgvector (Supabase Database)

AI Results
       ↓
JSONB
```

AI results should be stored as structured JSON where the schema is likely to evolve.

---

# 26. JSONB Strategy

Use JSONB for flexible AI output.

Example:

```json
{
  "summary": "This employment agreement defines...",
  "parties": [
    {
      "name": "Example Company",
      "role": "Employer"
    }
  ],
  "key_terms": {
    "notice_period": "90 days",
    "probation": "6 months"
  }
}
```

However, important queryable entities should still have normalized tables.

For example:

```text
clauses
attention_items
citations
comparison_changes
actions
```

should not exist only inside a JSON blob.

---

# 27. AI Result Versioning

AI outputs can change when models or prompts change.

Store:

```text
model_name
prompt_version
created_at
```

Example:

```text
model_name:
gemini-2.x

prompt_version:
summary-v3
```

This enables:

* Reproducibility
* Debugging
* Evaluation
* Model comparison
* Regression testing

---

# 28. Recommended Database Constraints

Examples:

```sql
CHECK (file_size_bytes > 0);

CHECK (page_count IS NULL OR page_count > 0);

CHECK (
    attention_level IN ('LOW', 'MEDIUM', 'HIGH')
);

CHECK (
    status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'DISMISSED')
);
```

Use database constraints for important invariants rather than relying entirely on frontend validation.

---

# 29. Recommended SQLAlchemy Relationship Model

Conceptually:

```text
User
 ├── documents
 ├── conversations
 ├── comparisons
 ├── actions
 ├── reports
 └── audit_logs

Document
 ├── versions
 ├── sections
 ├── clauses
 ├── chunks
 ├── analyses
 ├── attention_items
 ├── conversations
 ├── comparisons
 ├── actions
 └── reports

Section
 ├── clauses
 └── chunks

Clause
 └── chunks

Chunk
 └── embedding

Conversation
 └── messages

Message
 └── citations

Comparison
 └── comparison_changes
```

---

# 30. Migration Strategy

Use Alembic.

Initial migration:

```text
001_initial_schema
```

Then incremental migrations:

```text
002_add_document_versions
003_add_vector_embeddings
004_add_attention_items
005_add_comparison_tables
006_add_action_center
007_add_audit_logs
```

Never manually modify production database tables without a migration.

---

# 31. Environment Configuration

Database connection should come from environment variables.

Example:

```env
SUPABASE_DB_URL=postgresql+psycopg://USER:PASSWORD@SUPABASE_HOST:5432/postgres
```

Never commit:

```text
SUPABASE_DB_URL
SUPABASE_SERVICE_ROLE_KEY
DB_PASSWORD
API_KEYS
JWT_SECRET (Supabase)
```

to GitHub.

Use:

```text
.env
```

locally and deployment-provider secret management in production.

---

# 32. Backup Strategy

Supabase Database should provide (managed):

* Automated daily backups
* Point-in-time recovery where supported
* Backup encryption
* Retention policy
* Periodic restore testing

A backup is useful only if restoration has actually been tested.

---

# 33. Performance Strategy

For MVP:

```text
Supabase Database (PostgreSQL)
+
pgvector
```

is sufficient.

Avoid introducing separate infrastructure prematurely.

Use:

* Proper indexes
* Pagination
* Connection pooling
* Async processing
* Vector indexes
* Query limits
* JSONB only where appropriate
* Background workers for heavy analysis

---

# 34. What Should NOT Be Stored

NyayaLens should not persist:

```text
Plaintext passwords
API keys
LLM provider secrets
JWT secrets
Raw authentication tokens
Unnecessary IP addresses
Full sensitive documents in logs
System prompts in audit logs
Provider credentials
```

---

# 35. MVP Tables

The minimum implementation should include:

```text
users
documents
sections
clauses
document_chunks
embeddings
analyses
attention_items
conversations
messages
citations
comparisons
comparison_changes
actions
reports
audit_logs
```

Optional for initial implementation:

```text
user_preferences
document_versions
```

---

# 36. Recommended Implementation Order

Build the database in this order:

### Phase 1 — Authentication

```text
users
user_preferences
```

### Phase 2 — Documents

```text
documents
document_versions
```

### Phase 3 — Document Intelligence

```text
sections
clauses
document_chunks
embeddings
```

### Phase 4 — AI

```text
analyses
attention_items
```

### Phase 5 — Q&A

```text
conversations
messages
citations
```

### Phase 6 — Comparison

```text
comparisons
comparison_changes
```

### Phase 7 — Action Center

```text
actions
```

### Phase 8 — Reports & Security

```text
reports
audit_logs
```

---

# 37. Critical MVP Relationships

The most important relationships are:

```text
users
  │
  └──< documents
          │
          ├──< sections
          │      └──< clauses
          │
          ├──< clauses
          │
          ├──< document_chunks
          │      └── embeddings
          │
          ├──< analyses
          │      └── attention_items
          │
          ├──< conversations
          │      └── messages
          │             └── citations
          │
          ├──< comparisons
          │      └── comparison_changes
          │
          ├──< actions
          │
          └──< reports
```

This structure directly supports the complete NyayaLens workflow:

```text
UPLOAD
   ↓
PROCESS
   ↓
UNDERSTAND
   ↓
ANALYZE
   ↓
ASK
   ↓
CITE
   ↓
COMPARE
   ↓
ACT
```

---

# 38. Final Database Architecture

```text
                         ┌─────────────────────┐
                         │       USERS         │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     DOCUMENTS       │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼────────────────────┐
              │                     │                    │
              ▼                     ▼                    ▼
        ┌───────────┐        ┌─────────────┐      ┌────────────┐
        │  SECTIONS │        │   CLAUSES   │      │   CHUNKS   │
        └───────────┘        └─────────────┘      └─────┬──────┘
                                                        │
                                                        ▼
                                                 ┌─────────────┐
                                                 │  EMBEDDINGS │
                                                 │  pgvector   │
                                                  │ (Supabase)  │
                                                 └──────┬──────┘
                                                        │
                                                        ▼
                                                   ┌────────┐
                                                   │  RAG   │
                                                   └───┬────┘
                                                       │
                                                       ▼
                                                    ┌───────┐
                                                    │  LLM  │
                                                    └───┬───┘
                                                        │
                              ┌─────────────────────────┼─────────────────────┐
                              │                         │                     │
                              ▼                         ▼                     ▼
                         ┌──────────┐             ┌───────────┐        ┌────────────┐
                         │ ANALYSIS │             │ MESSAGES  │        │ COMPARISON │
                         └────┬─────┘             └─────┬─────┘        └─────┬──────┘
                              │                         │                    │
                              ▼                         ▼                    ▼
                      ┌───────────────┐          ┌───────────┐      ┌──────────────────┐
                      │ ATTENTION     │          │ CITATIONS │      │ COMPARISON       │
                      │ ITEMS         │          └───────────┘      │ CHANGES          │
                      └───────┬───────┘                             └──────────────────┘
                              │
                              ▼
                         ┌──────────┐
                         │ ACTIONS  │
                         └────┬─────┘
                              │
                              ▼
                         ┌──────────┐
                         │ REPORTS  │
                         └──────────┘
```

---

# 39. Definition of Done

The database implementation is considered complete when:

* [ ] Supabase Database is configured
* [ ] pgvector is enabled (Supabase Database)
* [ ] Alembic migrations work
* [ ] User table exists
* [ ] Document ownership is enforced
* [ ] Document processing state is persisted
* [ ] Sections are stored
* [ ] Clauses are stored
* [ ] Chunks are stored
* [ ] Embeddings are stored
* [ ] Vector search works
* [ ] AI analyses are persisted
* [ ] Attention items are persisted
* [ ] Conversations work
* [ ] Messages are persisted
* [ ] Citations reference actual document chunks
* [ ] Comparisons work
* [ ] Comparison changes are persisted
* [ ] Actions are persisted
* [ ] Reports are tracked
* [ ] Audit logging exists
* [ ] User-level authorization is enforced
* [ ] Database indexes are configured
* [ ] Sensitive data is not unnecessarily logged
* [ ] Production backups are configured
* [ ] Database migrations are committed to GitHub

---

# 40. Final Principle

NyayaLens should treat the database as a **secure evidence layer**, not simply an application storage layer.

The most important invariant is:

```text
Authenticated User
        ↓
Authorized Document
        ↓
Verified Evidence
        ↓
Grounded AI Response
        ↓
Traceable Citation
```

Every AI answer that claims to come from a user's document should be traceable back to the exact stored document chunk, section, clause, and page whenever that information is available.

**NyayaLens — Understand. Review. Act.**
