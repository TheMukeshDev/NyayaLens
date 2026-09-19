"use client";

import Link from "next/link";
import { AlertTriangle, BookOpenText, MessageSquare, ScrollText } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonText } from "@/components/ui/skeleton";
import type { DocumentOut, UnderstandingSummary } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

const NEXT_STEPS = [
  {
    href: "summary",
    label: "Read the summary",
    description: "A plain-language overview of what the document says.",
    icon: BookOpenText,
  },
  {
    href: "clauses",
    label: "Review clauses",
    description: "Detailed explanations of each clause with sources.",
    icon: ScrollText,
  },
  {
    href: "attention",
    label: "View attention items",
    description: "Areas worth reviewing carefully before you decide.",
    icon: AlertTriangle,
  },
  {
    href: "ask",
    label: "Ask about this document",
    description: "Get document-grounded answers with verifiable citations.",
    icon: MessageSquare,
  },
];

export function OverviewView({ document }: { document: DocumentOut }) {
  const { loading, data, error, retry } = useApiData<Partial<UnderstandingSummary>>(
    `/documents/${document.id}/summary`,
  );

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle as="h2">About this document</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {loading ? (
            <>
              <SkeletonText className="h-16" />
              <SkeletonText className="h-4 w-3/4" />
            </>
          ) : error ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-muted">
                The overview is not available yet. It will appear here once the
                document analysis has been generated.
              </p>
              <button
                type="button"
                onClick={retry}
                className="w-fit text-sm font-medium text-brand hover:underline"
              >
                Try again
              </button>
            </div>
          ) : data?.purpose || data?.overview ? (
            <>
              <p className="text-[15px] leading-relaxed">{data.purpose ?? data.overview}</p>
              {data.parties && data.parties.length > 0 ? (
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">
                    Parties
                  </h3>
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {data.parties.map((party, index) => (
                      <li
                        key={index}
                        className="rounded-md border border-line bg-canvas px-3 py-1 text-sm text-ink"
                      >
                        {party}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {data.key_terms && data.key_terms.length > 0 ? (
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">
                    Key terms
                  </h3>
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {data.key_terms.map((term, index) => (
                      <li
                        key={index}
                        className="rounded-md bg-blue-50 px-3 py-1 text-sm text-brand"
                      >
                        {term}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-muted">
              No summary has been generated for this document yet.
            </p>
          )}
        </CardContent>
      </Card>

      <section aria-labelledby="next-steps-heading">
        <h2 id="next-steps-heading" className="text-lg font-semibold tracking-tight text-navy">
          Continue reviewing
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {NEXT_STEPS.map((step) => {
            const Icon = step.icon;
            return (
              <Card
                key={step.href}
                className="transition-colors hover:border-brand/40"
              >
                <Link href={`/documents/${document.id}/${step.href}`} className="flex h-full flex-col gap-2 p-5">
                  <Icon className="size-5 text-brand" aria-hidden="true" />
                  <span className="font-semibold text-navy">{step.label}</span>
                  <span className="text-sm text-muted">{step.description}</span>
                </Link>
              </Card>
            );
          })}
        </div>
      </section>
    </div>
  );
}