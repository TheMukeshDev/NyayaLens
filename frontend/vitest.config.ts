import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Frontend unit / component / accessibility test configuration.
 *
 * Tests live in `frontend/tests/**` and run in a jsdom environment (no network,
 * no backend). End-to-end tests live in `frontend/e2e/**` and are driven by
 * Playwright (`playwright.config.ts`), not Vitest.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL(".", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    css: false,
    restoreMocks: true,
    clearMocks: true,
  },
});
