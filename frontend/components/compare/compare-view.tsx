"use client";

import { useState } from "react";
import { ArrowRightLeft, FileText, FlaskConical } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Field, FormError, Select } from "@/components/ui/field";
import { SkeletonList } from "@/components/ui/skeleton";
import { ChangeBadge } from "@/components/ui/status";
import { clientJson } from "@/lib/api/client";
import { formatSource } from "@/lib/format";
import type {
  ChangeOut,
  ComparisonChangesData,
  DocumentOut,
} from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

export function CompareView() {
  const { loading, data, error, retry } = useApiData<DocumentOut[] | { items: DocumentOut[] }>(
    "/documents",
  );
  const [documentA, setDocumentA] = useState("");
  const [documentB, setDocumentB] = useState("");
  const [comparisonId, setComparisonId] = useState<string | null>(null);
  const [comparing, setComparing] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  const documents: DocumentOut[] = Array.isArray(data)
    ? data
    : (data?.items as DocumentOut[] | undefined) ?? [];
  const readyDocuments = documents.filter((doc) => doc.status === "READY");

  async function compare() {
    if (!documentA || !documentB) return;
    setComparing(true);
    setCompareError(null);
    const result = await clientJson<{ comparison_id: string }>(
      "/comparisons",
      "POST",
      { document_a_id: documentA, document_b_id: documentB },
    );
    setComparing(false);
    if (result.ok && result.data?.comparison_id) {
      setComparisonId(result.data.comparison_id);
    } else {
      setCompareError(result.error?.message ?? "Could not start the comparison.");
    }
  }

  if (loading) return <SkeletonList rows={3} />;

  if (error) {
    return (
      <ErrorState
        title="Your documents are not available"
        message={`${error} Once you have uploaded documents, you can compare two versions here.`}
        onRetry={retry}
      />
    );
  }

  if (readyDocuments.length < 1) {
    return (
      <EmptyState
        icon={FileText}
        title="Nothing to compare yet"
        description="Upload two documents you would like to compare — for example an original and a revised version — and differences will be highlighted here."
        action={<Button href="/upload">Upload a document</Button>}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <section aria-label="Choose documents to compare" className="flex flex-col gap-4">
        <h2 className="sr-only">Choose documents to compare</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Document A" htmlFor="compare-a">
            <Select id="compare-a" value={documentA} onChange={(event) => setDocumentA(event.target.value)}>
              <option value="">Choose a document…</option>
              {readyDocuments.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.display_name ?? doc.filename}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Document B" htmlFor="compare-b">
            <Select id="compare-b" value={documentB} onChange={(event) => setDocumentB(event.target.value)}>
              <option value="">Choose a document…</option>
              {readyDocuments.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.display_name ?? doc.filename}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        {compareError ? <FormError message={compareError} /> : null}
        <div className="flex justify-end">
          <Button
            onClick={() => void compare()}
            disabled={!documentA || !documentB || documentA === documentB}
            loading={comparing}
          >
            <ArrowRightLeft className="size-4" aria-hidden="true" />
            Compare
          </Button>
        </div>
      </section>

      {comparisonId ? <ChangesSection comparisonId={comparisonId} /> : null}
    </div>
  );
}

function ChangesSection({ comparisonId }: { comparisonId: string }) {
  const { loading, data, error, retry } = useApiData<ComparisonChangesData>(
    `/comparisons/${comparisonId}/changes`,
    4000,
  );

  if (loading) return <SkeletonList rows={4} />;

  if (error) {
    return (
      <ErrorState
        title="The comparison is not ready yet"
        message={`${error} Differences will appear here once the comparison has finished.`}
        onRetry={retry}
      />
    );
  }

  const changes = data?.changes ?? [];

  if (changes.length === 0) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="No differences found"
        description="The two documents appear to be identical in the sections we compared."
      />
    );
  }

  return (
    <section aria-labelledby="changes-heading" className="flex flex-col gap-4">
      <h2 id="changes-heading" className="text-lg font-semibold tracking-tight text-navy">
        Differences ({changes.length})
      </h2>
      {changes.map((change, index) => (
        <ChangeCard key={index} change={change} />
      ))}
    </section>
  );
}

function ChangeCard({ change }: { change: ChangeOut }) {
  const sourceA = change.citation_a
    ? [
        "Version A",
        formatSource(change.citation_a),
      ]
        .filter(Boolean)
        .join(" · ")
    : null;
  const sourceB = change.citation_b
    ? ["Version B", formatSource(change.citation_b)]
        .filter(Boolean)
        .join(" · ")
    : null;

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-semibold text-navy">{change.section}</p>
            {change.clause ? <p className="text-sm text-muted">{change.clause}</p> : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ChangeBadge type={change.type} />
            {change.importance ? (
              <span className="rounded-full border border-line bg-canvas px-2.5 py-0.5 text-xs font-medium text-muted">
                {change.importance} importance
              </span>
            ) : null}
          </div>
        </div>

        {change.type !== "UNCHANGED" && (change.before !== null || change.after !== null) ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {change.before !== null ? (
              <div className="rounded-lg border-l-4 border-red-200 bg-red-50/50 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-danger-strong">Before</p>
                <p className="mt-1 text-sm leading-relaxed">
                  {change.before || <span className="italic text-muted">(absent)</span>}
                </p>
              </div>
            ) : null}
            {change.after !== null ? (
              <div className="rounded-lg border-l-4 border-green-200 bg-green-50/50 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-success">After</p>
                <p className="mt-1 text-sm leading-relaxed">
                  {change.after || <span className="italic text-muted">(absent)</span>}
                </p>
              </div>
            ) : null}
          </div>
        ) : null}

        <p className="text-[15px] leading-relaxed">{change.explanation}</p>

        {sourceA || sourceB ? (
          <p className="text-xs text-muted">
            {[sourceA, sourceB].filter(Boolean).join(" · ")}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}