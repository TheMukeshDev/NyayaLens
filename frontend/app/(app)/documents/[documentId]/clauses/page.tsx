import { ClausesView } from "@/components/analysis/clauses-view";
import { loadDocument } from "@/lib/document-page";

export const metadata = { title: "Clauses" };

export default async function DocumentClausesPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const document = await loadDocument(documentId, { requireReady: true });
  return <ClausesView document={document} />;
}