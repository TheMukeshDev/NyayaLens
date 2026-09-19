import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Alert } from "@/components/ui/alert";

describe("Alert", () => {
  it("uses role=alert for errors so it is announced", () => {
    render(
      <Alert kind="error" title="Upload failed">
        Try again.
      </Alert>,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Upload failed");
    expect(alert).toHaveTextContent("Try again.");
  });

  it("uses role=status for non-error kinds", () => {
    render(<Alert kind="info">Heads up.</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Heads up.");
  });
});
