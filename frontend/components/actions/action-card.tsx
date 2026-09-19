"use client";

import { Check, CircleDashed, ListChecks, Play, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ActionStatusBadge, PriorityBadge } from "@/components/ui/status";
import { ACTION_TYPE_LABELS } from "@/lib/constants";
import { formatSource } from "@/lib/format";
import type { ActionOut, ActionStatus } from "@/lib/types";

export function ActionCard({
  action,
  onStatus,
  busy,
  documentLabel,
}: {
  action: ActionOut;
  onStatus: (status: ActionStatus) => void;
  busy: boolean;
  documentLabel?: string | null;
}) {
  const source = formatSource(action.source);

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h3 className="font-semibold text-navy">{action.title}</h3>
          <ActionStatusBadge status={action.status} />
        </div>
        {action.description ? <p className="text-sm text-muted">{action.description}</p> : null}
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
          <span className="inline-flex items-center gap-1.5">
            <ListChecks className="size-3.5" aria-hidden="true" />
            {ACTION_TYPE_LABELS[action.action_type] ?? action.action_type}
          </span>
          <PriorityBadge priority={action.priority} />
          {documentLabel ? <span>{documentLabel}</span> : null}
          {source ? <span className="text-muted">{source}</span> : null}
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          {action.status === "TODO" ? (
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => onStatus("IN_PROGRESS")}>
              <Play className="size-3.5" aria-hidden="true" />
              Start
            </Button>
          ) : null}
          {action.status === "IN_PROGRESS" ? (
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => onStatus("TODO")}>
              <RotateCcw className="size-3.5" aria-hidden="true" />
              Back to to do
            </Button>
          ) : null}
          {action.status === "DISMISSED" || action.status === "COMPLETED" ? (
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus("IN_PROGRESS")}>
              <RotateCcw className="size-3.5" aria-hidden="true" />
              Reopen
            </Button>
          ) : null}
          {action.status !== "COMPLETED" ? (
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => onStatus("COMPLETED")}>
              <Check className="size-3.5" aria-hidden="true" />
              Complete
            </Button>
          ) : null}
          {action.status !== "DISMISSED" ? (
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus("DISMISSED")}>
              <CircleDashed className="size-3.5" aria-hidden="true" />
              Dismiss
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}