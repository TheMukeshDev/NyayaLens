import { createClient } from "@/lib/supabase/client";

import { apiRequest, apiRequestJson, authFailure, type ApiResult } from "./shared";

async function sessionToken(): Promise<string | null> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/** Browser-side API call with the user's current session token. */
export async function clientApi<T>(path: string, init: RequestInit = {}): Promise<ApiResult<T>> {
  const token = await sessionToken();
  if (!token) return authFailure();
  return apiRequest<T>(token, path, init);
}

/** Browser-side JSON call with an optional body. */
export async function clientJson<T>(
  path: string,
  method: "GET" | "POST" | "PATCH" | "DELETE" = "GET",
  body?: unknown,
): Promise<ApiResult<T>> {
  const token = await sessionToken();
  if (!token) return authFailure();
  return apiRequestJson<T>(token, path, method, body);
}