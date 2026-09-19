"use client";

import { BookOpenText } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonText } from "@/components/ui/skeleton";
import { EvidenceBadge } from "@/components/ui/status";
import type { DocumentOut, UnderstandingSummary } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

function Block({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">{title}</h3>
      <ul className="mt-2 flex flex-col gap-2">
        {items.map((item, index) => (
          <li key={index} className="flex items-start gap-2">
            <span className="mt-2 size-1.5 shrink-0 rounded-full bg-brand" aria-hidden="true" />
            <span className="text-[15px]">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SummaryView({ document }: { document: DocumentOut }) {
  const { loading, data, error, retry } = useApiData<Partial<UnderstandingSummary>>(
    `/documents/${document.id}/summary`,
  );

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <SkeletonText className="h-5 w-48" />
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <SkeletonText className="h-16" />
          <SkeletonText className="h-4 w-3/4" />
          <SkeletonText className="h-4 w-1/2" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Summary is not available yet"
        message={`${error} The summary will appear here once it has been generated for this document.`}
        onRetry={retry}
      />
    );
  }

  const hasContent =
    data &&
    (data.purpose ||
      data.overview ||
      (data.parties && data.parties.length > 0) ||
      (data.key_terms && data.key_terms.length > 0) ||
      (data.obligations && data.obligations.length > 0) ||
      (data.important_conditions && data.important_conditions.length > 0));

  if (!hasContent) {
    return (
      <EmptyState
        icon={BookOpenText}
        title="No summary yet"
        description="A plain-language summary of this document will appear here once it has been generated."
      />
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {data?.evidence_state ? (
        <EvidenceBadge state={data.evidence_state} />
      ) : null}

      {(data.purpose || data.overview) ? (
        <Card>
          <CardHeader>
            <CardTitle as="h2">{data.document_type ? `About this ${data.document_type.toLowerCase()}` : "About this document"}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-[15px] leading-relaxed">{data.purpose ?? data.overview}</p>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardContent className="flex flex-col gap-6 p-6">
          <Block title="Parties" items={data?.parties ?? []} />
          <Block title="Key terms" items={data?.key_terms ?? []} />
          <Block title="Your obligations" items={data?.obligations ?? []} />
          <Block title="Important conditions" items={data?.important_conditions ?? []} />
        </CardContent>
      </Card>

      <Alert kind="info" title="A note on this summary">
        This summary is a plain-language interpretation generated from the
        document text. Treat it as a starting point, not legal advice.
      </Alert>
    </div>
  );
}