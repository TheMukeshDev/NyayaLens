"use client";

import Link from "next/link";
import { FileText } from "lucide-react";

import { RetryButton } from "@/components/documents/retry-button";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DocumentStatusBadge } from "@/components/ui/status";
import { PROCESSING_LABELS, documentStatusLabel } from "@/lib/constants";
import type { DocumentOut, DocumentStatusData } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";
import { formatBytes } from "@/lib/format";

const PROCESSING_POLL_MS = 4000;

function ProgressBar({ progress }: { progress: number | null }) {
  if (progress == null) {
    return (
      <div role="progressbar" aria-label="Processing progress" className="h-1.5 w-full overflow-hidden rounded-full bg-blue-100">
        <div className="processing-indeterminate h-full rounded-full bg-brand" />
      </div>
    );
  }
  return (
    <div
      role="progressbar"
      aria-valuenow={progress}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Processing progress"
      className="h-1.5 w-full overflow-hidden rounded-full bg-blue-100"
    >
      <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
    </div>
  );
}

export function ProcessingView({ document }: { document: DocumentOut }) {
  const { data: status } = useApiData<DocumentStatusData>(
    `/documents/${document.id}/status`,
    PROCESSING_POLL_MS,
  );

  const ready = status?.status === "READY" || document.status === "READY";
  const failed = status?.status === "FAILED" || document.status === "FAILED";
  const label = documentStatusLabel(status?.status ?? document.status);

  return (
    <Card>
      <CardContent className="flex flex-col gap-5 p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-brand">
              <FileText className="size-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="truncate font-medium text-ink">{document.filename}</p>
              <p className="mt-0.5 text-sm text-muted">{formatBytes(document.file_size_bytes)}</p>
            </div>
          </div>
          <DocumentStatusBadge status={status?.status ?? document.status} />
        </div>

        {ready ? (
          <Alert kind="success" title="Document ready">
            <p>
              Your document has finished processing. You can now review the
              summary, clauses, attention items, and ask questions about it.
            </p>
            <div className="mt-3 flex flex-wrap gap-3">
              <Button href={`/documents/${document.id}`}>Open document</Button>
              <Button href="/dashboard" variant="secondary">Go to dashboard</Button>
            </div>
          </Alert>
        ) : failed ? (
          <Alert
            kind="error"
            title="Processing failed"
            action={<RetryButton document={document} />}
          >
            {document.processing_error ??
              "We could not process this document. You can retry, or upload the file again."}
          </Alert>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-ink">{label}</p>
                {status?.progress != null ? (
                  <span className="text-sm text-muted">{status.progress}%</span>
                ) : null}
              </div>
              <ProgressBar progress={status?.progress ?? null} />
              <p className="text-sm text-muted">
                {status?.message ?? PROCESSING_LABELS[document.status] ?? "Processing your document…"}
              </p>
            </div>
            <p className="flex items-center gap-2 text-sm text-muted">
              You can leave this page — your document is stored privately and
              processing continues in the background.
            </p>
            <p>
              <Link href="/dashboard" className="text-sm font-medium text-brand hover:underline">
                Back to dashboard
              </Link>
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}