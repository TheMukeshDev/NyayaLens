import { AttentionView } from "@/components/analysis/attention-view";
import { loadDocument } from "@/lib/document-page";

export const metadata = { title: "Attention" };

export default async function DocumentAttentionPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const document = await loadDocument(documentId, { requireReady: true });
  return <AttentionView document={document} />;
}