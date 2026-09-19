import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  DocumentStatusBadge,
  EvidenceBadge,
  PriorityBadge,
} from "@/components/ui/status";

describe("status badges", () => {
  it("renders every evidence state with human copy", () => {
    const { rerender } = render(<EvidenceBadge state="DOCUMENT-GROUNDED" />);
    expect(screen.getByText("Document-grounded")).toBeInTheDocument();

    rerender(<EvidenceBadge state="INSUFFICIENT-EVIDENCE" />);
    expect(screen.getByText("Insufficient evidence")).toBeInTheDocument();
  });

  it("renders document processing statuses", () => {
    render(<DocumentStatusBadge status="READY" />);
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("renders priorities", () => {
    render(<PriorityBadge priority="HIGH" />);
    expect(screen.getByText("High priority")).toBeInTheDocument();
  });
});
