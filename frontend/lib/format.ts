/** Formatting helpers for file metadata, dates and pages. */

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const dateFormatter = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
  timeStyle: "short",
});

const dayFormatter = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
});

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return dateFormatter.format(date);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return dayFormatter.format(date);
}

/** Short relative form such as "Just now", "3h ago", "2d ago". */
export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return dayFormatter.format(date);
}

/** Formats e.g. "8" or "8–11" from a page range. */
export function formatPage(pageStart: number | null | undefined, pageEnd?: number | null): string {
  if (pageStart == null) return "";
  if (pageEnd != null && pageEnd > pageStart) return `p. ${pageStart}–${pageEnd}`;
  return `p. ${pageStart}`;
}

/** Renders a source location compactly, e.g. "Section 8 · p. 6". */
export function formatSource(location: {
  section?: string | null;
  clause?: string | null;
  page_start?: number | null;
  page_end?: number | null;
}): string {
  const parts: string[] = [];
  if (location.section) parts.push(location.section);
  if (location.clause) parts.push(location.clause);
  const page = formatPage(location.page_start, location.page_end);
  if (page) parts.push(page);
  return parts.join(" · ");
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/(^|\s)(\p{L})/gu, (match) => match.toUpperCase());
}