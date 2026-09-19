import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

import { MarketingNav } from "@/components/marketing/marketing-nav";

describe("MarketingNav", () => {
  it("renders the primary navigation landmark and links", () => {
    render(<MarketingNav />);
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    for (const label of ["Features", "How it works", "Security", "About"]) {
      expect(screen.getAllByRole("link", { name: label }).length).toBeGreaterThan(0);
    }
  });

  it("toggles the mobile menu and reflects it in ARIA state", async () => {
    const user = userEvent.setup();
    render(<MarketingNav />);

    const toggle = screen.getByRole("button", { name: "Open menu" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).toHaveAttribute("aria-controls", "marketing-mobile-menu");
    expect(screen.queryByRole("button", { name: "Close menu" })).toBeNull();

    await user.click(toggle);

    const closeToggle = screen.getByRole("button", { name: "Close menu" });
    expect(closeToggle).toHaveAttribute("aria-expanded", "true");
    expect(document.getElementById("marketing-mobile-menu")).not.toBeNull();

    await user.click(closeToggle);
    expect(screen.getByRole("button", { name: "Open menu" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("shows a dashboard link when logged in", () => {
    render(<MarketingNav loggedIn />);
    expect(screen.getAllByRole("link", { name: /dashboard/i }).length).toBeGreaterThan(0);
  });
});
