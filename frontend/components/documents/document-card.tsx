import Link from "next/link";
import { FileText } from "lucide-react";

import { DocumentStatusBadge } from "@/components/ui/status";
import { formatBytes, formatRelativeTime } from "@/lib/format";
import type { DocumentOut } from "@/lib/types";

import { RetryButton } from "./retry-button";
import { documentHref } from "./document-href";

export function DocumentCard({ document }: { document: DocumentOut }) {
  const failed = document.status === "FAILED";
  const ready = document.status === "READY";

  return (
    <article className="rounded-xl border border-line bg-surface p-5 shadow-sm transition-shadow hover:shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span
            className={`mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-lg ${
              failed ? "bg-red-50 text-danger-strong" : "bg-blue-50 text-brand"
            }`}
          >
            <FileText className="size-5" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <Link
              href={documentHref(document)}
              className="block truncate font-medium text-ink hover:text-brand"
            >
              {document.display_name ?? document.filename}
            </Link>
            <p className="mt-0.5 text-sm text-muted">
              {formatBytes(document.file_size_bytes)}
              {document.uploaded_at ? ` · uploaded ${formatRelativeTime(document.uploaded_at)}` : ""}
            </p>
            {failed && document.processing_error ? (
              <p className="mt-1 text-sm text-danger-strong">{document.processing_error}</p>
            ) : null}
          </div>
        </div>
        <DocumentStatusBadge status={document.status} />
      </div>
      <div className="mt-4 flex items-center gap-3">
        <Link
          href={documentHref(document)}
          className="text-sm font-medium text-brand hover:underline"
        >
          {ready ? "Open document" : "View progress"}
        </Link>
        {failed ? <RetryButton document={document} /> : null}
      </div>
    </article>
  );
}