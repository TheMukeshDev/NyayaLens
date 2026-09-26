import type { ReactNode } from "react";
import { FileQuestion, GitCompare, ListChecks, MessageSquare, UploadCloud } from "lucide-react";

import { DocumentCard } from "@/components/documents/document-card";
import { ProcessingCard } from "@/components/documents/processing-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { serverApi } from "@/lib/api/server";
import type { DocumentListData, DocumentStatusData } from "@/lib/types";
import { isDemoMode } from "@/lib/supabase/config";

export const metadata = { title: "Dashboard" };

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle as="h2">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">{children}</CardContent>
    </Card>
  );
}

export default async function DashboardPage() {
  const documentsResult = isDemoMode() ? null : await serverApi<DocumentListData>("/documents");
  const documents = documentsResult?.ok && documentsResult.data ? documentsResult.data.items : [];
  const errored = documentsResult ? !documentsResult.ok && documentsResult.status !== 0 : false;
  const authMismatch = documentsResult?.status === 401;
  const recent = documents.slice(0, 6);
  const processing = documents.filter(
    (doc) => doc.status !== "READY" && doc.status !== "FAILED",
  );

  const statuses =
    processing.length > 0
      ? await Promise.all(
          processing.map(async (doc) => {
            const result = await serverApi<DocumentStatusData>(`/documents/${doc.id}/status`);
            return { id: doc.id, status: result.ok ? result.data : null };
          }),
        )
      : [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-navy">Welcome back</h1>
        <p className="max-w-2xl text-base text-muted">
          Review your documents, track attention items, and turn insights into
          practical next steps.
        </p>
      </div>

      {/* Recent Documents */}
      <Section
        title="Recent documents"
        description="Documents you have uploaded are kept private to your account."
      >
        {recent.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2">
            {recent.map((doc) => (
              <DocumentCard key={doc.id} document={doc} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={UploadCloud}
            title={isDemoMode() ? "Demo workspace" : errored ? "We couldn't load your documents" : "No documents yet"}
            description={
              isDemoMode()
                ? "Demo uploads are shown immediately in the upload screen. Connect a real Supabase project to persist documents and run backend processing."
                : authMismatch
                  ? "Your authentication token was rejected by the backend. Use the connection test to verify Supabase and backend configuration."
                : errored
                  ? "The document service is not available right now. Please try again shortly."
                : "Upload your first document to begin reviewing."
            }
            action={
              authMismatch ? (
                <Button href="/connection-test" variant="secondary">Run connection test</Button>
              ) : (
                <Button href="/upload">Upload document</Button>
              )
            }
          />
        )}
      </Section>

      {/* Processing Documents */}
      {processing.length > 0 ? (
        <Section
          title="Processing documents"
          description="We'll let you know when each document is ready to review."
        >
          <div className="grid gap-4 md:grid-cols-2">
            {processing.map((doc) => {
              const status = statuses.find((entry) => entry.id === doc.id)?.status ?? null;
              return <ProcessingCard key={doc.id} document={doc} status={status} />;
            })}
          </div>
        </Section>
      ) : null}

      {/* Attention Items */}
      <Section
        title="Attention items"
        description="Areas worth reviewing are surfaced here once your documents are analyzed."
      >
        <EmptyState
          icon={FileQuestion}
          title="No attention items yet"
          description="Attention items from your document reviews will appear here."
          action={<Button href="/upload" variant="secondary">Upload a document</Button>}
        />
      </Section>

      {/* Recent Questions */}
      <Section
        title="Recent questions"
        description="Answers to questions you ask about your documents."
      >
        <EmptyState
          icon={MessageSquare}
          title="No questions yet"
          description="Ask about any ready document and the question and answer will appear here."
          action={<Button href="/upload" variant="secondary">Ask about a document</Button>}
        />
      </Section>

      {/* Quick Actions */}
      <Section title="Quick actions" description="Common next steps to keep moving.">
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="border-line bg-canvas/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <UploadCloud className="size-4.5 text-brand" aria-hidden="true" />
                Upload document
              </CardTitle>
              <CardDescription>Add a legal document to review.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button href="/upload" variant="secondary" size="sm">
                Upload
              </Button>
            </CardContent>
          </Card>
          <Card className="border-line bg-canvas/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <GitCompare className="size-4.5 text-brand" aria-hidden="true" />
                Compare documents
              </CardTitle>
              <CardDescription>Spot differences between two versions.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button href="/compare" variant="secondary" size="sm">
                Compare
              </Button>
            </CardContent>
          </Card>
          <Card className="border-line bg-canvas/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ListChecks className="size-4.5 text-brand" aria-hidden="true" />
                View actions
              </CardTitle>
              <CardDescription>Track your review checklist and follow-ups.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button href="/actions" variant="secondary" size="sm">
                Open actions
              </Button>
            </CardContent>
          </Card>
        </div>
      </Section>
    </div>
  );
}