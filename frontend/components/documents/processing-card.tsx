import Link from "next/link";
import { FileText } from "lucide-react";

import { PROCESSING_LABELS, documentStatusLabel } from "@/lib/constants";
import type { DocumentOut, DocumentStatusData } from "@/lib/types";

function ProgressBar({ progress }: { progress: number | null }) {
  return (
    <div
      role="progressbar"
      aria-valuenow={progress ?? undefined}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Processing progress"
      className="h-1.5 w-full overflow-hidden rounded-full bg-blue-100"
    >
      <div
        className={progress != null ? "h-full rounded-full bg-brand transition-all" : "processing-indeterminate h-full rounded-full bg-brand"}
        style={progress != null ? { width: `${Math.min(100, Math.max(0, progress))}%` } : undefined}
      />
    </div>
  );
}

/** Card for a document that is still processing (Dashboard + Processing page). */
export function ProcessingCard({
  document,
  status,
}: {
  document: DocumentOut;
  status: DocumentStatusData | null;
}) {
  const label = documentStatusLabel(document.status);

  return (
    <article className="rounded-xl border border-line bg-surface p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-brand">
            <FileText className="size-5" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <Link
              href={`/documents/${document.id}/processing`}
              className="block truncate font-medium text-ink hover:text-brand"
            >
              {document.display_name ?? document.filename}
            </Link>
            <p className="mt-0.5 text-sm text-muted">{label}</p>
          </div>
        </div>
      </div>
      <div className="mt-4 flex flex-col gap-2">
        <ProgressBar progress={status?.progress ?? null} />
        <p className="text-sm text-muted">
          {status?.message ?? PROCESSING_LABELS[document.status] ?? "Processing…"}
        </p>
      </div>
    </article>
  );
}