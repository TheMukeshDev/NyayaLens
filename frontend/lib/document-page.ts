import { notFound, redirect } from "next/navigation";

import { serverApi } from "@/lib/api/server";
import type { DocumentOut } from "@/lib/types";

/**
 * Server-side document loader for document tab pages.
 * Redirects to /login (via the workspace layout), /dashboard or /processing
 * when the document cannot be reviewed right now.
 */
export async function loadDocument(
  documentId: string,
  options: { requireReady?: boolean } = {},
): Promise<DocumentOut> {
  const result = await serverApi<DocumentOut>(`/documents/${documentId}`);

  if (result.error?.code === "DOCUMENT_NOT_FOUND") {
    notFound();
  }
  if (!result.ok) {
    redirect("/dashboard");
  }

  const document = result.data as DocumentOut;
  if (options.requireReady && document.status !== "READY") {
    redirect(`/documents/${documentId}/processing`);
  }
  return document;
}