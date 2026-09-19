import { redirect } from "next/navigation";

import { ProcessingView } from "@/components/documents/processing-view";
import { serverApi } from "@/lib/api/server";
import type { DocumentOut } from "@/lib/types";

export const metadata = { title: "Processing" };

export default async function ProcessingPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const result = await serverApi<DocumentOut>(`/documents/${documentId}`);

  if (!result.ok) {
    redirect("/dashboard");
  }

  const document = result.data as DocumentOut;
  if (document.status === "READY") {
    redirect(`/documents/${documentId}`);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-navy">Processing document</h1>
        <p className="max-w-2xl text-base text-muted">
          We are reviewing your document. This usually takes a minute or two.
        </p>
      </div>
      <ProcessingView document={document} />
    </div>
  );
}