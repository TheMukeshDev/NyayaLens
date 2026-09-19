# NyayaLens — Design System

**Product:** NyayaLens
**Tagline:** Understand. Review. Act.

---

# 1. Design Principles

The visual system should communicate:

```text
Trust
Clarity
Control
Evidence
Professionalism
Accessibility
```

Avoid:

* Excessive gradients
* Cyberpunk aesthetics
* Overuse of animations
* Excessive glassmorphism
* AI gimmicks
* Decorative elements that compete with document content

---

# 2. Color System

## Primary

```text
Deep Navy
#0F172A
```

Used for:

* Navigation
* Headings
* Primary brand elements

## Primary Action

```text
Blue
#2563EB
```

Used for:

* Buttons
* Links
* Active states

## Background

```text
#F8FAFC
```

## Surface

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

Color must never be the only indicator of state.

---

# 3. Typography

Primary font:

```text
Inter
```

Fallback:

```text
system-ui, sans-serif
```

### H1

```text
36–44px
Weight: 700
```

### H2

```text
28–32px
Weight: 700
```

### H3

```text
20–24px
Weight: 600
```

### Body

```text
16px
Line-height: 1.5
```

### Secondary

```text
14px
```

---

# 4. Spacing

Use an 8-point spacing system.

```text
8px
16px
24px
32px
40px
48px
64px
```

Avoid arbitrary spacing values unless necessary.

---

# 5. Border Radius

Recommended:

```text
Small:
6px

Medium:
8px

Large:
12px

Cards:
12px
```

Use consistent rounding throughout the product.

---

# 6. Shadows

Use subtle shadows.

Avoid heavy floating-card effects.

Preferred hierarchy:

```text
No shadow
Subtle shadow
Elevated modal shadow
```

---

# 7. Buttons

## Primary

```text
Background: #2563EB
Text: White
```

Example:

```text
Upload Document
```

## Secondary

Outlined or neutral surface.

Example:

```text
Compare Documents
```

## Destructive

Used only for destructive actions.

Example:

```text
Delete Document
```

---

# 8. Button Sizes

### Small

```text
Height: 32px
```

### Medium

```text
Height: 40px
```

### Large

```text
Height: 48px
```

Interactive controls should provide comfortable touch targets.

---

# 9. Form Controls

Inputs should have:

* Visible label
* Clear focus state
* Error message
* Helpful placeholder only where appropriate
* Accessible description when needed

Never use placeholder text as the only label.

---

# 10. Cards

Cards should communicate grouped information.

Examples:

```text
Document Card
Attention Card
Action Card
Comparison Card
```

Card hierarchy:

```text
Title
Supporting information
Primary content
Action
```

---

# 11. Status System

Use text + icon + optional color.

Example:

```text
✓ READY
● PROCESSING
! HIGH ATTENTION
× FAILED
```

Never use color alone.

---

# 12. Attention Levels

### Low

```text
LOW ATTENTION
```

### Medium

```text
MEDIUM ATTENTION
```

### High

```text
HIGH ATTENTION
```

These indicate areas worth reviewing—not definitive legal risk scores.

---

# 13. Citation Design

Citation should be visually distinct.

Example:

```text
The notice period is 90 days. [1]
```

Clicking `[1]` opens:

```text
Source

Section 8 — Termination
Page 6

Original text:
...
```

Citation UI must make source verification easy.

---

# 14. AI Answer Design

AI answers should visually distinguish:

```text
DOCUMENT-GROUNDED
```

from:

```text
GENERAL INFORMATION
```

and:

```text
INSUFFICIENT EVIDENCE
```

This is a trust feature, not merely a visual feature.

---

# 15. Document Viewer

The document viewer should support:

* Page navigation
* Zoom
* Search
* Source highlighting where technically possible
* Citation navigation

When a citation is selected:

```text
Citation
 ↓
Relevant page
 ↓
Relevant section/clause
```

---

# 16. Icons

Use:

```text
Lucide
```

Icons should support meaning rather than decorate every element.

Examples:

```text
Upload
FileText
Search
AlertTriangle
CheckCircle
MessageSquare
GitCompare
ListChecks
Shield
Settings
```

---

# 17. Navigation

Desktop:

```text
Sidebar
```

Mobile:

```text
Header + Drawer
```

Active navigation should have:

* Visual indicator
* Accessible state
* Text label

---

# 18. Tables

Tables should be used for structured comparison.

Example:

| Term   | Version 1 | Version 2 | Change   |
| ------ | --------- | --------- | -------- |
| Notice | 30 days   | 90 days   | Modified |

On mobile, convert dense tables into cards when necessary.

---

# 19. Alerts

Types:

```text
Info
Success
Warning
Error
```

Every alert should have a clear message and, where applicable, an action.

---

# 20. Loading

Use:

* Skeletons for content
* Spinners for short actions
* Progress indicators for document processing

Do not show indefinite spinners without explanation.

---

# 21. Animation

Animations should be subtle and functional.

Allowed:

* Button feedback
* Page transitions
* Expand/collapse
* Progress updates

Avoid:

* Excessive motion
* Decorative particle effects
* Continuous animations

Respect reduced-motion preferences.

---

# 22. Accessibility

Target:

```text
WCAG 2.2 AA-oriented implementation
```

Requirements include:

* Keyboard accessibility
* Focus visibility
* Semantic HTML
* Accessible forms
* Contrast
* Screen-reader support
* Reduced motion
* Error identification
* Logical reading order

---

# 23. Responsive Breakpoints

Recommended Tailwind-oriented breakpoints:

```text
sm: 640px
md: 768px
lg: 1024px
xl: 1280px
2xl: 1536px
```

Design mobile-first where practical.

---

# 24. Layout

Maximum content width:

```text
1200–1280px
```

Use generous whitespace around document content.

Typical page:

```text
┌────────────────────────────────────┐
│ Header                             │
├────────────┬───────────────────────┤
│ Sidebar    │ Main Content          │
│            │                       │
│            │                       │
└────────────┴───────────────────────┘
```

---

# 25. Brand Voice

NyayaLens copy should be:

### Clear

Avoid unnecessary legal jargon.

### Calm

Do not create fear.

### Honest

Clearly communicate limitations.

### Action-oriented

Tell users what they can do next.

### Responsible

Never imply guaranteed legal outcomes.

---

# 26. Example Copy

Instead of:

```text
AI Legal Risk Score: 91%
```

Use:

```text
HIGH ATTENTION

The termination clause specifies a 90-day notice period.
Review this section carefully before making a decision.
```

Instead of:

```text
AI Lawyer
```

Use:

```text
AI Document Assistant
```

Instead of:

```text
You're legally safe.
```

Use:

```text
No obvious issue was identified by this automated review.
For important decisions, consider professional legal review.
```

---

# 27. Design System Component Architecture

```text
components/
├── ui/
│   ├── Button
│   ├── Input
│   ├── Card
│   ├── Badge
│   ├── Dialog
│   ├── Tabs
│   └── Alert
│
├── documents/
│   ├── DocumentCard
│   ├── DocumentViewer
│   ├── UploadZone
│   └── ProcessingStepper
│
├── analysis/
│   ├── SummaryCard
│   ├── ClauseCard
│   ├── AttentionCard
│   └── CitationPanel
│
├── chat/
│   ├── ChatWindow
│   ├── UserMessage
│   ├── AIAnswer
│   └── SourceCitation
│
├── comparison/
│   ├── DocumentSelector
│   ├── ComparisonSummary
│   └── ChangeCard
│
└── actions/
    ├── ActionCard
    ├── ActionList
    └── ActionStatus
```

---

# 28. Final Design Rule

Every major NyayaLens interface should answer:

```text
What am I looking at?
What matters?
Why does it matter?
Where did this information come from?
What can I do next?
```

If the interface answers those five questions clearly, the product will feel trustworthy and useful rather than like a generic AI wrapper.
