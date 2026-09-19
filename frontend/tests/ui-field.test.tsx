import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Field, FormError, Input } from "@/components/ui/field";

describe("Field", () => {
  it("associates the label with its control", () => {
    render(
      <Field label="Email" htmlFor="email">
        <Input id="email" />
      </Field>,
    );
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("links hint and error text and marks the control invalid", () => {
    render(
      <Field
        label="Email"
        htmlFor="email"
        hint="We never share it."
        error="Enter a valid email."
      >
        <Input id="email" />
      </Field>,
    );

    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");

    const describedBy = input.getAttribute("aria-describedby") ?? "";
    expect(describedBy).toContain("email-error");
    expect(describedBy).toContain("email-hint");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email.");
  });
});

describe("FormError", () => {
  it("is announced as an alert", () => {
    render(<FormError message="Something went wrong." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong.");
  });
});
