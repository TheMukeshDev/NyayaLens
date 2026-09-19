import type { ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";

type Kind = "info" | "success" | "warning" | "error";

const KIND_META: Record<Kind, { icon: typeof Info; classes: string }> = {
  info: { icon: Info, classes: "border-blue-200 bg-blue-50 text-navy" },
  success: { icon: CheckCircle2, classes: "border-green-200 bg-green-50 text-success" },
  warning: { icon: TriangleAlert, classes: "border-amber-200 bg-amber-50 text-warning" },
  error: { icon: AlertCircle, classes: "border-red-200 bg-red-50 text-danger-strong" },
};

type AlertProps = {
  kind?: Kind;
  title?: string;
  className?: string;
  children: ReactNode;
  action?: ReactNode;
};

export function Alert({ kind = "info", title, className, children, action }: AlertProps) {
  const meta = KIND_META[kind];
  const Icon = meta.icon;
  return (
    <div
      role={kind === "error" ? "alert" : "status"}
      className={`rounded-xl border p-4 ${meta.classes} ${className ?? ""}`}
    >
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          {title ? <p className="font-semibold">{title}</p> : null}
          <div className="text-sm leading-relaxed">{children}</div>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </div>
  );
}