import { clientApi, clientJson } from "@/lib/api/client";
import { ERROR_MESSAGES } from "@/lib/constants";
import { isDemoMode } from "@/lib/supabase/config";
import type { ApiError, DocumentOut, UploadIntentData } from "@/lib/types";

/**
 * Direct-to-storage document upload.
 *
 * The file bytes are never sent through the API: a serverless function has a
 * hard request-body limit far below the supported upload size, and buffering
 * the file would also pin a container's memory for the whole transfer. Instead:
 *
 *   1. `POST /documents/upload-intent` reserves a private object key and
 *      returns a single-use signed URL.
 *   2. the browser `PUT`s the bytes straight to Supabase Storage.
 *   3. `POST /documents/{id}/complete` makes the backend read the object back
 *      and verify its magic bytes, real size and checksum before recording it.
 *
 * Nothing the browser declares is trusted as the record of the upload; step 3
 * is the security boundary, and it is also what rejects a file whose contents
 * do not match its name.
 */
export type UploadResult =
  | { ok: true; document: DocumentOut }
  | { ok: false; error: ApiError };

function uploadError(code: string, message: string): UploadResult {
  return { ok: false, error: { code, message, details: null } };
}

/** `PUT` the raw bytes to the signed upload URL Supabase issued. */
async function putToStorage(
  ticket: UploadIntentData["upload"],
  file: File,
): Promise<{ ok: true } | { ok: false; message: string }> {
  try {
    const response = await fetch(ticket.signed_url, {
      method: "PUT",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: file,
    });
    if (!response.ok) {
      return {
        ok: false,
        message:
          "The file could not be transferred to secure storage. Check your connection and try again.",
      };
    }
    return { ok: true };
  } catch {
    return {
      ok: false,
      message: "The file could not be transferred to secure storage. Please try again.",
    };
  }
}

export async function uploadDocument(file: File): Promise<UploadResult> {
  if (isDemoMode()) {
    const now = new Date().toISOString();
    return {
      ok: true,
      document: {
        id: `demo-document-${Date.now()}`,
        filename: file.name,
        display_name: file.name,
        mime_type: file.type || "application/octet-stream",
        file_size_bytes: file.size,
        status: "READY",
        processing_error: null,
        page_count: null,
        checksum_sha256: null,
        uploaded_at: now,
        created_at: now,
        updated_at: now,
      },
    };
  }

  const intent = await clientJson<UploadIntentData>(
    "/documents/upload-intent",
    "POST",
    { filename: file.name, size_bytes: file.size },
  );
  if (!intent.ok || !intent.data) {
    return uploadError(
      intent.error?.code ?? "INTERNAL_ERROR",
      intent.error?.message ?? "The upload could not be started. Please try again.",
    );
  }

  const { document, upload } = intent.data;

  const transferred = await putToStorage(upload, file);
  if (!transferred.ok) {
    return uploadError("STORAGE_ERROR", transferred.message);
  }

  const completed = await clientApi<DocumentOut>(`/documents/${document.id}/complete`, {
    method: "POST",
  });
  if (!completed.ok || !completed.data) {
    return uploadError(
      completed.error?.code ?? "INTERNAL_ERROR",
      completed.error?.message ?? "The upload could not be verified. Please try again.",
    );
  }

  return { ok: true, document: completed.data };
}

/**
 * Ask the backend to process a document that is sitting in `UPLOADED`.
 *
 * There is no long-lived background worker on a serverless host, so processing
 * is requested per document. Deliberately fire-and-forget: the processing page
 * polls status, and a slow or failed request must not block navigation. The
 * endpoint is owner-scoped and refuses documents that are not `UPLOADED`, so
 * repeating the call is harmless.
 */
export function requestProcessing(documentId: string): void {
  if (isDemoMode()) return;
  void clientApi<DocumentOut>(`/documents/${documentId}/process`, {
    method: "POST",
    keepalive: true,
  }).catch(() => undefined);
}

/** Human-readable message for a failed upload, preferring the curated copy. */
export function uploadErrorMessage(result: Extract<UploadResult, { ok: false }>): string {
  const { code, message } = result.error;
  return ERROR_MESSAGES[code] ?? message;
}
