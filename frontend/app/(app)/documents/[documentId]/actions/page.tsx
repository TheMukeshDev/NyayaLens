import { ActionsView } from "@/components/actions/actions-view";
import { loadDocument } from "@/lib/document-page";

export const metadata = { title: "Action Center" };

export default async function DocumentActionsPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const document = await loadDocument(documentId, { requireReady: true });
  return <ActionsView document={document} />;
}