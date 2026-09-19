import { expect, test } from "@playwright/test";

import { SEEDED_DOCUMENT_ID, pdfFixture, signIn, waitForHydrated } from "./fixtures";

test("landing page renders and is interactive", async ({ page }) => {
  const response = await page.goto("/", { waitUntil: "domcontentloaded" });
  expect(response?.status()).toBe(200);

  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("link", { name: /get started/i }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /^log in$/i }).first()).toBeVisible();

  // Client-side routing proves the page hydrated (not just rendered on the server).
  const primaryNav = page.getByRole("navigation", { name: "Primary" });
  await primaryNav.getByRole("link", { name: "Features" }).click();
  await expect(page).toHaveURL(/\/features$/);
  await expect(primaryNav.getByRole("link", { name: "Features" })).toHaveAttribute(
    "aria-current",
    "page",
  );
});

test("protected routes redirect to login when signed out", async ({ page }) => {
  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/login\?next=(%2F|\/)dashboard$/);
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();

  await page.goto("/upload", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/login\?next=(%2F|\/)upload$/);
});

test("a document the user does not own is not found", async ({ page }) => {
  await signIn(page);

  const response = await page.goto("/documents/99999999-9999-4999-8999-999999999999", {
    waitUntil: "domcontentloaded",
  });
  expect(response?.status()).toBe(404);
});

/**
 * The full product journey, end to end through the real UI against the mock
 * services. Each step asserts observable, user-facing state.
 */
test("signup -> login -> upload -> processing -> overview -> summary -> Q&A -> comparison -> action center -> report", async ({
  page,
}) => {
  /* ---- 1. Signup (email confirmation required) --------------------------- */
  const newEmail = `e2e.signup.${Date.now()}@example.com`;
  await page.goto("/signup", { waitUntil: "domcontentloaded" });
  await page.fill("#email", newEmail);
  await page.fill("#password", "signup-password-123");
  await page.getByRole("button", { name: "Sign up" }).click();

  await expect(page).toHaveURL(/\/login\?signed_up=1$/);
  await expect(page.getByText("Check your email to confirm your account")).toBeVisible();

  /* ---- 2. Login as the seeded test user ---------------------------------- */
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();

  /* ---- 3. Upload --------------------------------------------------------- */
  await page.goto("/upload", { waitUntil: "domcontentloaded" });
  await waitForHydrated(page);
  await page.setInputFiles("#document-file", pdfFixture());

  const uploadButton = page.getByRole("button", { name: "Upload document" });
  await expect(uploadButton).toBeEnabled();
  await uploadButton.click();

  await expect(page.getByRole("heading", { name: "Document uploaded" })).toBeVisible();

  const processingHref = await page
    .getByRole("link", { name: "View processing" })
    .getAttribute("href");
  expect(processingHref).toMatch(/^\/documents\/[0-9a-f-]+\/processing$/);
  const documentId = processingHref!.split("/")[2];

  /* ---- 4. Processing -> READY -------------------------------------------- */
  await page.getByRole("link", { name: "View processing" }).click();
  await expect(page).toHaveURL(new RegExp(`/documents/${documentId}/processing$`));
  await expect(page.getByText("Document ready")).toBeVisible({ timeout: 30_000 });

  /* ---- 5. Document overview ---------------------------------------------- */
  await page.getByRole("link", { name: "Open document" }).click();
  await expect(page).toHaveURL(new RegExp(`/documents/${documentId}$`));
  await expect(page.getByRole("heading", { level: 1, name: "contract.pdf" })).toBeVisible();
  await expect(page.getByText("Acme Corp")).toBeVisible();

  /* ---- 6. Summary -------------------------------------------------------- */
  await page.getByRole("link", { name: "Summary", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/documents/${documentId}/summary$`));
  await expect(page.getByText("Notice period of 30 days")).toBeVisible();

  /* ---- 7. Q&A ------------------------------------------------------------ */
  await page.getByRole("link", { name: "Ask", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/documents/${documentId}/ask$`));
  await page.fill("#ask-question", "What is the notice period?");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(
    page.getByText(
      "Either party may terminate the agreement by giving at least 30 days written notice.",
    ),
  ).toBeVisible();
  await expect(page.getByText("Sources (1)")).toBeVisible();

  /* ---- 8. Comparison ----------------------------------------------------- */
  await page.goto("/compare", { waitUntil: "domcontentloaded" });
  await waitForHydrated(page);
  await page.selectOption("#compare-a", documentId);
  await page.selectOption("#compare-b", SEEDED_DOCUMENT_ID);
  await page.getByRole("button", { name: "Compare" }).click();

  await expect(page.getByRole("heading", { name: "Differences (1)" })).toBeVisible();
  await expect(page.getByText("The notice period increased from 30 to 60 days.")).toBeVisible();

  /* ---- 9. Action center -------------------------------------------------- */
  await page.goto(`/documents/${documentId}/actions`, { waitUntil: "domcontentloaded" });
  await waitForHydrated(page);
  await page.getByRole("button", { name: "Generate action plan" }).first().click();

  await expect(page.getByRole("heading", { name: "Review checklist" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Review the confidentiality clause" })).toBeVisible();
  await expect(page.getByText("Termination notice period")).toBeVisible();

  // Drive a status transition and observe it in the UI.
  await expect(page.getByRole("button", { name: "Start" })).toHaveCount(2);
  await page.getByRole("button", { name: "Start" }).first().click();
  await expect(page.getByRole("button", { name: "Back to to do" })).toHaveCount(1);

  /* ---- 10. Report -------------------------------------------------------- */
  await page.getByRole("button", { name: "Create review report" }).click();
  await expect(page.getByText("Report created")).toBeVisible();
  await page.getByRole("link", { name: "View reports" }).click();

  await expect(page).toHaveURL(/\/reports$/);
  await expect(page.getByText("Review", { exact: true })).toBeVisible();

  const [popup] = await Promise.all([
    page.waitForEvent("popup"),
    page.getByRole("button", { name: "Download" }).click(),
  ]);
  await expect.poll(() => popup.url()).toContain("mock-report.pdf");
});
