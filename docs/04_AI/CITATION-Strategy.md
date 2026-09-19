# NyayaLens — Citation Strategy

**Version:** 1.0

---

# 1. Objective

Citations are a core trust mechanism in NyayaLens.

A user should be able to understand:

> **Where did this answer come from?**

---

# 2. Citation Principle

For document-grounded factual claims:

```text
Claim
 ↓
Evidence
 ↓
Source
```

The AI should not provide unsupported document-specific claims.

---

# 3. Citation Metadata

Each citation should contain:

```json
{
  "id": "cit_123",
  "document_id": "doc_123",
  "chunk_id": "chunk_18",
  "section": "8. Termination",
  "clause": "8.2",
  "page": 6
}
```

---

# 4. Source Hierarchy

Preferred source:

```text
Clause
 ↓
Section
 ↓
Page
 ↓
Document
```

The more specific the source, the better.

---

# 5. Citation Lifecycle

```text id="j23q8h"
Document Processing
       ↓
Chunk Creation
       ↓
Source Metadata
       ↓
Embedding
       ↓
Retrieval
       ↓
AI Response
       ↓
Citation IDs
       ↓
Backend Validation
       ↓
Frontend Citation
```

---

# 6. Citation Generation

The model should reference retrieved chunk IDs rather than inventing page numbers.

Example:

```json
{
  "answer": "The agreement specifies a 90-day notice period.",
  "citations": [
    {
      "chunk_id": "chunk_18"
    }
  ]
}
```

The backend resolves:

```text
chunk_18
 ↓
Section 8
 ↓
Clause 8.2
 ↓
Page 6
```

---

# 7. Citation Validation

Every citation must pass:

```text id="6f9f9k"
Does chunk exist?
        ↓
Does chunk belong to document?
        ↓
Does document belong to authenticated user?
        ↓
Does source metadata exist?
        ↓
Is citation structurally valid?
```

If any answer is NO:

```text
Citation rejected.
```

---

# 8. Citation Ownership

This is a critical security requirement.

A citation must never expose information from:

* Another user's document
* Another document outside the current comparison
* Deleted documents
* Unauthorized resources

---

# 9. Citation UI

Example:

```text id="h7f2sw"
The notice period is 90 days. [1]
```

Selecting `[1]` opens:

```text
SOURCE

Section 8 — Termination
Clause 8.2
Page 6

Original Text
────────────────
...
```

---

# 10. Source Navigation

Where supported, clicking a citation should navigate the document viewer to:

```text
Page
+
Relevant section
+
Relevant clause
```

This creates a direct verification workflow.

---

# 11. Citation States

### Valid

```text
SOURCE VERIFIED
```

### Missing

```text
SOURCE NOT AVAILABLE
```

### Insufficient Evidence

```text
INSUFFICIENT EVIDENCE
```

The frontend must not imply that an answer is verified if citation validation failed.

---

# 12. Multiple Citations

An answer may have multiple supporting sources.

Example:

```text
The employee must provide 90 days' notice [1]
and return company property upon departure [2].
```

Each claim should be connected to the most relevant source.

---

# 13. Citation Granularity

Prefer:

```text
Section + Clause + Page
```

over:

```text
Page 6
```

when the information is available.

---

# 14. Citation and Hallucination Control

Citations do not automatically prove that an answer is correct.

Therefore:

```text
Retrieved evidence
+
Citation validation
+
Answer validation
```

should be used together.

A model should not be allowed to cite a chunk merely because the chunk exists.

---

# 15. Unsupported Answer

If evidence does not support the answer:

```text
INSUFFICIENT-EVIDENCE

I couldn't find enough information in this document
to answer that confidently.
```

Do not generate a citation simply to make the answer appear authoritative.

---

# 16. General Information

For general legal information that is not derived from the user's document:

```text
GENERAL-INFORMATION
```

Document citations should not be falsely attached to general legal claims.

If external authoritative sources are introduced in a future version, they should use a separate source type.

---

# 17. Comparison Citations

For comparison:

```text
Document A
Section 8 • Page 6

Document B
Section 8 • Page 7
```

A change should ideally expose both sides.

---

# 18. Citation Data Model

Recommended relationships:

```text id="3lqj4w"
Document
   ↓
Section
   ↓
Clause
   ↓
Chunk
   ↓
Citation
   ↓
Message / Analysis
```

---

# 19. Citation API Contract

Example:

```text
GET /api/v1/citations/{citation_id}
```

Response:

```json
{
  "section": "8. Termination",
  "clause": "8.2",
  "page": 6,
  "document_id": "doc_123",
  "source_text": "..."
}
```

---

# 20. Citation Security Rule

> **Never trust citation IDs supplied by the model or frontend.**

Every citation must be resolved and authorized by the backend.

---

# 21. Citation Quality Metrics

Track:

### Citation Validity

Percentage of returned citations that resolve successfully.

### Citation Support

Percentage of citations that actually support the associated claim.

### Citation Coverage

Percentage of document-grounded answers containing citations.

Target:

```text
Citation validity: ≥ 99%
Citation coverage: ≥ 95%
```

The exact targets should be validated against the evaluation dataset.

---

# 22. Final Citation Principle

> **A citation is not decoration. It is the bridge between an AI-generated explanation and the underlying document evidence.**
