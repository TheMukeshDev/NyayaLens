"use client";

import { useState } from "react";
import { ListChecks } from "lucide-react";

import { ActionCard } from "@/components/actions/action-card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Field, Select } from "@/components/ui/field";
import { SkeletonList } from "@/components/ui/skeleton";
import { clientJson } from "@/lib/api/client";
import { ACTION_STATUS_LABELS } from "@/lib/constants";
import type { ActionOut, ActionStatus, Priority } from "@/lib/types";
import { useApiData } from "@/lib/use-api-data";

const DEFAULT_STATUS_FILTER: ActionStatus | "ALL" = "ALL";
const DEFAULT_PRIORITY_FILTER: Priority | "ALL" = "ALL";

const STATUS_FILTERS: (ActionStatus | "ALL")[] = [
  "ALL",
  "TODO",
  "IN_PROGRESS",
  "COMPLETED",
  "DISMISSED",
];

export function ActionsBoardView() {
  const { loading, data, error, retry } = useApiData<ActionOut[] | { items: ActionOut[] }>(
    "/actions",
  );
  const [statusFilter, setStatusFilter] = useState<ActionStatus | "ALL">(DEFAULT_STATUS_FILTER);
  const [priorityFilter, setPriorityFilter] = useState<Priority | "ALL">(DEFAULT_PRIORITY_FILTER);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actions, setActions] = useState<ActionOut[] | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const allActions = actions ?? (Array.isArray(data) ? data : (data?.items as ActionOut[] | undefined) ?? []);
  const filtered = allActions.filter(
    (action) =>
      (statusFilter === "ALL" || action.status === statusFilter) &&
      (priorityFilter === "ALL" || action.priority === priorityFilter),
  );

  async function updateStatus(action: ActionOut, status: ActionStatus) {
    setBusyId(action.id);
    setUpdateError(null);
    const result = await clientJson<ActionOut>(`/actions/${action.id}`, "PATCH", { status });
    setBusyId(null);
    if (!result.ok) {
      setUpdateError(result.error?.message ?? "Could not update this action.");
      return;
    }
    const updated = result.data;
    setActions((current) => {
      const base =
        current ??
        (Array.isArray(data) ? data : (data?.items as ActionOut[] | undefined) ?? []);
      return base.map((item) => (item.id === action.id ? (updated ?? item) : item));
    });
  }

  function toggleStatusFilter(next: ActionStatus | "ALL") {
    setStatusFilter((current) => (current === next ? DEFAULT_STATUS_FILTER : next));
  }

  if (loading && !actions) return <SkeletonList rows={4} />;

  if (error && !actions) {
    return (
      <ErrorState
        title="Your actions are not available"
        message={`${error} Your action plan items will appear here across all documents.`}
        onRetry={retry}
      />
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <h2 className="sr-only">All actions</h2>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-1 rounded-xl border border-line bg-surface p-1">
          {STATUS_FILTERS.map((filter) => {
            const active = statusFilter === filter;
            return (
              <button
                key={filter}
                type="button"
                aria-pressed={active}
                onClick={() => toggleStatusFilter(filter)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  active ? "bg-navy text-white" : "text-muted hover:text-navy"
                }`}
              >
                {filter === "ALL" ? "All" : ACTION_STATUS_LABELS[filter]}
              </button>
            );
          })}
        </div>
        <Field label="Priority" htmlFor="action-priority">
          <Select
            id="action-priority"
            value={priorityFilter}
            onChange={(event) => setPriorityFilter((event.target.value as Priority | "ALL") || "ALL")}
          >
            <option value="ALL">All priorities</option>
            <option value="HIGH">High priority</option>
            <option value="MEDIUM">Medium priority</option>
            <option value="LOW">Low priority</option>
          </Select>
        </Field>
      </div>

      {updateError ? (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-danger-strong">
          {updateError}
        </p>
      ) : null}

      {filtered.length === 0 ? (
        <EmptyState
          icon={ListChecks}
          title={allActions.length === 0 ? "No actions yet" : "No actions match these filters"}
          description={
            allActions.length === 0
              ? "Generate an action plan from any reviewed document to see a board of practical next steps here."
              : "Try a different status or priority filter."
          }
          action={
            allActions.length === 0 ? (
              <Button href="/upload">Upload a document</Button>
            ) : undefined
          }
        />
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              busy={busyId === action.id}
              documentLabel={`Doc ${action.document_id.slice(0, 8)}`}
              onStatus={(status) => void updateStatus(action, status)}
            />
          ))}
        </div>
      )}
    </div>
  );
}