# NyayaLens — Accessibility Audit

**Date:** 2026-09-19
**Scope:** Accessibility review of the NyayaLens frontend (`frontend/`) as it exists in the working tree.
**Target:** WCAG 2.1 Level AA (with selected 2.2 AA and best-practice checks).

**Method:** Source inspection of every page/component plus automated testing:

- `cd frontend && npm run lint` → **clean (0 errors, 0 warnings)**
- `cd frontend && npm run build` → **success** (TypeScript typecheck passed)
- Automated browser scan with `axe-core@4` driven by `puppeteer-core@23` against a production
  build (`next start`), tags `wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa, best-practice`
- Keyboard/structure smoke test (real Chrome): skip link on focus, mobile menu
  `aria-expanded`, and one-`h1`-per-page assertions
- Manual contrast computation for every foreground/background token pairing used in the UI

> **Honesty rule applied throughout:** a criterion is `PASS` only when it was verified by a
> running tool (axe / the smoke test / a computed contrast ratio) **or** is a pure-static
> property of the source (for example "every icon-only button has `aria-label`"). Anything that
> requires an authenticated session, a screen reader, or visual/manual judgement is marked
> `NOT TESTED`, never `PASS`.

---

## 1. Results summary

| # | Area | Status |
|---|------|--------|
| 1 | Automated axe scan — public pages (9 routes/states) | **PASS** (0 violations, 0 incomplete) |
| 2 | Automated axe scan — authenticated pages | **NOT TESTED** (auth-gated; no Supabase session available) |
| 3 | Document `lang` and per-page titles | **PASS** |
| 4 | Heading hierarchy (no skipped levels, one `h1`/page) | **PASS** (runtime public) / **PASS by source review** (authed) |
| 5 | Bypass blocks / skip link | **PASS** (runtime public) / **PASS by source review** (app shell) |
| 6 | Visible keyboard focus indicator | **PASS by source review** |
| 7 | Keyboard focus order & modal focus management | **PASS by source review** / **NOT TESTED at runtime** (authed drawer/dialog) |
| 8 | Text color contrast | **PASS** (axe public + computed authed pairings) |
| 9 | Non-text contrast (icons, focus ring, borders) | **PASS by source review + computed ratios** |
| 10 | Use of color (never the sole indicator) | **PASS by source review** |
| 11 | Forms: labels, descriptions, error association | **PASS by source review** / **NOT TESTED at runtime** |
| 12 | Non-text content accessible names (icon-only controls) | **PASS by source review** |
| 13 | Images / alt text | **PASS** (no `<img>`/`<Image>`/inline SVG media in the app) |
| 14 | Status messages / live regions | **PASS by source review** / **NOT TESTED with a screen reader** |
| 15 | Motion & `prefers-reduced-motion` | **PASS by source review** |
| 16 | Reflow / zoom / text-spacing (1.4.10, 1.4.12) | **NOT TESTED** |
| 17 | Screen-reader walkthrough (NVDA/JAWS/VoiceOver) | **NOT TESTED** |
| 18 | Keyboard-only walkthrough of authenticated flows | **NOT TESTED** |

Verification checklist requested by the task:

| Claim | Result |
|-------|--------|
| Automated accessibility tests were run | **PASS** (§2, §3) |
| All tool-detected violations were fixed | **PASS** — axe reports 0 violations on public pages |
| Color is never the only state indicator | **PASS by source review** (§6.3) |
| Interactive elements are keyboard reachable | **PASS by source review**; runtime keyboard checks on public pages **PASS**; authed **NOT TESTED** (§6.1) |
| Forms are correctly labelled | **PASS by source review**; runtime **NOT TESTED** (§6.4) |
| Full manual/screen-reader audit completed | **NO — NOT TESTED** (§5) |

---

## 2. Tooling

- Harness: `%TEMP%\opencode\a11y\axe-scan.mjs` (axe-core + puppeteer-core, system Chrome).
- Keyboard smoke test: `%TEMP%\opencode\a11y\keyboard-smoke.mjs`.
- Contrast computations: `%TEMP%\opencode\a11y\contrast.mjs`.
- Raw report: `%TEMP%\opencode\a11y\axe-report.json`.
- These live outside the repo so no dependency or script was added to `package.json`.

The project **also** has an in-repo a11y harness that runs in CI: `eslint-config-next`
enables six `jsx-a11y` rules (`alt-text`, `aria-props`, `aria-proptypes`,
`aria-unsupported-elements`, `role-has-required-aria-props`, `role-supports-aria-props`),
and `npm test` runs `frontend/tests/a11y.test.tsx` (8 axe-core tests over shared UI
primitives via `frontend/tests/axe.ts`) — all pass. Axe was used as the primary automated
scanner because it is already present transitively via `axe-core`.

### axe results (final run)

```
/                                    0 violation type(s), 0 incomplete
/features                            0 violation type(s), 0 incomplete
/how-it-works                        0 violation type(s), 0 incomplete
/security                            0 violation type(s), 0 incomplete
/about                               0 violation type(s), 0 incomplete
/privacy                             0 violation type(s), 0 incomplete
/login                               0 violation type(s), 0 incomplete
/signup                              0 violation type(s), 0 incomplete
/login?error=Invalid login credentials  0 violation type(s), 0 incomplete
```

### Keyboard/structure smoke results (final run)

```
PASS  Skip link is first Tab stop and becomes visible on focus
PASS  Skip link target #main-content exists
PASS  Marketing mobile menu toggles aria-expanded and is visible
PASS  Marketing mobile menu closes after navigation
PASS  Exactly one h1 on / , /features , /how-it-works , /security , /about , /privacy , /login , /signup
12/12 checks passed
```

---

## 3. Issues found and fixed

All of the following were **confirmed** by axe, by computed contrast, or by direct source
inspection, then fixed.

### 3.1 Color contrast (WCAG 1.4.3) — FAIL → FIXED

| Location | Before | Ratio | After | Ratio |
|----------|--------|-------|-------|-------|
| `/login` error alert, badges, `ErrorState`, form errors, inline retry/action errors | `#dc2626` on red-50 `#fef2f2` | **4.41 (fail)** | new `--color-danger-strong #b91c1c` | **5.91 (pass)** |
| `danger-outline` button hover/active state | `#dc2626` on red-50 / red-100 | **4.41 / ~3.9 (fail)** | `text-danger-strong` | 5.91 / 5.3 (pass) |
| Upload success panel | `text-success/80`, `/90` on green-50 | **3.37 / 3.99 (fail)** | solid `text-success` | **4.79 (pass)** |
| Input placeholder | `text-muted/60` on white | **2.30 (fail)** | `text-muted` | **4.76 (pass)** |
| Homepage decorative step numbers | `text-slate-100` | **1.10 (fail)** | `text-slate-500` + `aria-hidden` | **4.76 (pass)** |

Files: `app/globals.css`, `components/ui/{badge,alert,error-state,field,button}.tsx`,
`components/actions/actions-board-view.tsx`, `components/documents/{retry-button,document-card}.tsx`,
`components/compare/compare-view.tsx`, `app/(app)/upload/upload-form.tsx`, `app/page.tsx`.

All foreground/background token pairings now in use were computed and pass 4.5:1 (normal text) or
3:1 (large text / non-text): brand on blue-50 **4.75**, success on green-50 **4.79**, warning on
amber-50 **4.84**, muted on canvas **4.55**, navy on blue-50 **16.4**, white on brand/danger **4.83+**.

### 3.2 Links distinguished by more than color (WCAG 1.4.1) — FAIL → FIXED

- `/security` privacy link inside body text was identified only by color (brand blue, `hover:underline`).
  Changed to `font-medium text-brand underline underline-offset-2 hover:no-underline`
  (`app/security/page.tsx`).

### 3.3 Keyboard focus visibility (WCAG 2.4.7) — PASS (existing, verified)

- Global `:focus-visible` outline (`2px solid brand`, offset 2px) applied to links, buttons,
  inputs, selects, textareas, summaries and `[tabindex]` (`app/globals.css`). Native
  `<button>`/`<a>`/`<input>` retained; no focus style is removed anywhere.

### 3.4 Bypass blocks / skip link (WCAG 2.4.1) — FAIL → FIXED

- The marketing layout had no skip link. Added `SkipLink` and `id="main-content"` on its `<main>`
  (`components/marketing/marketing-layout.tsx`). The authenticated `AppShell` already had an
  inline skip link targeting `id="main-content"`.

### 3.5 Heading structure (WCAG 1.3.1 / 2.4.6) — FAIL → FIXED

- `CardTitle` now accepts an `as` prop (`h2 | h3 | h4`, default `h3`) so card titles nested under a
  page `h1` render as `h2` (`components/ui/card.tsx`). Applied in `dashboard`, `overview-view`,
  `summary-view`, `settings`.
- Added the missing page `h1` on `/compare`, `/reports`, `/actions` and `/settings`
  (`app/(app)/{compare,reports,actions,settings}/page.tsx`).
- Added `sr-only` section `h2`s to remove `h1 → h3` skips in `clauses-view`, `attention-view`,
  `ask-view`, `compare-view`, `reports-view`, `actions-board-view`.
- Result: exactly one `h1` per page and no skipped heading levels (axe `heading-order` clean on
  all public pages; source-reviewed on authed pages).

### 3.6 Mobile navigation drawer keyboard behaviour (WCAG 2.1.1 / 2.1.2 / 2.4.3) — FAIL → FIXED (source review)

`components/app-shell.tsx` mobile workspace drawer previously had no dialog semantics or focus
management. Now:

- `role="dialog"`, `aria-modal="true"`, `aria-label="Workspace menu"`, `tabIndex={-1}`.
- Focus moves into the drawer on open; `Tab`/`Shift+Tab` are trapped within it.
- `Escape` closes the drawer; focus is restored to the menu toggle (or the previously focused
  element if still in the DOM).
- Background scroll is locked while open.

### 3.7 Form inputs: labels, help text, errors (WCAG 1.3.1 / 3.3.2 / 4.1.3) — FIXED (source review)

- `Field` now clones its child control to inject `aria-describedby` (linking hint and error text)
  and `aria-invalid` when an error is present (`components/ui/field.tsx`).
- `FormError` uses `role="alert"` with `text-danger-strong`.
- Upload drop-zone now exposes a keyboard focus ring (`focus-within:ring-2 ring-brand`), and the
  file input is linked to its help text via `aria-describedby="document-file-help"` +
  `aria-invalid` (`app/(app)/upload/upload-form.tsx`).

### 3.8 Status messages (WCAG 4.1.3) — FIXED (source review)

- `Alert` renders `role="alert"` for errors and `role="status"` otherwise
  (`components/ui/alert.tsx`).
- `RetryButton` error text now has `role="alert"` (`components/documents/retry-button.tsx`).
- Ask conversation is an ARIA live log: `role="log" aria-live="polite" aria-label="Conversation"`,
  so answers/errors are announced as they arrive (`components/ask/ask-view.tsx`).

### 3.9 Other confirmed-good properties

- **Images:** no `<img>`, `next/image`, or inline SVG media anywhere in `app/` or `components/`
  (logos/marks are text or icon fonts with `aria-hidden`). Alt-text rule trivially passes.
- **`lang`:** `<html lang="en">` set in `app/layout.tsx`.
- **Titles:** all 14 route segments define `metadata.title`; root template `"%s — NyayaLens"`.
- **Use of color:** every status is conveyed by an icon **and** a text label
  (`components/ui/status.tsx`, `badge.tsx`), never by color alone.
- **Icon-only controls:** the menu toggles and dialog close button carry `aria-label`; decorative
  icons are `aria-hidden`.
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` collapses animation/transition
  durations and disables smooth scrolling (`app/globals.css`).

---

## 4. Authenticated pages — source-reviewed, not defect-scanned

`/dashboard`, `/upload`, `/documents/*`, `/settings`, `/compare`, `/reports`, `/actions`, `/ask`
are behind Supabase auth. Without a session they redirect to `/login`, so **axe could not scan
them**. They were reviewed in source and the shared primitives they use (`Button`, `Field`,
`Card`, `Alert`, `Badge`, `Status`, `EmptyState`, `ErrorState`, `Dialog`, `AppShell`) are the same
ones verified above. The specific authenticated-only risks are listed as `NOT TESTED` in §5.

Notably, the shared `Dialog` (`components/ui/dialog.tsx`) already implements a correct modal
pattern: `role="dialog"` + `aria-modal`, `aria-labelledby`/`aria-describedby`, Escape-to-close,
focus trap, initial focus, body scroll lock, and focus restore. It was verified by source review
only (no page currently renders it in a scannable state).

---

## 5. NOT TESTED (and why)

These are explicitly **not** claims of compliance.

1. **Authentication-gated routes under axe** — no Supabase session/backend available.
2. **Runtime keyboard operation of the authed app shell drawer** — implemented and unit-of-source
   reviewed, but not exercised in a browser (login required). Public-page keyboard behaviour *was*
   exercised (§2).
3. **Screen-reader usability** (NVDA, JAWS, VoiceOver, TalkBack) — no screen reader was run;
   live-region and label code was inspected only.
4. **Manual keyboard-only walkthrough** of full authenticated flows (upload → processing → summary
   → ask → actions).
5. **Reflow at 320 px / 400 % zoom (WCAG 1.4.10)** and **text-spacing override (1.4.12)** — not
   measured. Layouts use responsive Tailwind breakpoints and `sm:grid-cols-*`, but this was not
   verified at extreme zoom.
6. **Target size (WCAG 2.5.8, 2.2 AA)** — small controls (e.g. 32 px `h-8` buttons, 20 px
   badges) were not measured against the 24 px minimum with spacing.
7. **Focus-not-obscured (WCAG 2.4.11, 2.2 AA)** — sticky header + skip link interaction not
   measured at runtime.
8. **Hover/focus contrast was computed for red/green/amber/brand pairings, but not every possible
   combination of nested tints** — only ones present in source.
9. **Dark mode / forced-colors (Windows High Contrast)** — the app is single light theme and was
   not tested under forced-colors mode.

---

## 6. Recommendations before claiming full WCAG 2.1 AA

1. Add an authenticated axe scan (seed a test user/session) and run it in CI. *Progress: a hermetic Playwright E2E now drives the authenticated pages against a mock (`frontend/e2e/`), so an axe step can be added there; the Vitest axe suite covers the shared UI primitives (`frontend/tests/a11y.test.tsx`).*
2. Run a scripted Playwright/Puppeteer keyboard walkthrough of the authed flows, including the
   mobile drawer.
3. Perform at least one manual screen-reader pass (NVDA on Windows is the closest to this stack).
4. Measure target sizes and 320 px reflow; adjust the `h-8`/`text-xs` controls if needed.
5. Consider adding `eslint-plugin-jsx-a11y` full recommended config to catch these earlier.

---

## 7. Files changed

- `frontend/app/globals.css` — added `--color-danger-strong`.
- `frontend/components/ui/badge.tsx`, `alert.tsx`, `error-state.tsx`, `field.tsx`, `button.tsx`,
  `card.tsx` — token/contrast, error semantics, `CardTitle as`, form ARIA wiring.
- `frontend/components/app-shell.tsx` — mobile drawer dialog semantics, focus trap, Escape, restore.
- `frontend/components/marketing/marketing-layout.tsx` — skip link + `#main-content`.
- `frontend/components/ask/ask-view.tsx` — live `role="log"`; `sr-only` section heading.
- `frontend/components/analysis/clauses-view.tsx`, `attention-view.tsx`, `summary-view.tsx`,
  `overview-view.tsx` — section headings.
- `frontend/components/actions/actions-board-view.tsx` — inline error contrast + `sr-only` heading.
- `frontend/components/compare/compare-view.tsx` — "Before" label contrast + `sr-only` heading.
- `frontend/components/reports/reports-view.tsx` — `sr-only` heading.
- `frontend/components/documents/retry-button.tsx`, `document-card.tsx` — error contrast + `role="alert"`.
- `frontend/app/(app)/{dashboard,settings,compare,reports,actions}/page.tsx` — page `h1` / `h2` structure.
- `frontend/app/(app)/upload/upload-form.tsx` — focus ring, `aria-describedby`, `aria-invalid`, success contrast.
- `frontend/app/page.tsx`, `app/security/page.tsx` — step-number contrast; non-color-only link.
