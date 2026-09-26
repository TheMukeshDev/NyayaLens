import { handleDemoRequest } from "@/lib/demo/api";
import { isDemoMode } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

import { apiRequest, authFailure, type ApiResult } from "./shared";

async function sessionToken(): Promise<string | null> {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/** Reads a JSON body off a `RequestInit`, ignoring anything non-JSON. */
function parseBody(body: BodyInit | null | undefined): unknown {
  if (typeof body !== "string" || !body) return undefined;
  try {
    return JSON.parse(body) as unknown;
  } catch {
    return undefined;
  }
}

/**
 * Server-side API call (Server Components / Server Actions).
 *
 * In demo mode this calls the demo router in-process instead of over HTTP, so a
 * Server Component and the Client Components below it read and write the same
 * workspace.
 */
export async function serverApi<T>(path: string, init: RequestInit = {}): Promise<ApiResult<T>> {
  if (isDemoMode()) {
    return demoResult(handleDemoRequest(init.method ?? "GET", path, parseBody(init.body)));
  }
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
  return serverApi<T>(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** Adapts a demo response to the same envelope shape as a real API call. */
function demoResult<T>(result: ReturnType<typeof handleDemoRequest>): ApiResult<T> {
  const body = result.body as
    | { success: boolean; data?: T; message?: string | null; error?: { code: string; message: string; details: string[] | null } }
    | null;

  if (result.status >= 200 && result.status < 300 && body?.success) {
    return {
      ok: true,
      status: result.status,
      data: (body.data ?? null) as T,
      message: body.message ?? null,
      error: null,
    };
  }

  return {
    ok: false,
    status: result.status,
    data: null,
    message: null,
    error: body?.error ?? {
      code: "INTERNAL_ERROR",
      message: `The service responded unexpectedly (${result.status}).`,
      details: null,
    },
  };
}
