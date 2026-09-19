# NyayaLens — Screen Specification

---

# 1. Design Objective

NyayaLens should feel:

* Trustworthy
* Calm
* Professional
* Simple
* Accessible
* Evidence-oriented

It should not look like a flashy generic AI chatbot.

---

# 2. Screen Inventory

| ID      | Screen             | Priority |
| ------- | ------------------ | -------- |
| SCR-001 | Landing            | P0       |
| SCR-002 | Login              | P0       |
| SCR-003 | Signup             | P0       |
| SCR-004 | Dashboard          | P0       |
| SCR-005 | Upload             | P0       |
| SCR-006 | Processing         | P0       |
| SCR-007 | Document Overview  | P0       |
| SCR-008 | Summary            | P0       |
| SCR-009 | Clause Explorer    | P0       |
| SCR-010 | Attention Analysis | P0       |
| SCR-011 | AI Q&A             | P0       |
| SCR-012 | Comparison         | P0       |
| SCR-013 | Action Center      | P0       |
| SCR-014 | Reports            | P1       |
| SCR-015 | Settings           | P1       |
| SCR-016 | Privacy            | P0       |

---

# 3. SCR-001 — Landing

## Purpose

Explain the product immediately.

### Hero

```text
Understand your legal documents.
Review what matters.
Know what to ask next.
```

Supporting text:

```text
AI-assisted document understanding with
source-grounded answers and practical review tools.
```

Primary CTA:

```text
Get Started
```

Secondary CTA:

```text
See How It Works
```

### Sections

1. Hero
2. Problem
3. How it works
4. Core features
5. Trust/security
6. Responsible AI
7. CTA
8. Footer

---

# 4. SCR-002 — Login

Components:

* Email
* Password
* Login button
* Forgot password
* Signup link

Requirements:

* Accessible labels
* Keyboard navigation
* Clear errors

---

# 5. SCR-003 — Signup

Components:

* Full name
* Email
* Password
* Confirm password
* Create account

---

# 6. SCR-004 — Dashboard

### Header

```text
Good morning, [Name]
Understand your documents with confidence.
```

### Primary CTA

```text
+ Upload Document
```

### Cards

```text
Documents
Needs Attention
Recent Questions
Pending Processing
```

### Recent Documents

Display:

* Filename
* Type
* Status
* Date
* Open action

---

# 7. SCR-005 — Upload

### Upload Zone

```text
Drag & drop your document
or
Browse Files
```

Display supported formats and size limit.

### Security message

```text
Your document is stored in private storage
and is only accessible to your account.
```

### Upload state

Show:

```text
Uploading...
```

---

# 8. SCR-006 — Processing

Use a stepper:

```text
✓ File validated
✓ Text extracted
● Analyzing clauses
○ Creating AI search index
○ Finalizing analysis
```

Do not falsely indicate completion.

---

# 9. SCR-007 — Document Overview

Header:

```text
Employment Agreement
Employment Agreement • PDF
```

Primary actions:

```text
Ask AI
Compare
Generate Report
```

Summary cards:

```text
Document Type
Pages
Clauses
Attention Items
```

---

# 10. SCR-008 — Summary

Sections:

### Overview

Plain-language explanation.

### Parties

List identified parties.

### Key Terms

Important dates and amounts.

### Obligations

What each party appears to be required to do.

### Important Conditions

Major conditions or restrictions.

---

# 11. SCR-009 — Clause Explorer

### Left/Top Filter

```text
All
Termination
Payment
Confidentiality
IP
Liability
Other
```

### Clause Card

```text
8. Termination

Notice period: 90 days

[View Source]
```

### Detail Panel

```text
Original Text
────────────────
...

Plain-Language Explanation
────────────────
...

Source
Section 8 • Page 6
```

---

# 12. SCR-010 — Attention Analysis

Each card:

```text
HIGH ATTENTION

Termination Notice

The agreement specifies a 90-day notice period.

Why this matters:
This may affect how much advance notice is required.

Source:
Section 8 • Page 6

[View Clause]
[Add Action]
```

Never use only red/yellow/green colors.

Include text labels.

---

# 13. SCR-011 — AI Q&A

### Chat Area

```text
Ask about this document
```

Suggested prompts:

```text
What are my main obligations?
What happens if I resign?
What is the notice period?
Are there confidentiality requirements?
```

### Answer

```text
DOCUMENT-GROUNDED

The agreement specifies a 90-day notice period...

Sources:
[Section 8 • Page 6]
```

### Insufficient Evidence

```text
INSUFFICIENT EVIDENCE

I couldn't find enough information in this document
to answer that confidently.
```

---

# 14. SCR-012 — Comparison

### Selection

```text
Document A
[Employment Agreement V1]

Document B
[Employment Agreement V2]

[Compare]
```

### Results

```text
3 Changes Found

HIGH
Termination Notice
30 days → 90 days

MEDIUM
...
```

Filters:

```text
All
Added
Removed
Modified
Unchanged
```

---

# 15. SCR-013 — Action Center

Sections:

```text
To Do
In Progress
Completed
```

Action card:

```text
Review termination clause

Priority: High

Source:
Employment Agreement

[Mark Complete]
```

---

# 16. SCR-014 — Reports

Display:

```text
Report Name
Document
Created
Type
Status
```

Actions:

```text
View
Generate
```

---

# 17. SCR-015 — Settings

Sections:

```text
Profile
Preferences
Security
Notifications
Account
```

---

# 18. SCR-016 — Privacy

Explain:

* Storage
* Processing
* AI use
* Data retention
* Deletion
* Security
* Limitations

Use plain language.

---

# 19. Global Components

Required reusable components:

```text
Button
Input
Select
Modal
Dialog
Toast
Card
Badge
Tabs
Table
Dropdown
Tooltip
Progress
Skeleton
Alert
EmptyState
ErrorState
```

NyayaLens-specific components:

```text
DocumentCard
ProcessingStepper
ClauseCard
AttentionCard
CitationBadge
CitationPanel
AIAnswer
ComparisonChange
ActionCard
DocumentViewer
```

---

# 20. Empty States

Example:

```text
No documents yet

Upload your first document to begin reviewing.

[Upload Document]
```

---

# 21. Error States

Example:

```text
We couldn't process this document.

Try uploading the file again.

[Retry]
```

Avoid technical stack traces.

---

# 22. Loading States

Use skeletons for:

* Dashboard
* Document overview
* Clauses
* Attention items
* Reports

Use progress indicators for long-running processing.

---

# 23. Responsive Requirements

### Desktop

Optimized for:

```text
1280px+
```

### Tablet

Support:

```text
768px+
```

### Mobile Web

Support:

```text
320px+
```

Important document content should remain readable without horizontal scrolling wherever possible.

---

# 24. Accessibility Requirements

Every interactive element must have:

* Accessible name
* Keyboard access
* Visible focus
* Appropriate semantic role
* Sufficient contrast

Do not rely exclusively on color.

Example:

Bad:

```text
🔴
```

Better:

```text
HIGH ATTENTION
```

---

# 25. Legal Disclaimer

Relevant screens should contain a concise disclaimer:

```text
NyayaLens provides AI-assisted legal information and
document-review assistance. It does not provide legal advice,
legal representation, or guarantee a legal outcome.
For important decisions, consult a qualified legal professional.
```

The wording may be refined during legal/product review.
