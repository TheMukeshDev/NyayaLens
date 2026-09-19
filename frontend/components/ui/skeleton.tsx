import type { HTMLAttributes } from "react";

import { Card } from "./card";

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-md bg-slate-200/70 ${className ?? ""}`}
      {...props}
    />
  );
}

export function SkeletonText({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <Skeleton className={`h-3 w-full ${className ?? ""}`} {...props} />;
}

/** Skeleton for a Dashboard-style card (Screen-Spec §22). */
export function SkeletonCard({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <Card className={`p-6 ${className ?? ""}`} {...props}>
      <div className="flex items-center justify-between gap-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <SkeletonText className="mt-4 h-4 w-3/4" />
      <SkeletonText className="mt-2 h-4 w-1/2" />
    </Card>
  );
}

/** Skeleton for the Document overview list (Screen-Spec §22). */
export function SkeletonList({ rows = 3 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-3" aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-14 w-full rounded-xl" />
      ))}
    </div>
  );
}