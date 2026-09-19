import { OverviewView } from "@/components/analysis/overview-view";
import { loadDocument } from "@/lib/document-page";

export const metadata = { title: "Document Overview" };

export default async function DocumentOverviewPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const document = await loadDocument(documentId, { requireReady: true });
  return <OverviewView document={document} />;
}