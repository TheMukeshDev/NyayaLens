# NyayaLens — Information Architecture

---

# 1. Architecture Overview

NyayaLens has two major website areas:

```text
Public Website
        +
Authenticated Workspace
```

---

# 2. Public Website

```text
/
├── features
├── how-it-works
├── security
├── about
├── login
└── signup
```

---

# 3. Authenticated Workspace

```text
/app
├── dashboard
├── documents
│   ├── upload
│   └── [documentId]
│       ├── summary
│       ├── clauses
│       ├── attention
│       ├── ask
│       └── actions
├── compare
├── actions
├── reports
├── settings
└── privacy
```

---

# 4. Dashboard

Dashboard contains:

```text
Welcome
 ↓
Recent Documents
 ↓
Processing Documents
 ↓
Attention Items
 ↓
Recent Questions
 ↓
Quick Actions
```

Quick actions:

```text
Upload Document
Compare Documents
View Actions
```

---

# 5. Documents

The document library provides:

* Search
* Filter
* Sort
* Processing status
* Document type
* Upload date
* Last analyzed date

Each document card should expose:

```text
Document Name
Type
Status
Updated
Actions
```

---

# 6. Document Workspace

Each document has its own workspace.

```text
Document
├── Overview
├── Summary
├── Clauses
├── Attention
├── Ask
└── Actions
```

The document name should remain visible so users always know which document they are reviewing.

---

# 7. Comparison

Comparison is a separate top-level feature because users may compare documents without first opening a single document workspace.

```text
Compare
 ├── Select Document A
 ├── Select Document B
 └── Results
```

---

# 8. Action Center

Global action center:

```text
Actions
├── To Do
├── In Progress
├── Completed
└── Dismissed
```

Users can filter by:

* Document
* Priority
* Type
* Status

---

# 9. Reports

```text
Reports
├── Document Review
├── Comparison
└── Action Plan
```

Reports should retain links back to their source document where appropriate.

---

# 10. Settings

Settings include:

```text
Profile
Preferences
Security
Notifications
Account
```

---

# 11. Privacy

Privacy should be independently accessible.

Contents:

* Document handling
* Storage
* AI processing
* Retention
* Deletion
* Responsible AI
* Limitations

---

# 12. Global Navigation

## Desktop

```text
┌──────────────────────────────────────┐
│ NyayaLens                            │
├──────────────┬───────────────────────┤
│ Dashboard    │                       │
│ Documents    │       Main Content    │
│ Compare      │                       │
│ Actions      │                       │
│ Reports      │                       │
│ Settings     │                       │
│ Privacy      │                       │
└──────────────┴───────────────────────┘
```

## Mobile

```text
Header
 ↓
Content
 ↓
Bottom/Drawer Navigation
```

---

# 13. Information Hierarchy

Every document page should prioritize:

```text
1. What is this?
2. What matters?
3. What needs attention?
4. What can I ask?
5. What should I do next?
```

---

# 14. Content Hierarchy

### Level 1

Document title

### Level 2

Primary section

### Level 3

Clause

### Level 4

Explanation

### Level 5

Supporting source

---

# 15. Search Architecture

Global document search:

```text
Documents
 ↓
Search
 ↓
Filename / Type / Metadata
```

Document search:

```text
Document
 ↓
Search
 ↓
Sections
Clauses
Content
```

Q&A should remain separate from simple keyword search.

---

# 16. Accessibility Structure

The information architecture must support:

* Logical heading order
* Semantic navigation landmarks
* Keyboard navigation
* Screen-reader labels
* Consistent focus order
* Accessible status announcements

---

# 17. URL Strategy

Use readable URLs:

```text
/app/dashboard
/app/documents
/app/documents/upload
/app/documents/{id}
/app/documents/{id}/summary
/app/documents/{id}/clauses
/app/documents/{id}/attention
/app/documents/{id}/ask
/app/documents/{id}/actions
/app/compare
/app/actions
/app/reports
/app/settings
/app/privacy
```

Avoid exposing sensitive information in URLs.
