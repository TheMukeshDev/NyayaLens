import { expect, type Page } from "@playwright/test";

/**
 * The seeded test user.
 *
 * `e2e/mock-server.mjs` seeds this account before the app starts, so logging in
 * never creates a real account anywhere. Keep the two files in sync.
 */
export const TEST_USER = {
  email: "e2e.user@example.com",
  password: "e2e-password-123",
} as const;

/** A document the mock already reports as READY (for the compare step). */
export const SEEDED_DOCUMENT_ID = "22222222-2222-4222-8222-222222222222";

/** Signs in through the real login form and waits for the workspace. */
export async function signIn(page: Page, user: { email: string; password: string } = TEST_USER) {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.fill("#email", user.email);
  await page.fill("#password", user.password);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

/**
 * Waits until React has hydrated the app shell.
 *
 * `domcontentloaded` can fire before React attaches its event handlers, and
 * events dispatched into a not-yet-hydrated client component are simply lost
 * (e.g. choosing an upload file never enables the submit button). React tags
 * the DOM nodes it owns with `__reactFiber$*`, so we wait for that marker.
 */
export async function waitForHydrated(page: Page, selector = "#main-content") {
  await page.waitForFunction(
    (sel) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      return Object.keys(el).some((key) => key.startsWith("__reactFiber$"));
    },
    selector,
    { timeout: 30_000 },
  );
}

/** A tiny, valid-enough PDF payload for the upload flow. */
export function pdfFixture(name = "contract.pdf") {
  return {
    name,
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n% e2e fixture\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"),
  };
}
