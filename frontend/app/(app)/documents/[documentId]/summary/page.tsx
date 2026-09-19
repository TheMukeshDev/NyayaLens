import { SummaryView } from "@/components/analysis/summary-view";
import { loadDocument } from "@/lib/document-page";

export const metadata = { title: "Summary" };

export default async function DocumentSummaryPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const document = await loadDocument(documentId, { requireReady: true });
  return <SummaryView document={document} />;
}