"use client";

import { Download, FileText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonList } from "@/components/ui/skeleton";
import { ReportStatusBadge } from "@/components/ui/status";
import { clientJson } from "@/lib/api/client";
import { formatDateTime, titleCase } from "@/lib/format";
import type { ReportDownloadOut, ReportOut } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

function DownloadButton({ reportId }: { reportId: string }) {
  async function download() {
    const result = await clientJson<ReportDownloadOut>(`/reports/${reportId}/download`);
    if (result.ok && result.data?.download_url) {
      window.open(result.data.download_url, "_blank", "noopener,noreferrer");
    }
  }

  return (
    <Button size="sm" variant="secondary" onClick={() => void download()}>
      <Download className="size-3.5" aria-hidden="true" />
      Download
    </Button>
  );
}

export function ReportsView() {
  const { loading, data, error, retry } = useApiData<ReportOut[] | { items: ReportOut[] }>(
    "/reports",
  );

  if (loading) return <SkeletonList rows={3} />;

  if (error) {
    return (
      <ErrorState
        title="Your reports are not available"
        message={`${error} Generated review reports will appear here.`}
        onRetry={retry}
      />
    );
  }

  const reports: ReportOut[] = Array.isArray(data)
    ? data
    : (data?.items as ReportOut[] | undefined) ?? [];

  if (reports.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No reports yet"
        description="Create a review report from any reviewed document's Action Center, and download it here."
        action={<Button href="/upload">Upload a document</Button>}
      />
    );
  }

  return (
    <>
      <h2 className="sr-only">Your reports</h2>
      <ul className="flex flex-col gap-3">
      {reports.map((report) => {
        const ready = report.status === "READY";
        return (
          <li
            key={report.report_id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface p-5"
          >
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-brand">
                <FileText className="size-5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-navy">{titleCase(report.report_type)}</p>
                <p className="text-sm text-muted">
                  Created {formatDateTime(report.created_at)}
                  {report.completed_at ? ` · Completed ${formatDateTime(report.completed_at)}` : ""}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <ReportStatusBadge status={report.status} />
              {ready ? <DownloadButton reportId={report.report_id} /> : null}
            </div>
          </li>
        );
      })}
      </ul>
    </>
  );
}