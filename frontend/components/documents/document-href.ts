import type { DocumentOut } from "@/lib/types";

/** Routes a document to its review page, or processing when not ready. */
export function documentHref(document: DocumentOut): string {
  if (document.status === "READY") {
    return `/documents/${document.id}`;
  }
  return `/documents/${document.id}/processing`;
}