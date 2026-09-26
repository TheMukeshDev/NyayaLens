import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright end-to-end configuration.
 *
 * The suite is hermetic: instead of a live Supabase project and FastAPI
 * backend, `e2e/mock-server.mjs` serves both `/auth/v1/*` (Supabase Auth) and
 * `/api/v1/*` (NyayaLens API). The Next.js dev server is started with
 * `SUPABASE_URL` / `NEXT_PUBLIC_API_URL` pointed at that mock, so the
 * complete signup -> report journey runs through the real UI with no external
 * dependencies. The seeded test user is defined in `e2e/fixtures.ts`.
 */
const MOCK_PORT = 4010;
const APP_PORT = 3100;

const MOCK_URL = `http://localhost:${MOCK_PORT}`;
const APP_URL = `http://localhost:${APP_PORT}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  timeout: 90_000,
  expect: { timeout: 20_000 },

  use: {
    baseURL: APP_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    // Next.js dev keeps long-lived connections open, so the `load` event can be
    // deferred; assertions wait for specific UI instead.
    navigationTimeout: 90_000,
    actionTimeout: 20_000,
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  webServer: [
    {
      command: "node e2e/mock-server.mjs",
      url: `${MOCK_URL}/__health`,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      env: { E2E_MOCK_PORT: String(MOCK_PORT) },
    },
    {
      command: "npm run dev",
      url: `${APP_URL}/`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        PORT: String(APP_PORT),
        // A separate build dir lets this dev server coexist with any dev server
        // the developer already has open (Next 16 allows one per project dir).
        NEXT_DIST_DIR: ".next-e2e",
        SUPABASE_URL: MOCK_URL,
        SUPABASE_ANON_KEY: "e2e-anon-key",
        // The browser bundle only ever sees NEXT_PUBLIC_* values, and a developer's
        // `.env.local` typically points those at a real project (or demo mode).
        // Setting both spellings here is what actually keeps the suite hermetic.
        NEXT_PUBLIC_SUPABASE_URL: MOCK_URL,
        NEXT_PUBLIC_SUPABASE_ANON_KEY: "e2e-anon-key",
        NEXT_PUBLIC_DEMO_MODE: "false",
        NEXT_PUBLIC_API_URL: MOCK_URL,
      },
    },
  ],
});
