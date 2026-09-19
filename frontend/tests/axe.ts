import axe from "axe-core";
import { expect } from "vitest";

/**
 * Run axe-core over a rendered tree and assert there are zero violations.
 *
 * `color-contrast` is disabled because jsdom has no layout/paint, so contrast
 * cannot be computed there. Every other rule runs.
 */
export async function expectNoA11yViolations(container: HTMLElement): Promise<void> {
  const results = await axe.run(container, {
    rules: {
      "color-contrast": { enabled: false },
    },
  });

  const summary = results.violations.map(
    (violation) => `${violation.id}: ${violation.help} [${violation.nodes.length} node(s)]`,
  );
  expect(summary).toEqual([]);
}
