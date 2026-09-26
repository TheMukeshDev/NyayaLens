import { isDemoMode } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/client";

import { apiRequest, authFailure, demoRequest, type ApiResult } from "./shared";

async function sessionToken(): Promise<string | null> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/**
 * Browser-side API call with the user's current session token.
 *
 * In demo mode there is no session and no backend, so the call is served by the
 * in-app demo API instead. Without this branch every screen that fetches data
 * would resolve to `authFailure()` and render "Your session has expired".
 */
export async function clientApi<T>(path: string, init: RequestInit = {}): Promise<ApiResult<T>> {
  if (isDemoMode()) {
    return demoRequest<T>(path, init);
  }
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
  return clientApi<T>(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
