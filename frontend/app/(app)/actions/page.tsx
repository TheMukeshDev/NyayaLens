import { ActionsBoardView } from "@/components/actions/actions-board-view";

export const metadata = { title: "Actions" };

export default function ActionsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-navy">Actions</h1>
        <p className="max-w-2xl text-base text-muted">
          Track practical next steps from your document reviews across all
          documents.
        </p>
      </div>
      <ActionsBoardView />
    </div>
  );
}