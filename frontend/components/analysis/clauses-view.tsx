"use client";

import { ScrollText } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonList } from "@/components/ui/skeleton";
import { formatPage } from "@/lib/format";
import type { DocumentOut, ImportantClause } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

type ClauseListData = {
  clauses?: ImportantClause[];
  items?: ImportantClause[];
};

export function ClausesView({ document }: { document: DocumentOut }) {
  const { loading, data, error, retry } = useApiData<ClauseListData>(
    `/documents/${document.id}/clauses`,
  );

  if (loading) {
    return <SkeletonList rows={4} />;
  }

  if (error) {
    return (
      <ErrorState
        title="Clause analysis is not available yet"
        message={`${error} Detected clauses will appear here once analysis has been completed.`}
        onRetry={retry}
      />
    );
  }

  const clauses = data?.clauses ?? data?.items ?? [];

  if (clauses.length === 0) {
    return (
      <EmptyState
        icon={ScrollText}
        title="No clauses detected"
        description="Clauses detected in this document will be listed here for review."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="sr-only">Detected clauses</h2>
      {clauses.map((clause, index) => (
        <Card key={clause.clause_id ?? index}>
          <CardContent className="flex flex-col gap-3 p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                {clause.clause_number ? (
                  <span className="rounded-md bg-navy px-2 py-0.5 text-xs font-semibold text-white">
                    {clause.clause_number}
                  </span>
                ) : null}
                <h3 className="font-semibold text-navy">{clause.title ?? "Clause"}</h3>
              </div>
              <span className="text-sm text-muted">
                {[clause.section, formatPage(clause.page_start, clause.page_end)]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </div>

            {clause.explanation ? (
              <p className="text-[15px] leading-relaxed">{clause.explanation}</p>
            ) : null}

            <blockquote className="rounded-lg border-l-4 border-line bg-canvas/60 px-4 py-3 text-sm italic text-muted">
              {clause.original_text}
            </blockquote>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}