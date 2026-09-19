import { ReportsView } from "@/components/reports/reports-view";

export const metadata = { title: "Reports" };

export default function ReportsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-navy">Reports</h1>
        <p className="max-w-2xl text-base text-muted">
          Download review reports generated from your documents.
        </p>
      </div>
      <ReportsView />
    </div>
  );
}