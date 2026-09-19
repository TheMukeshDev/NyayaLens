import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));
vi.mock("@/app/(app)/actions", () => ({
  signOut: vi.fn(),
}));

import { ActionCard } from "@/components/actions/action-card";
import { AppShell } from "@/components/app-shell";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { SkipLink } from "@/components/ui/skip-link";
import { DocumentStatusBadge, EvidenceBadge } from "@/components/ui/status";
import type { ActionOut } from "@/lib/types";

import { expectNoA11yViolations } from "./axe";

const action: ActionOut = {
  id: "11111111-1111-1111-1111-111111111111",
  document_id: "22222222-2222-2222-2222-222222222222",
  attention_item_id: null,
  action_type: "REVIEW_CLAUSE",
  title: "Review the termination notice period",
  description: "The notice period may require review.",
  priority: "HIGH",
  status: "TODO",
  due_date: null,
  source: { section: "8", clause: "8.2", page_start: 6, page_end: 6 },
  created_at: null,
};

describe("accessibility (axe-core)", () => {
  it("Button (button and link variants)", async () => {
    const { container } = render(
      <div>
        <Button>Primary action</Button>
        <Button href="/signup" variant="secondary">
          Sign up
        </Button>
        <Button loading>Saving</Button>
      </div>,
    );
    await expectNoA11yViolations(container);
  });

  it("Alert (info and error)", async () => {
    const { container } = render(
      <div>
        <Alert kind="info" title="Note">
          Informational message.
        </Alert>
        <Alert kind="error" title="Failed">
          Something failed.
        </Alert>
      </div>,
    );
    await expectNoA11yViolations(container);
  });

  it("Field with an error and hint", async () => {
    const { container } = render(
      <Field
        label="Email"
        htmlFor="a11y-email"
        hint="We never share it."
        error="Enter a valid email."
        required
      >
        <Input id="a11y-email" type="email" />
      </Field>,
    );
    await expectNoA11yViolations(container);
  });

  it("Action card", async () => {
    const { container } = render(
      <ActionCard action={action} onStatus={vi.fn()} busy={false} />,
    );
    await expectNoA11yViolations(container);
  });

  it("Status badges", async () => {
    const { container } = render(
      <div>
        <EvidenceBadge state="DOCUMENT-GROUNDED" />
        <DocumentStatusBadge status="READY" />
      </div>,
    );
    await expectNoA11yViolations(container);
  });

  it("Skip link with its main-content target", async () => {
    const { container } = render(
      <div>
        <SkipLink />
        <main id="main-content" tabIndex={-1}>
          Content
        </main>
      </div>,
    );
    await expectNoA11yViolations(container);
  });

  it("Marketing navigation (collapsed and expanded)", async () => {
    const user = userEvent.setup();
    const { container } = render(<MarketingNav />);

    await expectNoA11yViolations(container);

    await user.click(screen.getByRole("button", { name: "Open menu" }));
    await expectNoA11yViolations(container);
  });

  it("Workspace shell (drawer closed and open)", async () => {
    const user = userEvent.setup();
    const { container } = render(<AppShell email="user@example.com">content</AppShell>);

    await expectNoA11yViolations(container);

    await user.click(screen.getByRole("button", { name: "Open menu" }));
    await expectNoA11yViolations(container);
  });
});
