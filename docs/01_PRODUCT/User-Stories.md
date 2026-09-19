# NyayaLens — User Stories

---

## 1. Authentication

### US-001 — Create Account

**As a user,**
I want to create an account
so that my documents are associated with my private workspace.

**Acceptance Criteria**

* User can register with email and password.
* Email format is validated.
* Password is securely hashed.
* Duplicate email is rejected.
* User receives appropriate validation feedback.

---

### US-002 — Login

**As a registered user,**
I want to log in securely
so that I can access my documents.

**Acceptance Criteria**

* Valid credentials allow access.
* Invalid credentials do not reveal which field was incorrect.
* Session/token is securely managed.

---

# 2. Document Upload

### US-003 — Upload Document

**As a user,**
I want to upload a legal document
so that NyayaLens can analyze it.

**Acceptance Criteria**

* PDF/DOCX/images are supported according to configured limits.
* File size is validated.
* MIME type is validated server-side.
* Unsafe files are rejected.
* Upload status is displayed.

---

### US-004 — Processing Status

**As a user,**
I want to see document processing progress
so that I know when analysis is ready.

**Acceptance Criteria**

The UI shows states such as:

```text
Validating
Processing
Extracting
Analyzing
Ready
Failed
```

---

# 3. Document Understanding

### US-005 — Summary

**As a user,**
I want a plain-language summary
so that I can understand the document quickly.

**Acceptance Criteria**

Summary includes relevant information such as:

* Document type
* Parties
* Purpose
* Key terms
* Major obligations

---

### US-006 — Key Information

**As a user,**
I want important dates, amounts, parties, and obligations extracted
so that I can find them quickly.

---

# 4. Clause Explorer

### US-007 — Browse Clauses

**As a user,**
I want to browse detected clauses
so that I can navigate the document efficiently.

---

### US-008 — Clause Details

**As a user,**
I want to see a clause's original text and explanation
so that I can understand its meaning.

---

# 5. Attention Analysis

### US-009 — Areas Requiring Attention

**As a user,**
I want the system to highlight areas that may deserve closer review
so that I can focus my time.

**Acceptance Criteria**

Each item should include:

* Category
* Attention level
* Explanation
* Source
* Suggested next step

The system must avoid presenting an AI-generated attention level as a definitive legal conclusion.

---

# 6. AI Q&A

### US-010 — Ask a Document Question

**As a user,**
I want to ask questions about my document
so that I can understand specific provisions.

---

### US-011 — Grounded Answer

**As a user,**
I want answers to be grounded in my document
so that I can verify them.

---

### US-012 — Citation

**As a user,**
I want to see the section and page supporting an answer
so that I can verify the source.

---

### US-013 — Insufficient Evidence

**As a user,**
I want the system to tell me when the document does not contain enough information
so that I am not given a fabricated answer.

---

# 7. Document Comparison

### US-014 — Select Documents

**As a user,**
I want to select two documents
so that I can compare them.

---

### US-015 — Detect Changes

**As a user,**
I want to see added, removed, and modified clauses
so that I can understand what changed.

---

### US-016 — Explain Changes

**As a user,**
I want a plain-language explanation of important changes
so that I can focus on meaningful differences.

---

# 8. Action Center

### US-017 — Review Checklist

**As a user,**
I want a checklist of things to review
so that I can systematically work through the document.

---

### US-018 — Professional Questions

**As a user,**
I want suggested questions to discuss with a qualified professional
so that I can have a more productive consultation.

---

### US-019 — Track Actions

**As a user,**
I want to mark actions as complete
so that I can track my review progress.

---

# 9. Reports

### US-020 — Generate Report

**As a user,**
I want to generate a review report
so that I can keep a structured record of my analysis.

---

# 10. Privacy

### US-021 — Private Documents

**As a user,**
I want my documents to be private
so that other users cannot access them.

---

### US-022 — Delete Document

**As a user,**
I want to delete my document
so that I can control my stored information.

---

# 11. Accessibility

### US-023 — Keyboard Navigation

**As a user,**
I want the website to be usable with a keyboard
so that I am not dependent on a mouse.

---

### US-024 — Readable Interface

**As a user,**
I want clear typography, labels, and contrast
so that the interface is easy to understand.

---

# 12. Error Handling

### US-025 — Processing Failure

**As a user,**
I want clear information when processing fails
so that I know what to do next.

---

# 13. Priority

| ID     | Feature                | Priority |
| ------ | ---------------------- | -------- |
| US-001 | Registration           | P0       |
| US-002 | Login                  | P0       |
| US-003 | Upload                 | P0       |
| US-004 | Processing             | P0       |
| US-005 | Summary                | P0       |
| US-007 | Clause Explorer        | P0       |
| US-009 | Attention Analysis     | P0       |
| US-010 | Q&A                    | P0       |
| US-012 | Citations              | P0       |
| US-014 | Comparison             | P0       |
| US-017 | Checklist              | P1       |
| US-018 | Professional Questions | P1       |
| US-020 | Reports                | P1       |
| US-021 | Privacy                | P0       |
| US-023 | Accessibility          | P0       |

---

# 14. Critical End-to-End Story

```text
As a user,
I want to upload my legal document,
understand its important terms,
ask questions about it,
verify answers against the source,
compare another version,
and receive practical next steps,
so that I can make a more informed decision
and know when professional review may be appropriate.
```
