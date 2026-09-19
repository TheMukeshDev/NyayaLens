import { createClient } from "@/lib/supabase/server";

import { apiRequest, apiRequestJson, authFailure, type ApiResult } from "./shared";

async function sessionToken(): Promise<string | null> {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/** Server-side API call (Server Components / Server Actions). */
export async function serverApi<T>(path: string, init: RequestInit = {}): Promise<ApiResult<T>> {
  const token = await sessionToken();
  if (!token) return authFailure();
  return apiRequest<T>(token, path, init);
}

/** Server-side JSON call with an optional body. */
export async function serverJson<T>(
  path: string,
  method: "GET" | "POST" | "PATCH" | "DELETE" = "GET",
  body?: unknown,
): Promise<ApiResult<T>> {
  const token = await sessionToken();
  if (!token) return authFailure();
  return apiRequestJson<T>(token, path, method, body);
}