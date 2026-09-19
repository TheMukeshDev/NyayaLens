import type { ReactNode } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Circle,
  CircleDashed,
  Clock,
  Info,
  Loader2,
  Minus,
  Pencil,
  Plus,
  XCircle,
} from "lucide-react";

import { ACTION_STATUS_LABELS, ATTENTION_LEVEL_LABELS } from "@/lib/constants";
import type {
  ActionStatus,
  AttentionLevel,
  ChangeType,
  DocumentStatus,
  EvidenceState,
  Priority,
} from "@/lib/types";

import { Badge } from "./badge";

type Tone = "neutral" | "brand" | "navy" | "success" | "warning" | "danger";

function Status({ tone, icon, label }: { tone: Tone; icon: ReactNode; label: string }) {
  return (
    <Badge tone={tone}>
      {icon}
      <span className="whitespace-nowrap">{label}</span>
    </Badge>
  );
}

/* ---------- Document processing status ---------- */

const DOCUMENT_STATUS_ICONS: Record<DocumentStatus, { tone: Tone; icon: ReactNode }> = {
  UPLOADED: { tone: "neutral", icon: <Circle className="size-3.5" aria-hidden="true" /> },
  VALIDATING: { tone: "brand", icon: <Loader2 className="size-3.5 animate-spin" aria-hidden="true" /> },
  PROCESSING: { tone: "brand", icon: <Loader2 className="size-3.5 animate-spin" aria-hidden="true" /> },
  EXTRACTING: { tone: "brand", icon: <Loader2 className="size-3.5 animate-spin" aria-hidden="true" /> },
  ANALYZING: { tone: "brand", icon: <Loader2 className="size-3.5 animate-spin" aria-hidden="true" /> },
  READY: { tone: "success", icon: <CheckCircle2 className="size-3.5" aria-hidden="true" /> },
  FAILED: { tone: "danger", icon: <XCircle className="size-3.5" aria-hidden="true" /> },
};

const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  UPLOADED: "Uploaded",
  VALIDATING: "Validating",
  PROCESSING: "Processing",
  EXTRACTING: "Extracting",
  ANALYZING: "Analyzing",
  READY: "Ready",
  FAILED: "Failed",
};

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  const { tone, icon } = DOCUMENT_STATUS_ICONS[status] ?? DOCUMENT_STATUS_ICONS.UPLOADED;
  return <Status tone={tone} icon={icon} label={DOCUMENT_STATUS_LABELS[status] ?? status} />;
}

/* ---------- Evidence state ---------- */

const EVIDENCE_META: Record<EvidenceState, { tone: Tone; icon: ReactNode; label: string }> = {
  "DOCUMENT-GROUNDED": {
    tone: "success",
    icon: <CheckCircle2 className="size-3.5" aria-hidden="true" />,
    label: "Document-grounded",
  },
  "GENERAL-INFORMATION": {
    tone: "warning",
    icon: <Info className="size-3.5" aria-hidden="true" />,
    label: "General information",
  },
  "INSUFFICIENT-EVIDENCE": {
    tone: "danger",
    icon: <AlertTriangle className="size-3.5" aria-hidden="true" />,
    label: "Insufficient evidence",
  },
};

export function EvidenceBadge({ state }: { state: EvidenceState }) {
  const meta = EVIDENCE_META[state];
  if (!meta) return null;
  return <Status tone={meta.tone} icon={meta.icon} label={meta.label} />;
}

/* ---------- Attention level ---------- */

const ATTENTION_META: Record<AttentionLevel, { tone: Tone; icon: ReactNode }> = {
  LOW: { tone: "neutral", icon: <Info className="size-3.5" aria-hidden="true" /> },
  MEDIUM: { tone: "warning", icon: <AlertCircle className="size-3.5" aria-hidden="true" /> },
  HIGH: { tone: "danger", icon: <AlertTriangle className="size-3.5" aria-hidden="true" /> },
};

export function AttentionBadge({ level }: { level: AttentionLevel }) {
  const meta = ATTENTION_META[level];
  if (!meta) return null;
  return (
    <Status
      tone={meta.tone}
      icon={meta.icon}
      label={ATTENTION_LEVEL_LABELS[level] ?? level}
    />
  );
}

/* ---------- Action status ---------- */

const ACTION_STATUS_META: Record<ActionStatus, { tone: Tone; icon: ReactNode }> = {
  TODO: { tone: "neutral", icon: <Circle className="size-3.5" aria-hidden="true" /> },
  IN_PROGRESS: { tone: "brand", icon: <Clock className="size-3.5" aria-hidden="true" /> },
  COMPLETED: { tone: "success", icon: <CheckCircle2 className="size-3.5" aria-hidden="true" /> },
  DISMISSED: { tone: "neutral", icon: <CircleDashed className="size-3.5" aria-hidden="true" /> },
};

export function ActionStatusBadge({ status }: { status: ActionStatus }) {
  const meta = ACTION_STATUS_META[status];
  if (!meta) return null;
  return (
    <Status tone={meta.tone} icon={meta.icon} label={ACTION_STATUS_LABELS[status] ?? status} />
  );
}

/* ---------- Priority ---------- */

const PRIORITY_META: Record<Priority, { tone: Tone; icon: ReactNode; label: string }> = {
  HIGH: { tone: "danger", icon: <AlertTriangle className="size-3.5" aria-hidden="true" />, label: "High priority" },
  MEDIUM: { tone: "warning", icon: <AlertCircle className="size-3.5" aria-hidden="true" />, label: "Medium priority" },
  LOW: { tone: "neutral", icon: <Info className="size-3.5" aria-hidden="true" />, label: "Low priority" },
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  const meta = PRIORITY_META[priority];
  if (!meta) return null;
  return <Status tone={meta.tone} icon={meta.icon} label={meta.label} />;
}

/* ---------- Comparison changes ---------- */

const CHANGE_META: Record<ChangeType, { tone: Tone; icon: ReactNode; label: string }> = {
  ADDED: { tone: "success", icon: <Plus className="size-3.5" aria-hidden="true" />, label: "Added" },
  REMOVED: { tone: "danger", icon: <Minus className="size-3.5" aria-hidden="true" />, label: "Removed" },
  MODIFIED: { tone: "warning", icon: <Pencil className="size-3.5" aria-hidden="true" />, label: "Modified" },
  UNCHANGED: { tone: "neutral", icon: <Circle className="size-3.5" aria-hidden="true" />, label: "Unchanged" },
};

export function ChangeBadge({ type }: { type: ChangeType }) {
  const meta = CHANGE_META[type];
  if (!meta) return null;
  return <Status tone={meta.tone} icon={meta.icon} label={meta.label} />;
}

/* ---------- Reports ---------- */

const REPORT_STATUS_META: Record<string, { tone: Tone; icon: ReactNode }> = {
  PROCESSING: { tone: "brand", icon: <Loader2 className="size-3.5 animate-spin" aria-hidden="true" /> },
  READY: { tone: "success", icon: <CheckCircle2 className="size-3.5" aria-hidden="true" /> },
  FAILED: { tone: "danger", icon: <XCircle className="size-3.5" aria-hidden="true" /> },
  ERROR: { tone: "danger", icon: <XCircle className="size-3.5" aria-hidden="true" /> },
};

const REPORT_STATUS_LABELS: Record<string, string> = {
  PROCESSING: "Generating",
  READY: "Ready",
  FAILED: "Failed",
  ERROR: "Failed",
};

export function ReportStatusBadge({ status }: { status: string }) {
  const meta = REPORT_STATUS_META[status];
  if (!meta) return null;
  return <Status tone={meta.tone} icon={meta.icon} label={REPORT_STATUS_LABELS[status] ?? status} />;
}