# NyayaLens — Feature Requirements

---

# 1. Functional Requirements

## FR-001 — Authentication

The system shall provide secure user registration and login.

### Requirements

* Email validation
* Password hashing
* Session/token management
* Authentication middleware
* Logout
* Account status validation

---

# 2. Document Upload

## FR-002 — File Upload

The system shall allow authenticated users to upload supported legal documents.

### Supported Formats

MVP:

```text
PDF
DOCX
JPG
JPEG
PNG
```

### Requirements

* File size limits
* MIME validation
* Extension validation
* Secure filename handling
* Malware scanning
* Private storage
* Upload progress

---

# 3. Document Processing

## FR-003 — Processing Pipeline

The system shall process uploaded documents asynchronously.

```text
Upload
 ↓
Validation
 ↓
Storage
 ↓
Text Extraction
 ↓
OCR if required
 ↓
Page Mapping
 ↓
Section Detection
 ↓
Clause Detection
 ↓
Chunking
 ↓
Embeddings
 ↓
AI Analysis
 ↓
READY
```

---

# 4. Document Classification

## FR-004

The system should identify the general document category where possible.

Examples:

```text
Employment Agreement
Rental Agreement
NDA
Service Agreement
Vendor Agreement
Loan Agreement
Policy
Other
```

The classification should be treated as an AI-generated classification and not as a definitive legal classification.

---

# 5. Summary

## FR-005

The system shall generate a concise plain-language summary.

The summary may include:

* Purpose
* Parties
* Key obligations
* Important dates
* Financial terms
* Termination conditions
* Major restrictions

---

# 6. Key Information Extraction

## FR-006

The system shall extract structured information where identifiable.

### Entities

* People
* Organizations
* Dates
* Amounts
* Currency
* Notice periods
* Deadlines
* Locations

---

# 7. Clause Detection

## FR-007

The system shall identify meaningful clauses.

Examples:

```text
Termination
Compensation
Confidentiality
Intellectual Property
Liability
Indemnification
Dispute Resolution
Governing Law
Notice
Renewal
Payment
```

Each clause should retain source metadata.

---

# 8. Clause Explorer

## FR-008

The interface shall allow users to:

* Browse clauses
* Search clauses
* Filter by type
* View original text
* View simplified explanation
* Navigate to source page

---

# 9. Attention Analysis

## FR-009

The system shall identify areas that may deserve closer attention.

Each attention item should include:

```text
Title
Category
Attention Level
Explanation
Source
Suggested Next Step
```

The product shall avoid representing attention levels as definitive legal judgments.

---

# 10. Document Q&A

## FR-010

Users shall be able to ask natural-language questions about their document.

Example:

```text
"What happens if I resign?"
```

The system should:

1. Retrieve relevant evidence.
2. Generate an answer.
3. Validate citations.
4. Return supporting sources.

---

# 11. Citation System

## FR-011

Document-grounded responses should provide source information when available.

Citation metadata:

```text
Section
Clause
Page
Chunk
Source Text
```

The system shall reject invalid or fabricated citation references.

---

# 12. Evidence States

## FR-012

AI answers should distinguish:

```text
DOCUMENT-GROUNDED
GENERAL-INFORMATION
INSUFFICIENT-EVIDENCE
```

This prevents users from confusing general legal information with information found in their document.

---

# 13. Document Comparison

## FR-013

The system shall compare two documents.

It shall identify:

```text
ADDED
REMOVED
MODIFIED
UNCHANGED
```

Important changes should receive an importance level.

---

# 14. Action Center

## FR-014

The system shall convert review findings into actionable tasks.

Examples:

```text
Review termination clause
Verify payment terms
Ask professional about non-compete
Confirm notice period
Check renewal condition
```

---

# 15. Professional Questions

## FR-015

The system shall generate questions that a user may discuss with a qualified legal professional.

Example:

```text
"Should I clarify how the 90-day notice period interacts with probation?"
```

The system should not instruct users that a specific legal outcome is guaranteed.

---

# 16. Reports

## FR-016

The system should generate downloadable review reports containing:

* Document information
* Summary
* Key clauses
* Attention items
* Questions
* Actions
* Citations
* Disclaimer
* Timestamp

---

# 17. Document History

## FR-017

Users shall be able to view their uploaded documents and their processing status.

---

# 18. Privacy

## FR-018

The system shall:

* Isolate user documents
* Use Supabase Storage (private buckets)
* Enforce backend authorization
* Avoid unnecessary sensitive logging
* Provide document deletion
* Protect secrets

---

# 19. Accessibility

## FR-019

The website shall support:

* Keyboard navigation
* Visible focus states
* Semantic HTML
* Accessible labels
* Sufficient contrast
* Responsive layouts
* Readable typography
* Non-color-only status indicators

---

# 20. Security

## FR-020

The backend shall implement:

* Authentication
* Authorization
* File validation
* Malware scanning
* Rate limiting
* Secure headers
* CORS restrictions
* Input validation
* Output validation
* Prompt-injection defenses
* Secure secret management

---

# 21. Performance

## FR-021

The system shall:

* Process documents asynchronously
* Paginate large document lists
* Limit expensive AI requests
* Reuse embeddings where appropriate
* Cache safe repeat operations
* Avoid unnecessary LLM calls

---

# 22. AI Safety

## FR-022

The system shall:

* Treat document content as untrusted data
* Avoid following instructions embedded inside documents
* Refuse to fabricate evidence
* State uncertainty
* Provide citations where possible
* Display responsible-AI messaging

---

# 23. Non-Functional Requirements

| Category        | Requirement                                      |
| --------------- | ------------------------------------------------ |
| Availability    | Production deployment should be reliable         |
| Security        | Sensitive documents protected                    |
| Performance     | UI remains responsive                            |
| Accessibility   | WCAG-oriented implementation                     |
| Scalability     | Architecture supports increasing documents/users |
| Maintainability | Modular frontend/backend                         |
| Observability   | Safe structured logging                          |
| Reliability     | Failed processing can be retried                 |
| Privacy         | Private storage and controlled access            |

---

# 24. MVP Scope

### Must Have

```text
Authentication
Document Upload
Document Processing
Summary
Clause Extraction
Attention Analysis
RAG Q&A
Citations
Comparison
Action Center
Privacy
Accessibility
```

### Should Have

```text
Reports
Document History
Professional Question Generator
```

### Future

```text
Voice
Multilingual UI
Collaboration
Professional Workspace
Advanced Analytics
```

---

# 25. Out of Scope

The MVP will not provide:

* Legal representation
* Court filing
* Guaranteed legal conclusions
* Lawyer replacement
* Autonomous legal decisions
* Native Android/iOS applications
* Custom foundation-model training
* Blockchain
* Kubernetes
* Complex microservice infrastructure

---

# 26. Acceptance Standard

A feature is complete only when:

```text
Frontend
   +
Backend
   +
Database
   +
Security
   +
Validation
   +
Testing
```

are implemented consistently.
