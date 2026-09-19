import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

type EmptyStateProps = {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
};

/** Standard empty state (Screen-Spec §20): icon, message, and a clear next step. */
export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line bg-canvas/50 px-6 py-12 text-center">
      {Icon ? (
        <Icon className="size-8 text-muted" aria-hidden="true" />
      ) : null}
      <h3 className="text-base font-semibold text-navy">{title}</h3>
      {description ? <p className="max-w-md text-sm text-muted">{description}</p> : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}