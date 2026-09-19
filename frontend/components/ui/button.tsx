import Link from "next/link";
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

import { Spinner } from "@/components/ui/spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "danger-outline";
type Size = "sm" | "md" | "lg";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-brand text-white hover:bg-blue-700 active:bg-blue-800 disabled:bg-blue-300",
  secondary:
    "border border-line bg-surface text-ink hover:bg-canvas active:bg-slate-100 disabled:text-muted",
  ghost: "text-ink hover:bg-canvas active:bg-slate-100 disabled:text-muted",
  danger: "bg-danger text-white hover:bg-red-700 active:bg-red-800 disabled:bg-red-300",
  "danger-outline":
    "border border-red-200 bg-surface text-danger-strong hover:bg-red-50 active:bg-red-100 disabled:text-red-300",
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "h-8 gap-1.5 rounded-md px-3 text-sm",
  md: "h-10 gap-2 rounded-lg px-4 text-sm",
  lg: "h-12 gap-2 rounded-xl px-5 text-base",
};

function baseClasses(variant: Variant, size: Size, loading: boolean): string {
  return [
    "inline-flex items-center justify-center font-medium transition-colors",
    "disabled:cursor-not-allowed disabled:opacity-60",
    loading ? "cursor-wait" : "",
    VARIANT_CLASSES[variant],
    SIZE_CLASSES[size],
  ]
    .filter(Boolean)
    .join(" ");
}

type ButtonBaseProps = {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  children: ReactNode;
};

type ButtonAsButton = ButtonBaseProps &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
    href?: undefined;
  };

type ButtonAsLink = ButtonBaseProps &
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "children"> & {
    href: string;
  };

type ButtonProps = ButtonAsButton | ButtonAsLink;

export function Button(props: ButtonProps) {
  // UI-only props are destructured here so they are never forwarded to the
  // rendered <button>/<Link> as invalid DOM attributes.
  const {
    variant = "primary",
    size = "md",
    loading = false,
    className,
    children,
    ...rest
  } = props;

  const classes = `${baseClasses(variant, size, loading)} ${className ?? ""}`;

  if (props.href !== undefined) {
    const { href, ...linkProps } = rest as ButtonAsLink;
    return (
      <Link href={href} className={classes} aria-busy={loading || undefined} {...linkProps}>
        {loading ? <Spinner size={16} /> : null}
        {children}
      </Link>
    );
  }

  const { type = "button", ...buttonProps } = rest as ButtonAsButton;
  return (
    <button
      type={type}
      className={classes}
      aria-busy={loading || undefined}
      disabled={loading || buttonProps.disabled}
      {...buttonProps}
    >
      {loading ? <Spinner size={16} /> : null}
      {children}
    </button>
  );
}
