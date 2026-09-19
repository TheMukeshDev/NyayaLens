# NyayaLens — Problem Statement

**Product:** NyayaLens
**Tagline:** Understand. Review. Act.
**Challenge:** AI for Legal Assistance & Access
**Version:** 1.0

---

## 1. Problem Overview

Legal documents are often difficult for ordinary people to understand.

Employment agreements, rental agreements, service contracts, loan documents, notices, policies, and other legal documents frequently contain:

* Complex legal terminology
* Long and dense clauses
* Important obligations hidden inside paragraphs
* Financial conditions
* Notice periods
* Termination conditions
* Confidentiality requirements
* Renewal conditions
* Dispute-resolution clauses
* Deadlines and dates

A person may technically have access to a document while still lacking the ability to understand what it practically means.

This creates an **access-to-understanding gap**.

---

## 2. Core Problem

The problem is not simply the absence of legal information.

The problem is that users often cannot efficiently:

1. Understand a legal document in plain language.
2. Find important clauses.
3. Identify obligations and deadlines.
4. Locate terms that require closer attention.
5. Ask questions about their own document.
6. Verify where an AI answer came from.
7. Compare different versions of a document.
8. Convert document findings into practical next steps.
9. Prepare focused questions for a qualified legal professional.

---

## 3. Current User Experience

A typical user may currently follow this process:

```text
Receive legal document
        ↓
Open PDF/DOCX
        ↓
Read dozens of pages
        ↓
Search unfamiliar terminology
        ↓
Try to identify important clauses
        ↓
Search internet for explanations
        ↓
Ask friends / colleagues
        ↓
Possibly consult a lawyer
```

This process is:

* Time-consuming
* Difficult for non-experts
* Fragmented
* Prone to misunderstanding
* Difficult to verify
* Especially challenging for long documents

---

## 4. The AI Problem

Generic AI chatbots can explain legal concepts, but a generic chatbot does not automatically provide reliable document-grounded assistance.

Potential problems include:

### Hallucination

The AI may generate information that is not present in the user's document.

### Missing Context

A clause may depend on another section elsewhere in the agreement.

### Lack of Traceability

The user may not know which clause or page supports the answer.

### Overconfidence

The system may present an interpretation as definitive legal advice.

### Privacy Risk

Users may upload confidential legal documents to systems without understanding how their data is handled.

NyayaLens is designed specifically to address these problems.

---

## 5. Target Problem

NyayaLens focuses on:

> **Helping people understand and review their own legal documents using grounded AI assistance while preserving source traceability, privacy, and appropriate human-review boundaries.**

---

## 6. Target Users

### Primary Users

* Students
* Employees
* Freelancers
* Tenants
* Small business owners
* Startup founders
* Consumers
* Individuals reviewing contracts

### Secondary Users

* Legal professionals
* HR professionals
* Startup teams
* Administrative teams
* Community organizations

---

## 7. User Pain Points

### Pain Point 1 — Complexity

Legal language is often difficult for non-lawyers.

### Pain Point 2 — Time

Users may spend significant time manually searching long documents.

### Pain Point 3 — Hidden Information

Important conditions may be buried inside lengthy clauses.

### Pain Point 4 — Uncertainty

Users may not know which parts deserve additional attention.

### Pain Point 5 — Verification

Users need to know why an AI answer was generated.

### Pain Point 6 — Comparison

Manually comparing two versions of a contract is difficult.

### Pain Point 7 — Action

Even after understanding a clause, users may not know what question to ask next.

---

## 8. Problem Boundaries

NyayaLens does **not** attempt to replace:

* Lawyers
* Courts
* Legal representation
* Professional legal opinions
* Formal legal review

The system provides:

> **AI-powered legal information and document-review assistance, not legal advice or representation.**

---

## 9. Proposed Problem-Solving Approach

NyayaLens introduces a structured workflow:

```text
UPLOAD
   ↓
UNDERSTAND
   ↓
EXTRACT
   ↓
REVIEW
   ↓
ASK
   ↓
VERIFY
   ↓
COMPARE
   ↓
ACT
```

### Understand

Generate a plain-language document summary.

### Extract

Identify:

* Parties
* Dates
* Amounts
* Obligations
* Clauses
* Conditions

### Review

Highlight areas requiring attention.

### Ask

Allow users to ask questions about their document.

### Verify

Show supporting section/page/clause citations.

### Compare

Compare document versions and identify changes.

### Act

Generate review checklists and questions for professional discussion.

---

## 10. Why This Matters

Legal access is not only about having access to legal documents.

It is also about being able to:

* Understand information
* Locate relevant provisions
* Ask informed questions
* Recognize uncertainty
* Seek professional help when necessary

NyayaLens addresses this gap through an accessible, grounded AI interface.

---

## 11. Challenge Alignment

| Challenge Requirement       | NyayaLens Response                                 |
| --------------------------- | -------------------------------------------------- |
| Legal assistance            | Document understanding and review assistance       |
| Access to legal information | Plain-language explanations                        |
| Generative AI               | Summarization, extraction, Q&A, comparison         |
| User accessibility          | Simple web interface                               |
| Trust                       | Source citations                                   |
| Security                    | Private storage and user-level authorization       |
| Responsible AI              | Clear limitations and human-review boundaries      |
| Practical utility           | Action center and professional-question generation |

---

## 12. Core Problem Statement

> **People frequently receive legal documents they must understand but lack the time, legal expertise, or tools to efficiently identify important clauses, obligations, changes, and areas requiring attention. NyayaLens uses grounded generative AI to make document understanding and review more accessible, traceable, and actionable without presenting itself as a substitute for qualified legal advice.**

---

## 13. Success Definition

The problem is considered meaningfully addressed when a user can:

```text
Upload a document
        ↓
Understand it quickly
        ↓
Find important clauses
        ↓
Ask document-specific questions
        ↓
See supporting sources
        ↓
Compare versions
        ↓
Generate practical next steps
```

with appropriate security and responsible-AI safeguards.
