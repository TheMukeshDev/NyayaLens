import { describe, expect, it, vi } from "vitest";

import {
  formatBytes,
  formatDate,
  formatDateTime,
  formatPage,
  formatRelativeTime,
  formatSource,
  titleCase,
} from "@/lib/format";

describe("formatBytes", () => {
  it("formats bytes, kilobytes and megabytes", () => {
    expect(formatBytes(500)).toBe("500 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});

describe("formatPage", () => {
  it("returns an empty string without a start page", () => {
    expect(formatPage(null)).toBe("");
    expect(formatPage(undefined)).toBe("");
  });

  it("formats a single page and a range", () => {
    expect(formatPage(6)).toBe("p. 6");
    expect(formatPage(6, 6)).toBe("p. 6");
    expect(formatPage(6, 9)).toBe("p. 6–9");
  });
});

describe("formatSource", () => {
  it("joins the populated parts with a middot", () => {
    expect(formatSource({ section: "8", clause: "8.2", page_start: 6, page_end: 6 })).toBe(
      "8 · 8.2 · p. 6",
    );
  });

  it("omits missing parts", () => {
    expect(formatSource({ section: "8" })).toBe("8");
    expect(formatSource({})).toBe("");
  });
});

describe("formatDate / formatDateTime", () => {
  it("returns an em dash for empty or invalid values", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime("not-a-date")).toBe("—");
  });

  it("formats an ISO timestamp", () => {
    expect(formatDate("2026-09-19T10:00:00Z")).toMatch(/2026/);
  });
});

describe("titleCase", () => {
  it("converts snake_case to Title Case", () => {
    expect(titleCase("employment_agreement")).toBe("Employment Agreement");
    expect(titleCase("nda")).toBe("Nda");
  });
});

describe("formatRelativeTime", () => {
  it("returns 'Just now' for a fresh timestamp", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-19T10:00:00Z"));
    expect(formatRelativeTime("2026-09-19T09:59:30Z")).toBe("Just now");
    vi.useRealTimers();
  });

  it("returns hours and days", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-19T10:00:00Z"));
    expect(formatRelativeTime("2026-09-19T07:00:00Z")).toBe("3h ago");
    expect(formatRelativeTime("2026-09-17T10:00:00Z")).toBe("2d ago");
    vi.useRealTimers();
  });

  it("returns an em dash for missing or invalid input", () => {
    expect(formatRelativeTime(null)).toBe("—");
    expect(formatRelativeTime("nope")).toBe("—");
  });
});
