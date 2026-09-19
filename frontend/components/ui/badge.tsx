import type { HTMLAttributes } from "react";

type Tone = "neutral" | "brand" | "navy" | "success" | "warning" | "danger";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "border-line bg-canvas text-muted",
  brand: "border-blue-200 bg-blue-50 text-brand",
  navy: "border-slate-200 bg-slate-50 text-navy",
  success: "border-green-200 bg-green-50 text-success",
  warning: "border-amber-200 bg-amber-50 text-warning",
  danger: "border-red-200 bg-red-50 text-danger-strong",
};

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: Tone;
};

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]} ${className ?? ""}`}
      {...props}
    />
  );
}