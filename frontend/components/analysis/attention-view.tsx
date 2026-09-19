"use client";

import { AlertTriangle } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonList } from "@/components/ui/skeleton";
import { AttentionBadge } from "@/components/ui/status";
import type { AttentionItemOut, DocumentOut } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

type AttentionData = {
  items: AttentionItemOut[];
};

export function AttentionView({ document }: { document: DocumentOut }) {
  const { loading, data, error, retry } = useApiData<AttentionData>(
    `/documents/${document.id}/attention`,
  );

  if (loading) {
    return <SkeletonList rows={3} />;
  }

  if (error) {
    return (
      <ErrorState
        title="Attention analysis is not available yet"
        message={`${error} Areas requiring attention will appear here once analysis has been completed.`}
        onRetry={retry}
      />
    );
  }

  const items = data?.items ?? [];

  if (items.length === 0) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="No attention items"
        description="Areas worth reviewing in this document will be surfaced here. None were detected yet."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="sr-only">Attention items</h2>
      <Alert kind="info">
        Attention items indicate areas worth reviewing carefully before a
        decision — they are not legal risk scores or conclusions.
      </Alert>
      {items.map((item) => (
        <Card key={item.id}>
          <CardContent className="flex flex-col gap-3 p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h3 className="font-semibold text-navy">{item.title}</h3>
              <AttentionBadge level={item.attention_level} />
            </div>
            <p className="text-[15px] leading-relaxed">{item.description}</p>
            {item.recommendation ? (
              <p className="rounded-lg bg-canvas/60 px-4 py-3 text-sm text-ink">
                <span className="font-medium text-navy">Recommendation: </span>
                {item.recommendation}
              </p>
            ) : null}
            {item.category ? (
              <p className="text-xs uppercase tracking-wide text-muted">{item.category}</p>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}