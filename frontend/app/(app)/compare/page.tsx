import { CompareView } from "@/components/compare/compare-view";

export const metadata = { title: "Compare Documents" };

export default function ComparePage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-navy">Compare documents</h1>
        <p className="max-w-2xl text-base text-muted">
          See exactly what changed between two versions of a document, with
          before-and-after text and explanations for each change.
        </p>
      </div>
      <CompareView />
    </div>
  );
}