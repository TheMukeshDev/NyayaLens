"use client";

import { useCallback, useEffect, useState } from "react";

import { clientApi } from "@/lib/api/client";

/** Fetches API data in the browser with loading/data/error + retry. */
export function useApiData<T>(path: string | null, refreshIntervalMs?: number) {
  const [loading, setLoading] = useState(path !== null);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!path) return;
    let active = true;

    async function run() {
      const result = await clientApi<T>(path as string);
      if (!active) return;
      setLoading(false);
      if (result.ok) {
        setData(result.data);
        setError(null);
      } else {
        setData(null);
        setError(result.error?.message ?? "Something went wrong. Please try again.");
      }
    }

    void run();
    if (refreshIntervalMs) {
      const id = setInterval(() => run(), refreshIntervalMs);
      return () => {
        active = false;
        clearInterval(id);
      };
    }
    return () => {
      active = false;
    };
  }, [path, tick, refreshIntervalMs]);

  const retry = useCallback(() => setTick((value) => value + 1), []);

  return { loading, data, error, retry };
}