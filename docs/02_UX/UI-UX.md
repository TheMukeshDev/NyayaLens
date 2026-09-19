# NyayaLens — UI/UX Specification

**Product:** NyayaLens
**Tagline:** Understand. Review. Act.
**Product Type:** AI-powered Legal Document Assistance Web Platform
**Platform:** Responsive Web Application
**Primary Target:** Desktop Web
**Secondary Targets:** Tablet Web, Mobile Web
**Version:** 1.0
**Status:** Development Specification

---

# 1. Product Definition

NyayaLens is a **web-based AI legal document assistance platform** that helps users understand, review, compare, and prepare actions around legal documents.

NyayaLens does **not** position itself as a lawyer or legal representative.

The platform should help users:

* Understand complicated legal documents
* Convert legal language into plain language
* Find important clauses
* Identify obligations and deadlines
* Highlight areas requiring attention
* Ask questions about their documents
* Compare two document versions
* Generate review checklists
* Prepare questions for a legal professional

## Core Product Flow

```text
LANDING PAGE
     ↓
SIGN UP / LOGIN
     ↓
DASHBOARD
     ↓
UPLOAD DOCUMENT
     ↓
PROCESSING
     ↓
DOCUMENT OVERVIEW
     ↓
┌────────────┬────────────┬─────────────┐
│ Understand │   Review   │     Ask     │
└────────────┴────────────┴─────────────┘
     ↓             ↓             ↓
   Summary      Clauses       AI Q&A
     ↓             ↓             ↓
     └─────────────┴─────────────┘
                   ↓
              COMPARE
                   ↓
             ACTION CENTER
                   ↓
        QUESTIONS / CHECKLIST
                   ↓
             EXPORT / SHARE
```

---

# 2. UX Design Principles

## 2.1 Clarity First

Legal documents are already complicated.

The interface must not add another layer of complexity.

Use:

```text
Simple language
Clear hierarchy
Short explanations
Progressive disclosure
Visible context
```

Avoid:

```text
Dense dashboards
Large walls of text
Unnecessary animations
Technical AI terminology
Legal jargon in navigation
```

---

# 3. Trust-First Design

Legal technology requires a high level of user trust.

NyayaLens should visually communicate:

```text
Private
Transparent
Evidence-based
AI-assisted
Professional
Human-review friendly
```

Do not use a visual style that makes the product look like:

* A cryptocurrency dashboard
* A gaming interface
* A generic chatbot
* An experimental AI demo

---

# 4. Desktop-First Web Layout

The primary breakpoint is desktop.

Recommended application width:

```text
Maximum content width:
1440px
```

Main content:

```text
1200–1280px
```

Sidebar:

```text
240px
```

Top navigation:

```text
64–72px
```

---

# 5. Responsive Breakpoints

```text
Mobile:
0–767px

Tablet:
768–1023px

Desktop:
1024–1439px

Large Desktop:
1440px+
```

## Desktop

Persistent sidebar.

## Tablet

Collapsed sidebar.

## Mobile

Sidebar becomes a drawer.

Bottom navigation may be used for:

```text
Home
Documents
Ask
Actions
```

The product remains a **website** at every breakpoint.

---

# 6. Global Website Structure

## Public Website

```text
/
├── Home
├── Features
├── How It Works
├── Security & Privacy
├── About
├── Login
└── Sign Up
```

## Authenticated Application

```text
/app
├── dashboard
├── documents
├── documents/:id
├── documents/:id/summary
├── documents/:id/review
├── documents/:id/ask
├── compare
├── actions
├── settings
└── privacy
```

---

# 7. Global Navigation

## Public Navigation

```text
┌──────────────────────────────────────────────────────────────┐
│ ⚖ NyayaLens   Features   How It Works   Security   About     │
│                                      [Login] [Get Started]    │
└──────────────────────────────────────────────────────────────┘
```

Logo:

```text
NyayaLens
Understand. Review. Act.
```

---

# 8. Authenticated Navigation

```text
┌─────────────────────────────────────────────────────────────────┐
│ NyayaLens                          Search   🔔   Profile        │
├──────────────┬──────────────────────────────────────────────────┤
│              │                                                  │
│ Dashboard    │                                                  │
│ Documents    │                                                  │
│ Review       │                MAIN CONTENT                      │
│ Compare      │                                                  │
│ Ask          │                                                  │
│ Actions      │                                                  │
│              │                                                  │
│ ───────────  │                                                  │
│ Settings     │                                                  │
│ Privacy      │                                                  │
│              │                                                  │
│              │                                                  │
│ Help         │                                                  │
└──────────────┴──────────────────────────────────────────────────┘
```

---

# 9. Navigation Behavior

The active page must always be visually identifiable.

Example:

```text
▣ Dashboard
▤ Documents
◉ Review
⇄ Compare
◯ Ask NyayaLens
☑ Action Center
```

Active navigation:

```text
Background: subtle blue tint
Text: primary blue
Icon: primary blue
```

Do not use only color to indicate active state.

---

# 10. Color System

## Primary

```text
Deep Navy
#0F172A
```

Purpose:

* Logo
* Headings
* Navigation
* Primary dark surfaces

## Primary Action

```text
Blue
#2563EB
```

Purpose:

* CTA buttons
* Links
* Active controls
* Important actions

## Page Background

```text
#F8FAFC
```

## Card / Surface

```text
#FFFFFF
```

## Primary Text

```text
#111827
```

## Secondary Text

```text
#64748B
```

## Border

```text
#E2E8F0
```

## Success

```text
#15803D
```

## Warning

```text
#B45309
```

## Attention

```text
#DC2626
```

## Information

```text
#0369A1
```

---

# 11. Typography

Primary font:

```text
Inter
```

Fallback:

```text
system-ui, sans-serif
```

## Desktop

```text
Hero H1       48px / 56px / 700
H1            36px / 44px / 700
H2            30px / 38px / 700
H3            24px / 32px / 600
H4            20px / 28px / 600
Body Large    18px / 28px / 400
Body          16px / 24px / 400
Small         14px / 20px / 400
Caption       12px / 18px / 500
```

## Mobile

```text
H1 30px
H2 24px
H3 20px
Body 16px
```

Never use extremely small text for legal information.

---

# 12. Spacing System

Use an 8-point system.

```text
4px
8px
16px
24px
32px
40px
48px
64px
80px
96px
```

Recommended:

```text
Card padding: 24px
Section spacing: 48–80px
Page horizontal padding: 32px
```

Mobile:

```text
Page padding: 16px
Card padding: 16–20px
```

---

# 13. Component System

The website should have reusable components.

```text
Button
Input
Select
Textarea
SearchBar
Card
Badge
Alert
Modal
Drawer
Tooltip
Tabs
Accordion
ProgressBar
FileUploader
DocumentCard
ClauseCard
Citation
ChatMessage
ComparisonRow
ChecklistItem
EmptyState
LoadingState
ErrorState
Toast
```

Components must not be recreated separately for every screen.

---

# 14. Button Specification

## Primary

```text
[ Upload Document ]
```

## Secondary

```text
[ Compare Documents ]
```

## Ghost

```text
View Details →
```

## Destructive

```text
Delete Document
```

## Button Rules

Minimum:

```text
Height: 44px
```

Primary CTA should always be visually obvious.

Avoid multiple competing primary buttons on the same screen.

---

# 15. Landing Page

## Purpose

Convert a visitor into a user while immediately explaining the product.

---

## Hero

```text
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│          Understand your legal documents.                    │
│                 Without the legal jargon.                    │
│                                                              │
│  Review important clauses, ask questions, compare versions   │
│  and prepare your next steps with AI assistance.              │
│                                                              │
│       [ Get Started ]     [ See How It Works ]               │
│                                                              │
│       Private • AI-assisted • Human review encouraged         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

Hero visual should show a simplified document-analysis interface rather than a stock lawyer photograph.

---

# 16. Landing Page Sections

Order:

```text
1. Hero
2. Trust Indicators
3. How NyayaLens Works
4. Core Features
5. Example Document Review
6. Security & Privacy
7. Responsible AI
8. FAQ
9. Final CTA
10. Footer
```

---

# 17. Trust Indicators

Use concise indicators:

```text
🔒 Private by design

AI-assisted analysis

Document-grounded answers

Human review encouraged
```

Avoid unsupported claims such as:

```text
100% secure
100% accurate
Guaranteed legal advice
```

---

# 18. How It Works

Three/four-step visual flow:

```text
01
Upload

Upload your legal document.

↓

02
Understand

Get a plain-language explanation.

↓

03
Review

Explore clauses and areas needing attention.

↓

04
Act

Generate questions and next-step checklists.
```

---

# 19. Feature Section

Cards:

### Understand

```text
Plain-language summaries
Important dates
Money and obligations
Parties and responsibilities
```

### Review

```text
Clause Explorer
Attention areas
Missing/inconsistent information
```

### Ask

```text
Document-grounded AI Q&A
Section citations
Follow-up questions
```

### Compare

```text
Compare two versions
See added/removed/changed clauses
```

### Act

```text
Review checklist
Questions for a professional
Export report
```

---

# 20. Login Page

Desktop:

```text
┌───────────────────────┬───────────────────────────┐
│                       │                           │
│      NyayaLens        │       Welcome back       │
│                       │                           │
│ Understand. Review.   │ Email                     │
│ Act.                  │ [____________________]    │
│                       │                           │
│                       │ Password                  │
│                       │ [____________________]    │
│                       │                           │
│                       │ [ Sign In ]               │
│                       │                           │
│                       │ Forgot password?           │
│                       │                           │
└───────────────────────┴───────────────────────────┘
```

---

# 21. Dashboard

The dashboard is the user's primary workspace.

## Header

```text
Good morning

Understand your documents and decide your next step.
```

Primary CTA:

```text
[ + Upload Document ]
```

---

# 22. Dashboard Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Welcome back                                                  │
│ Your document workspace                                       │
│                                      [ + Upload Document ]     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Documents      Needs Review      Questions      Actions      │
│    12              3               5             7           │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ Recent Documents                                              │
│                                                              │
│ Employment Agreement     Reviewed     12 Sep                 │
│ Rental Agreement         Needs Review 10 Sep                 │
│ NDA                       Processing    09 Sep                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

# 23. Dashboard Cards

## Statistics

Use simple cards:

```text
Documents
12
```

```text
Needs Attention
3
```

```text
Open Questions
5
```

```text
Pending Actions
7
```

Do not make statistics visually dominant over actual documents.

---

# 24. Document Card

```text
┌────────────────────────────────────────────┐
│ 📄 Employment Agreement                    │
│ Employment Contract                        │
│                                            │
│ Last reviewed: 12 Sep 2026                 │
│                                            │
│ ● Analysis Complete                        │
│                                            │
│ [ Open Review ]             ⋮              │
└────────────────────────────────────────────┘
```

Statuses:

```text
Processing
Analysis Complete
Needs Attention
Failed
Archived
```

---

# 25. Documents Page

Purpose:

Provide a complete document library.

Layout:

```text
Documents

[ Search documents... ]   [ Filter ] [ Sort ]

[ + Upload Document ]

────────────────────────────────────────────

All Documents

Document
Type
Status
Last Updated
Actions
```

Filters:

```text
Document type
Status
Date
Recently viewed
Needs attention
```

---

# 26. Upload Document Page

This is one of the most important UX flows.

## Upload Area

```text
┌──────────────────────────────────────────────┐
│                                              │
│                  ↑                           │
│             Upload Document                  │
│                                              │
│ Drag & drop your file here                   │
│ or                                           │
│ [ Browse Files ]                             │
│                                              │
│ PDF • DOCX • JPG • PNG                       │
│                                              │
└──────────────────────────────────────────────┘
```

Do not require users to understand technical file requirements.

---

# 27. Upload Validation

Before upload:

```text
✓ File type supported
✓ File size supported
✓ File readable
```

Error:

```text
We couldn't upload this file.

Please upload a supported PDF, DOCX, JPG, or PNG file.
```

Never expose internal stack traces.

---

# 28. Processing Screen

After upload:

```text
Analyzing your document

✓ Document uploaded
✓ Text extracted
● Identifying important sections
○ Preparing document analysis
○ Building your review
```

Progress should communicate stages rather than fake percentage accuracy.

Do not display:

```text
AI is 73% done
```

unless the percentage is actually meaningful.

---

# 29. Document Overview

After processing:

```text
Employment Agreement

Employment Contract

Analysis completed
12 September 2026

[ Review Document ] [ Ask NyayaLens ] [ Compare ]
```

Summary cards:

```text
PARTIES
Employee + Employer

DOCUMENT TYPE
Employment Agreement

IMPORTANT DATES
Joining: 01 Oct 2026

COMPENSATION
₹8,00,000/year

ATTENTION AREAS
3
```

---

# 30. Document Workspace

The main document interface uses tabs.

```text
Overview
Summary
Clauses
Attention
Ask
Compare
Actions
```

The current tab must be clearly visible.

---

# 31. Summary Screen

Structure:

```text
Executive Summary

What this document is about

[ AI-generated summary ]

────────────────────────

Key Details

Parties
Dates
Money
Responsibilities
Termination
Confidentiality

────────────────────────

Important Things to Review

1. Termination notice
2. Non-compete clause
3. Confidentiality period
```

---

# 32. Plain-Language Explanation

Every complex clause should support:

```text
Legal text
↓
Plain-language explanation
↓
Why it matters
```

Example:

```text
TERMINATION

Legal language

"The employee may terminate this agreement
by providing ninety days written notice..."

Plain language

You may need to give your employer 90 days'
notice before leaving.

Why this matters

This could affect how quickly you can leave
the organization.
```

---

# 33. Clause Explorer

Layout:

```text
Clause Explorer

Search clauses...

Categories:

All
Termination
Payment
Confidentiality
Responsibilities
Dispute Resolution
Other
```

Clause card:

```text
┌─────────────────────────────────────────────┐
│ Termination                 § 8 • Page 6   │
│                                             │
│ 90-day notice period                        │
│                                             │
│ Plain language                              │
│ You may need to provide 90 days' notice.   │
│                                             │
│ [ View Original ] [ Explain ]              │
└─────────────────────────────────────────────┘
```

---

# 34. Attention Analysis

Do not call this a definitive:

```text
Legal Risk Score
```

Instead use:

```text
Review Attention
```

or:

```text
Areas to Review
```

---

# 35. Attention Categories

```text
HIGH ATTENTION
MEDIUM ATTENTION
FOR REVIEW
INFORMATIONAL
```

Each item must explain **why** it was highlighted.

Example:

```text
HIGH ATTENTION

Termination Clause

The notice period is 90 days.

Why this was highlighted:
This creates a significant obligation before
termination.

Source:
Section 8 • Page 6
```

---

# 36. Attention Disclaimer

Near the analysis:

```text
These observations are AI-generated and are
intended to help you review the document.
They are not a legal determination or legal advice.
Consider consulting a qualified professional
for important decisions.
```

---

# 37. AI Q&A Screen

This should NOT look like a generic ChatGPT clone.

Instead:

```text
Ask about this document

Your questions will be answered using the
document's available content.

┌────────────────────────────────────────────┐
│ What happens if I leave the company?       │
└────────────────────────────────────────────┘

Suggested questions:

• What is my notice period?
• What are my payment obligations?
• Can the agreement be terminated early?
• What happens after termination?
```

---

# 38. AI Answer

```text
NyayaLens

Based on Section 8 of the agreement, you
are required to provide 90 days' written
notice before termination.

The agreement does not appear to describe
an alternative shorter notice period in
this section.

Sources:

§ 8 — Termination
Page 6
```

---

# 39. Citation Design

Citations are mandatory for document-grounded answers.

Example:

```text
Source
────────────────
§ 8
Termination
Page 6

[ View in Document ]
```

Clicking the citation should open the relevant document section.

Never display a citation that the system cannot verify.

---

# 40. AI Answer States

## Loading

```text
Reviewing the relevant sections...
```

## Answer

Normal answer with sources.

## No Evidence

```text
I couldn't find enough information in this
document to answer that confidently.

You may want to:
[ Ask a broader question ]
[ Prepare this question for a professional ]
```

## Error

```text
We couldn't generate an answer right now.

[ Try Again ]
```

---

# 41. Document Comparison

Purpose:

Help users understand changes between two versions.

Screen:

```text
Compare Documents

Document A
[ Employment Agreement v1 ]

Document B
[ Employment Agreement v2 ]

[ Compare Documents ]
```

---

# 42. Comparison Results

Top summary:

```text
Comparison Complete

12 changes found

3 important changes
5 wording changes
4 formatting changes
```

Then:

```text
TERMINATION

Previous
30 days

New
90 days

Changed

Why it matters:
The required notice period increased
from 30 to 90 days.
```

---

# 43. Comparison Categories

```text
Added
Removed
Changed
Unchanged
```

Use icons + labels.

Do not rely exclusively on red/green colors.

---

# 44. Side-by-Side Comparison

Desktop:

```text
┌──────────────────────────┬──────────────────────────┐
│ VERSION 1                │ VERSION 2                │
├──────────────────────────┼──────────────────────────┤
│ 30 days notice           │ 90 days notice           │
│                          │                          │
│ Confidentiality: 2 yrs   │ Confidentiality: 3 yrs   │
└──────────────────────────┴──────────────────────────┘
```

Mobile:

Use stacked comparison:

```text
Previous
↓

New
↓

What changed?
```

---

# 45. Action Center

Purpose:

Convert document understanding into practical next steps.

```text
Action Center

Based on your document

☐ Confirm termination notice
☐ Review confidentiality clause
☐ Check payment schedule
☐ Ask professional about dispute clause
☐ Save a copy of the final agreement
```

---

# 46. Questions for Professional

NyayaLens can generate questions users may discuss with a qualified legal professional.

Example:

```text
Questions to Discuss

1. Is the 90-day termination period typical
   for this type of agreement?

2. What circumstances could allow an earlier
   termination?

3. What obligations continue after termination?

[ Copy Questions ]
[ Export ]
```

---

# 47. Export Report

Allow users to generate a review report.

Report contents:

```text
NyayaLens Document Review

Document name
Document type
Date analyzed

Executive Summary

Key Details

Important Clauses

Areas to Review

Questions for Professional

AI / Privacy Disclaimer
```

The report should clearly distinguish:

```text
Document evidence
```

from:

```text
AI-generated interpretation
```

---

# 48. Privacy Screen

Privacy should be easy to understand.

Sections:

```text
Your Documents
How AI Processing Works
Data Retention
Deletion
Third-Party AI Services
Security
```

Example:

```text
Your documents belong to you.

We explain what happens to your document,
where it is stored, and how AI processing
is used.
```

Avoid vague statements such as:

```text
Your data is completely safe.
```

---

# 49. Security UI

Security indicators:

```text
🔒 Secure upload
🛡 Private documents
🔐 Protected account
```

But only display these claims if technically implemented.

---

# 50. Responsible AI Notice

Global notice:

```text
NyayaLens provides AI-assisted information
and document analysis. It does not provide
legal representation or replace a qualified
legal professional.
```

For high-stakes interactions:

```text
Important:

AI-generated information can be incomplete
or incorrect. Verify important matters
against the original document and consider
professional legal advice.
```

---

# 51. Empty States

## No Documents

```text
No documents yet

Upload your first document to begin reviewing.

[ Upload Document ]
```

## No Search Results

```text
No documents found

Try another search term or remove a filter.
```

## No Attention Areas

```text
No specific areas were flagged for review.

This does not mean the document is legally
safe or error-free.
```

---

# 52. Error States

Errors must be human-readable.

Bad:

```text
HTTP 500
```

Good:

```text
Something went wrong while analyzing this document.

Your document has not been deleted.

[ Try Again ]
[ Contact Support ]
```

---

# 53. Loading States

Use skeleton loaders for:

* Dashboard
* Document list
* Summary
* Clause cards

For AI processing use meaningful status messages:

```text
Reading document
Finding sections
Identifying important information
Preparing review
```

---

# 54. Modal System

Use modals for:

```text
Delete document
Confirm deletion
Export report
Rename document
Important warnings
```

Do not use modals for ordinary navigation.

---

# 55. Delete Document Flow

User selects:

```text
Delete Document
```

Modal:

```text
Delete "Employment Agreement"?

This will permanently remove the document
and its associated analysis.

This action cannot be undone.

[ Cancel ] [ Delete Document ]
```

Destructive action must be visually distinct.

---

# 56. Search

Global search:

```text
Search documents, clauses...
```

Results may include:

```text
Documents
Clauses
Questions
```

Search should never expose documents the authenticated user is not authorized to access.

---

# 57. Accessibility

NyayaLens must be accessible by default.

## Requirements

* Keyboard navigation
* Visible focus states
* Semantic HTML/web accessibility equivalents
* Screen-reader labels
* Accessible form labels
* Sufficient contrast
* Resizable text
* No color-only information
* Large click targets
* Logical tab order
* Accessible modals
* Accessible error messages

Target:

```text
WCAG 2.2 AA
```

where practical.

---

# 58. Keyboard Navigation

Expected flow:

```text
Tab
→ navigation
→ main CTA
→ form
→ document content
→ actions
```

Every interactive element must be keyboard accessible.

---

# 59. Responsive Design

## Desktop

Use:

```text
Sidebar + Content
```

## Tablet

Use:

```text
Collapsed Sidebar + Content
```

## Mobile Web

Use:

```text
Top Header
↓
Content
↓
Bottom Navigation / Drawer
```

---

# 60. Mobile Document Review

Do not attempt to display an unreadable desktop table.

Instead:

```text
Document
↓
Summary
↓
Important Clauses
↓
Attention Areas
↓
Ask
↓
Actions
```

Comparison should use expandable sections.

---

# 61. Document Viewer

The document viewer should support:

```text
Page navigation
Search
Zoom
Highlighted sections
Citation jumping
```

Example:

```text
Page 6

──────────────

8. TERMINATION

The employee may terminate...

[ AI Highlight ]

90 days' written notice
```

---

# 62. AI Highlight Interaction

When the user clicks an AI-highlighted section:

```text
┌──────────────────────────────────────┐
│ Why is this highlighted?             │
│                                      │
│ This clause describes a 90-day       │
│ termination notice requirement.      │
│                                      │
│ [ Explain More ]                     │
└──────────────────────────────────────┘
```

---

# 63. Onboarding

First-time user:

```text
Welcome to NyayaLens

You can use NyayaLens to:

✓ Understand documents
✓ Review important clauses
✓ Ask questions
✓ Compare versions
✓ Prepare next steps

[ Upload My First Document ]
```

Do not force a long onboarding questionnaire.

---

# 64. Tooltips

Use tooltips for legal/technical concepts.

Example:

```text
RAG
ⓘ
```

Tooltip:

```text
NyayaLens retrieves relevant parts of your
document before generating an answer.
```

However, user-facing terminology should preferably be:

```text
Document-grounded answers
```

rather than:

```text
RAG
```

---

# 65. AI Transparency

Whenever AI produces content, indicate it clearly.

Example:

```text
AI-generated explanation
```

Do not make AI-generated content appear indistinguishable from verified legal facts.

---

# 66. Confidence / Uncertainty

Avoid fake numerical confidence scores.

Do not show:

```text
AI Confidence: 97%
```

unless the underlying system has a validated meaning for that score.

Prefer:

```text
Based on the available document evidence
```

or:

```text
Not enough evidence found
```

---

# 67. Important Information Hierarchy

The interface should prioritize:

```text
1. What is this document?
2. What does it require from me?
3. What should I review?
4. What changed?
5. What can I ask?
6. What should I do next?
```

---

# 68. Dashboard Information Hierarchy

Priority:

```text
Upload Document
      ↓
Recent Documents
      ↓
Needs Attention
      ↓
Pending Actions
      ↓
Document Statistics
```

Do not make analytics the main focus.

---

# 69. UX Safety Rules

NyayaLens must never:

```text
Claim to be a lawyer
Guarantee a legal outcome
Declare a contract legally valid
Declare a contract legally invalid
Guarantee court results
Tell users to ignore professional advice
Fabricate citations
Present unsupported legal claims as facts
```

Instead:

```text
Explain
Highlight
Ask
Compare
Prepare
Escalate
```

---

# 70. Prompt Injection UX Protection

Documents are untrusted input.

If uploaded text contains instructions such as:

```text
Ignore previous instructions...
```

NyayaLens should treat that text as document content, not as system instructions.

The UI does not need to expose technical details, but if relevant:

```text
Some document content may contain instructions
that are unrelated to your question. NyayaLens
treats document text as information, not commands.
```

---

# 71. Notification System

Notifications may include:

```text
Document analysis completed
Comparison completed
Report ready
Processing failed
```

Notification example:

```text
✓ Employment Agreement analysis is ready.
[ Open Review ]
```

Do not use notifications for unnecessary marketing.

---

# 72. Profile Menu

```text
Profile
Account Settings
Privacy
Help
Sign Out
```

---

# 73. Settings

Sections:

```text
Account
Preferences
Notifications
Privacy
Security
AI Preferences
```

AI preferences may include:

```text
Show AI explanations
Show detailed citations
```

Avoid settings that imply users can disable safety mechanisms.

---

# 74. Footer

Public website footer:

```text
NyayaLens

Understand. Review. Act.

Product
Features
How It Works
Security

Company
About
Contact

Legal
Privacy Policy
Terms
Responsible AI

© 2026 NyayaLens
```

---

# 75. Visual Style

## Recommended

```text
Minimal
Professional
Calm
Clean
Trustworthy
Modern
Human-centered
```

## Avoid

```text
Neon gradients
Cyberpunk
Excessive glassmorphism
3D legal scales everywhere
Stock lawyer imagery
AI robot imagery
Excessive animation
```

---

# 76. Animation

Animations should be subtle.

Allowed:

```text
Fade
Slide
Skeleton loading
Button feedback
Accordion expansion
Tab transition
```

Duration:

```text
150–250ms
```

Avoid:

```text
Long page transitions
Continuous motion
Decorative animations
```

Provide reduced-motion support where possible.

---

# 77. Design Tokens

Frontend should centralize all design values.

Example:

```text
Tailwind theme configuration / CSS variables

primary
background
surface
textPrimary
textSecondary
border
success
warning
attention
info
```

Spacing:

```text
xs
sm
md
lg
xl
xxl
```

Typography:

```text
display
h1
h2
h3
body
small
caption
```

Do not hardcode design values repeatedly across screens.

---

# 78. Recommended Component Architecture

```text
components/
│
├── buttons/
├── forms/
├── navigation/
├── cards/
├── documents/
├── clauses/
├── ai/
├── comparison/
├── actions/
├── feedback/
└── layout/
```

---

# 79. Recommended Frontend Pages

```text
pages/
│
├── LandingPage
├── LoginPage
├── SignupPage
├── DashboardPage
├── DocumentsPage
├── UploadPage
├── DocumentOverviewPage
├── SummaryPage
├── ClauseExplorerPage
├── AttentionPage
├── AskPage
├── ComparePage
├── ActionCenterPage
├── ReportPage
├── SettingsPage
└── PrivacyPage
```

---

# 80. Primary User Journey

## Scenario

User receives a new employment agreement.

### Step 1

Visits:

```text
nyayalens.com
```

### Step 2

Clicks:

```text
Get Started
```

### Step 3

Creates account.

### Step 4

Dashboard opens.

### Step 5

Clicks:

```text
Upload Document
```

### Step 6

Uploads:

```text
Employment_Agreement.pdf
```

### Step 7

NyayaLens processes document.

### Step 8

User sees:

```text
Summary
Key Clauses
Attention Areas
```

### Step 9

User asks:

```text
What happens if I leave the company?
```

### Step 10

NyayaLens provides:

```text
Answer
+
Section
+
Page
+
Original evidence
```

### Step 11

User uploads second version.

### Step 12

User compares:

```text
Version 1
vs
Version 2
```

### Step 13

NyayaLens identifies:

```text
30 days → 90 days
```

### Step 14

User opens:

```text
Action Center
```

### Step 15

Generates:

```text
Questions to discuss with a legal professional
```

This is the primary demo flow.

---

# 81. MVP Screen Priority

## P0 — Must Have

```text
Landing
Login
Dashboard
Upload
Processing
Document Overview
Summary
Clause Explorer
Attention Analysis
Ask
Comparison
Action Center
```

## P1 — Should Have

```text
Documents Library
Document Viewer
Export Report
Privacy
Settings
```

## P2 — Future

```text
Multilingual UI
Voice interaction
Collaborative review
Professional workspace
Advanced analytics
Team accounts
```

---

# 82. MVP Navigation

The first development version should expose only:

```text
Dashboard
Documents
Compare
Ask
Actions
Settings
```

Document-specific tabs:

```text
Overview
Summary
Clauses
Attention
Ask
Compare
Actions
```

This keeps navigation understandable.

---

# 83. Frontend State Requirements

Every major page must support:

```text
Loading
Success
Empty
Error
Unauthorized
Not Found
```

AI pages additionally:

```text
Generating
Evidence Found
Insufficient Evidence
Generation Error
```

---

# 84. Authentication States

```text
Unauthenticated
Authenticated
Session Expired
Unauthorized
```

If the session expires:

```text
Your session has expired.

Please sign in again to continue.

[ Sign In ]
```

---

# 85. Document Security UX

Users must never see:

```text
Public document URL
Storage credentials
Internal document IDs unnecessarily
Backend error details
AI API credentials
```

Document access must be enforced server-side.

---

# 86. Responsive Width Rules

Desktop:

```text
Page max-width: 1440px
Content max-width: 1280px
```

Tablet:

```text
Page padding: 24px
```

Mobile:

```text
Page padding: 16px
```

Cards should generally be full-width on mobile.

---

# 87. Desktop Grid

Recommended:

```text
12-column grid
```

Example:

```text
Sidebar: 2 columns
Main: 10 columns
```

Dashboard:

```text
4 statistic cards
↓
8-column recent documents
4-column attention/action panel
```

---

# 88. Mobile Grid

Use:

```text
1-column layout
```

Cards stack vertically.

Never force horizontal scrolling for important information.

---

# 89. Accessibility Copy Rules

Prefer:

```text
Review document
```

over:

```text
Analyze
```

when the action is intended for general users.

Prefer:

```text
Areas to review
```

over:

```text
Risk engine
```

Prefer:

```text
Ask about this document
```

over:

```text
RAG Chat
```

---

# 90. Microcopy Rules

Tone:

```text
Clear
Calm
Helpful
Non-judgmental
Professional
```

Example:

Bad:

```text
Your contract has dangerous clauses!
```

Better:

```text
3 areas may deserve closer review.
```

Bad:

```text
This contract is unsafe.
```

Better:

```text
This clause may create an important obligation.
```

---

# 91. AI Failure UX

If the model cannot answer:

```text
I couldn't find enough information in the
document to answer this confidently.

Try asking about a specific clause or section.
```

Actions:

```text
[ Try Again ]
[ View Document ]
[ Add to Questions ]
```

---

# 92. Citation Failure UX

If evidence cannot be verified:

```text
This answer could not be linked to a specific
section of the document, so NyayaLens is not
presenting it as document evidence.
```

This is preferable to fabricating a citation.

---

# 93. Accessibility Checklist

Before release:

```text
☐ Keyboard navigation works
☐ Focus states visible
☐ All inputs labelled
☐ Buttons have accessible names
☐ Images have meaningful alt text
☐ Color is not the only indicator
☐ Contrast checked
☐ Text can scale
☐ Modals keyboard accessible
☐ Error messages announced
☐ Tables have appropriate headers
☐ Reduced motion considered
☐ Mobile navigation accessible
```

---

# 94. UI Quality Checklist

Before every release:

```text
☐ No overflowing text
☐ No broken layouts
☐ No horizontal scrolling on mobile
☐ Loading states implemented
☐ Empty states implemented
☐ Error states implemented
☐ Buttons have correct states
☐ Forms validate correctly
☐ Navigation works
☐ Back navigation works
☐ Refresh does not break authenticated state
☐ Unauthorized documents cannot be opened
```

---

# 95. Hackathon Evaluation Alignment

NyayaLens UI/UX directly addresses the challenge evaluation areas.

## Security — High Impact

UI communicates:

```text
Privacy
Secure upload
Document ownership
Responsible AI
```

Backend must enforce the actual security.

## Accessibility — High Impact

UI includes:

```text
Keyboard navigation
Accessible controls
Readable typography
Responsive design
Color-independent states
```

## Problem Alignment — High Impact

The interface directly supports:

```text
Understand
Review
Compare
Ask
Act
```

## Code Quality — Medium Impact

Reusable:

```text
Design tokens
Components
Layouts
State patterns
```

## Efficiency — Low Impact

UX supports:

```text
Progressive loading
Async processing
Focused document retrieval
Caching
```

## Testing — Low Impact

Every major screen has defined:

```text
Loading
Success
Empty
Error
Unauthorized
```

---

# 96. Final Website Information Architecture

```text
NYAYALENS
│
├── PUBLIC
│   ├── Home
│   ├── Features
│   ├── How It Works
│   ├── Security
│   ├── About
│   ├── Login
│   └── Signup
│
└── APP
    │
    ├── Dashboard
    │
    ├── Documents
    │   ├── All Documents
    │   ├── Upload
    │   └── Document
    │       ├── Overview
    │       ├── Summary
    │       ├── Clauses
    │       ├── Attention
    │       ├── Ask
    │       └── Actions
    │
    ├── Compare
    │
    ├── Ask
    │
    ├── Action Center
    │
    ├── Settings
    │
    └── Privacy
```

---

# 97. Final Design Direction

NyayaLens should look like:

```text
Professional legal-tech SaaS
        +
Modern AI product
        +
Simple document workspace
```

Not:

```text
Generic chatbot
        or
AI experiment
        or
Traditional legal website
```

The visual experience should make the user feel:

> "I can understand what's in this document, see where the information came from, and know what I should review next."

---

# 98. Definition of Done — UI/UX

The UI/UX implementation is complete when:

```text
☐ Public landing page complete
☐ Authentication screens complete
☐ Responsive application shell complete
☐ Dashboard complete
☐ Document upload complete
☐ Processing state complete
☐ Document overview complete
☐ Summary complete
☐ Clause Explorer complete
☐ Attention Analysis complete
☐ AI Q&A complete
☐ Citation UI complete
☐ Comparison complete
☐ Action Center complete
☐ Report/export UI complete
☐ Privacy UI complete
☐ Settings complete
☐ Loading states complete
☐ Empty states complete
☐ Error states complete
☐ Mobile responsive
☐ Tablet responsive
☐ Keyboard accessible
☐ Consistent design tokens
☐ No hardcoded secrets
☐ No fake AI confidence scores
☐ Responsible AI messaging implemented
```

---

# 99. Implementation Rule

This document is the **UI/UX source of truth** for NyayaLens.

During development:

1. Build reusable components first.
2. Implement the design tokens.
3. Build the application shell.
4. Build screens according to the P0 priority.
5. Implement all loading/error/empty states.
6. Connect real backend functionality.
7. Test desktop.
8. Test tablet.
9. Test mobile web.
10. Perform accessibility review.
11. Perform security review.
12. Only then polish animations and visual details.

**Do not sacrifice security, accessibility, or document-grounded accuracy for visual effects.**

---

# 100. Product Experience Statement

NyayaLens is not designed to tell users:

> "Here is your legal answer."

It is designed to help users understand:

> **"Here is what your document says, here is where it says it, here is why this part may deserve attention, and here are useful questions to consider next."**

**NyayaLens — Understand. Review. Act.**
