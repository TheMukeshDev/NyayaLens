# End-to-end tests (Playwright)

The E2E suite drives the **real Next.js UI** through the full journey —
signup → login → upload → processing → overview → summary → Q&A → comparison →
action center → report — against two hermetic test doubles, so it needs no live
Supabase project, database, or AI keys.

```
npm run test:e2e                 # run everything
npx playwright test --headed     # watch it happen
npx playwright test --grep "journey" --debug
```

First run only:

```
npx playwright install chromium chromium-headless-shell
```

## How it works

`playwright.config.ts` starts two servers before the tests:

1. **`mock-server.mjs`** (port `4010`) — a single HTTP server that answers both
   `@supabase/ssr`'s auth calls (`/auth/v1/*`) and the FastAPI backend
   (`/api/v1/*`).
2. **The Next.js dev server** (port `3100`), started with
   `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_API_URL` pointed at the mock and
   `NEXT_DIST_DIR=.next-e2e` so it can coexist with a dev server you already have
   open (Next 16 permits only one `next dev` per project directory).

Because auth gating (`proxy.ts`) and the dashboard/document pages fetch
**server-side**, stubbing only the browser is not enough — that is why the mock
is a real server rather than a `page.route` interception.

## The seeded test user

`mock-server.mjs` seeds one account before the app starts:

| | |
|---|---|
| email | `e2e.user@example.com` |
| password | `e2e-password-123` |

`fixtures.ts` holds the same values as `TEST_USER`; keep the two in sync. No real
account is ever created — signup in the journey uses a throwaway address and the
mock never leaves the process. The mock also seeds one `READY` document
(`SEEDED_DOCUMENT_ID`) so the comparison step always has two documents to compare.

## Writing tests

- Import `test`/`expect` from `@playwright/test` and helpers from `./fixtures`.
- Call `waitForHydrated(page)` after a `page.goto(...)` before interacting with a
  client component. `domcontentloaded` can fire before React attaches handlers,
  and events dispatched too early are silently lost (e.g. choosing a file never
  enables the upload button).
- Use `{ waitUntil: "domcontentloaded" }` on `page.goto` — the dev server keeps
  long-lived connections open, so the `load` event can be deferred.
- Load the app through `localhost`, never `127.0.0.1` (see `.freebuff/run.md`).

## Adding behaviour to the mock

Add the route to `mock-server.mjs` and keep the response shape matching
`src/lib/types.ts`. Everything the mock returns should be shaped like the real
backend envelope: `{ success: true, data, message }`, and errors as
`{ success: false, error: { code, message, details } }`.
