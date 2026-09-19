import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// `globals` is disabled, so React Testing Library cannot auto-register its
// cleanup hook — do it explicitly so each test starts from an empty document.
afterEach(() => {
  cleanup();
});
