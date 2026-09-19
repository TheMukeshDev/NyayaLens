import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ActionCard } from "@/components/actions/action-card";
import type { ActionOut } from "@/lib/types";

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

describe("ActionCard", () => {
  it("renders the title, type, priority and evidence source", () => {
    render(<ActionCard action={action} onStatus={vi.fn()} busy={false} />);
    expect(
      screen.getByRole("heading", { name: "Review the termination notice period" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Review a clause")).toBeInTheDocument();
    expect(screen.getByText("High priority")).toBeInTheDocument();
    expect(screen.getByText("8 · 8.2 · p. 6")).toBeInTheDocument();
  });

  it("reports the requested status change", async () => {
    const onStatus = vi.fn();
    const user = userEvent.setup();
    render(<ActionCard action={action} onStatus={onStatus} busy={false} />);

    await user.click(screen.getByRole("button", { name: /complete/i }));
    expect(onStatus).toHaveBeenCalledWith("COMPLETED");

    await user.click(screen.getByRole("button", { name: /start/i }));
    expect(onStatus).toHaveBeenCalledWith("IN_PROGRESS");
  });

  it("disables every action while a request is in flight", () => {
    render(<ActionCard action={action} onStatus={vi.fn()} busy />);
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
    for (const button of buttons) {
      expect(button).toBeDisabled();
    }
  });
});
