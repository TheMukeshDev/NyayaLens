import axe from "axe-core";
import { expect } from "vitest";

/**
 * Run axe-core over a rendered tree and assert there are zero violations.
 *
 * `color-contrast` is disabled because jsdom has no layout/paint, so contrast
 * cannot be computed there. Every other rule runs.
 */
let axeQueue: Promise<unknown> = Promise.resolve();

export async function expectNoA11yViolations(container: HTMLElement): Promise<void> {
  const runAxe = () =>
    axe.run(container, {
      rules: {
        "color-contrast": { enabled: false },
      },
    });

  const nextPromise = axeQueue.then(runAxe, runAxe);
  axeQueue = nextPromise.catch(() => {});
  const results = await nextPromise;

  const summary = results.violations.map(
    (violation) => `${violation.id}: ${violation.help} [${violation.nodes.length} node(s)]`,
  );
  expect(summary).toEqual([]);
}
