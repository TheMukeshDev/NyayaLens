# Run doc — NyayaLens preview

The thing worth previewing in this repo is the **Next.js web app** in `frontend/`.
The FastAPI backend in `backend/` is a separate service and is **not required**
to view the marketing/auth pages (only API-backed workspace pages need it).

## 1. Reproduce the uncommitted artifacts

A fresh checkout needs two things to run the frontend:

1. **Dependencies** (project uses npm; `frontend/package-lock.json` is committed):
   ```
   cd frontend
   npm install
   ```
   `frontend/node_modules/` is usually already present in the worktree.

2. **Frontend env file** — copy the template, or copy `.env.local` from the main
   checkout (it contains only browser-safe `NEXT_PUBLIC_*` values):
   ```
   cp frontend/.env.local.example frontend/.env.local   # or copy from the main checkout
   ```
   Procedure: **copy `frontend/.env.local` from the main checkout** (never
   symlink — ports may need adapting per worktree). Values it holds:
   `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`.

   The repository-root `.env` (Supabase service-role key, DB URL, AI keys) is
   **backend-only** and is not needed for the frontend preview.

Do **not** commit any `.env`/`.env.local` file — only the templates.

## 2. Run the server

```
cd frontend
npm run dev          # next dev (Next.js 16.3.5, Turbopack)
```

**Port:** this environment sets `PORT=0`, so Next binds a **random free port**.
Read the actual port from the startup log line:
```
- Local:  http://localhost:<port>
```
To pin the conventional port instead, run `npm run dev -- -p 3000` (only if free).

**Open the app via `http://localhost:<port>`, NOT `http://127.0.0.1:<port>`.**
Next.js 16 blocks "cross-origin" dev resources (`/_next/hmr`, `/__nextjs_font/*`)
when requested from `127.0.0.1`, which silently breaks client hydration (React
event handlers never attach, menus/forms do nothing) and Fast Refresh. The
server logs this as:
```
⚠ Blocked cross-origin request to Next.js dev resource /_next/hmr from "127.0.0.1".
```
If `127.0.0.1` must work, add `allowedDevOrigins: ['127.0.0.1']` to
`frontend/next.config.ts` and restart the dev server.

**Detached start (Windows)** — stdout and stderr must go to *different* files:
```
powershell -NoProfile -Command "(Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev' -RedirectStandardOutput '<log>' -RedirectStandardError '<log>.err' -WindowStyle Hidden -PassThru).Id"
```
Run this from `frontend/`. Name the executable exactly (`npm.cmd`) — Start-Process
does not resolve shell shims. Confirm it survived:
```
powershell -NoProfile -Command "Get-Process -Id <pid>"
```

**Wait for the first compile before registering.** The first `GET /` compiles the
route and can take ~15-20s; the server prints "Ready" before that. Wait until
`GET /` actually returns 200, then register the preview with the `localhost` URL
and the node process id.

## 3. Tests

All commands run from `frontend/`.

```
npm test          # Vitest: unit, component, and axe accessibility tests (jsdom)
npm run test:e2e  # Playwright: full signup -> report journey (Chromium)
npx tsc --noEmit  # TypeScript
npm run lint      # ESLint
npm run build     # production build
```

**Vitest** tests live in `frontend/tests/**` and need no backend or network.
Config: `vitest.config.ts` + `vitest.setup.ts`; axe helper in `tests/axe.ts`.

**Playwright** tests live in `frontend/e2e/**`. The suite is hermetic: it starts
its own mock Supabase + mock backend (`e2e/mock-server.mjs`) and its own Next dev
server (see `playwright.config.ts`), so it needs no live services or AI keys.
First run only, install the browser:
```
npx playwright install chromium chromium-headless-shell
```
Notes:
- The E2E dev server runs on port **3100** against a mock on **4010**, and uses
  `NEXT_DIST_DIR=.next-e2e` so it does **not** collide with a dev server you
  already have open on the same project directory (Next 16 allows only one
  `next dev` per project dir, and it uses the dist dir to detect that).
- Use `http://localhost:3100` (not `127.0.0.1`) — see the hydration note in §2.
- Artifacts (`test-results/`, `playwright-report/`, `.next-e2e/`) are gitignored.

## 4. Notes

- Route `/dashboard`, `/upload`, `/settings`, etc. redirect to
  `/login?next=...` when signed out (this is expected).
- Handlers live behind the Supabase session; without a logged-in user the
  marketing and login pages are what you can exercise.
- Adding features above this section is out of scope for the run doc.
