import type { ReactNode } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, FileText } from "lucide-react";

import { DocumentNav } from "@/components/documents/document-nav";
import { Alert } from "@/components/ui/alert";
import { DocumentStatusBadge } from "@/components/ui/status";
import { RetryButton } from "@/components/documents/retry-button";
import { serverApi } from "@/lib/api/server";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { DocumentOut } from "@/lib/types";

export default async function DocumentLayout({
  params,
  children,
}: {
  params: Promise<{ documentId: string }>;
  children: ReactNode;
}) {
  const { documentId } = await params;
  const result = await serverApi<DocumentOut>(`/documents/${documentId}`);

  if (result.error?.code === "DOCUMENT_NOT_FOUND") {
    notFound();
  }

  if (!result.ok) {
    return (
      <div className="flex flex-col gap-4">
        <Link href="/dashboard" className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-muted hover:text-ink">
          <ArrowLeft className="size-4" aria-hidden="true" />
          Dashboard
        </Link>
        <Alert kind="error" title="Document unavailable">
          {result.error?.message ??
            "We could not load this document right now. Please go back to your dashboard and try again."}
        </Alert>
      </div>
    );
  }

  const document = result.data as DocumentOut;
  const failed = document.status === "FAILED";

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/dashboard"
        className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-muted hover:text-ink"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Dashboard
      </Link>

      <div className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <span className="mt-1 flex size-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-brand">
              <FileText className="size-5.5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h1 className="truncate text-2xl font-bold tracking-tight text-navy">
                {document.display_name ?? document.filename}
              </h1>
              <p className="mt-1 text-sm text-muted">
                {formatBytes(document.file_size_bytes)}
                {document.page_count ? ` · ${document.page_count} page${document.page_count === 1 ? "" : "s"}` : ""}
                {document.uploaded_at ? ` · uploaded ${formatDateTime(document.uploaded_at)}` : ""}
              </p>
            </div>
          </div>
          <DocumentStatusBadge status={document.status} />
        </div>

        {failed ? (
          <Alert kind="error" title="Processing failed" action={<RetryButton document={document} />}>
            {document.processing_error ??
              "We could not process this document. You can retry, or upload the file again."}
          </Alert>
        ) : null}
      </div>

      <DocumentNav document={document} />

      {children}
    </div>
  );
}