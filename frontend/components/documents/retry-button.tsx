"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { clientJson } from "@/lib/api/client";
import type { DocumentOut } from "@/lib/types";

/** Retries processing for a FAILED document; handshake with the retry endpoint. */
export function RetryButton({ document }: { document: DocumentOut }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRetry() {
    setLoading(true);
    setError(null);
    const result = await clientJson<DocumentOut>(
      `/documents/${document.id}/retry`,
      "POST",
    );
    if (result.ok) {
      router.refresh();
      return;
    }
    setError(result.error?.message ?? "Could not retry this document right now.");
    setLoading(false);
  }

  return (
    <span className="inline-flex items-center gap-2">
      <Button
        variant="ghost"
        size="sm"
        onClick={handleRetry}
        loading={loading}
        className="text-danger-strong"
      >
        <RotateCw className="size-3.5" aria-hidden="true" />
        Retry
      </Button>
      {error ? <span role="alert" className="text-sm text-danger-strong">{error}</span> : null}
    </span>
  );
}