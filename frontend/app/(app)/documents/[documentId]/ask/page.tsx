import { AskView } from "@/components/ask/ask-view";
import { loadDocument } from "@/lib/document-page";

export const metadata = { title: "Ask" };

export default async function DocumentAskPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const document = await loadDocument(documentId, { requireReady: true });
  return <AskView document={document} />;
}