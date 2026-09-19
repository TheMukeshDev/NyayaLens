import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

// The real module is a Next.js server action ("use server").
vi.mock("@/app/(app)/actions", () => ({
  signOut: vi.fn(),
}));

import { AppShell } from "@/components/app-shell";

describe("AppShell", () => {
  it("exposes a skip link and a main-content target", () => {
    render(<AppShell email="user@example.com">content</AppShell>);
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveAttribute(
      "href",
      "#main-content",
    );
    expect(document.getElementById("main-content")).not.toBeNull();
  });

  it("opens the mobile drawer as a modal dialog and closes it with Escape", async () => {
    const user = userEvent.setup();
    render(<AppShell email="user@example.com">content</AppShell>);

    await user.click(screen.getByRole("button", { name: "Open menu" }));

    const dialog = screen.getByRole("dialog", { name: "Workspace menu" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("button", { name: "Close menu" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );

    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Workspace menu" })).toBeNull();
    });
    expect(screen.getByRole("button", { name: "Open menu" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });
});
