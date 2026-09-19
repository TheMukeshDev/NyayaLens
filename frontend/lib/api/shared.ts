import type { ApiError, SuccessResponse } from "@/lib/types";

export const API_BASE = "/api/v1";

export interface ApiResult<T> {
  ok: boolean;
  status: number;
  data: T | null;
  message: string | null;
  error: ApiError | null;
}

export function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_URL ?? "").trim().replace(/\/+$/, "");
}

/** Parses the standard backend envelope, never throwing on bad responses. */
export async function parseApiResponse<T>(response: Response): Promise<ApiResult<T>> {
  const body = (await response.json().catch(() => null)) as
    | ({ success?: boolean } & Partial<SuccessResponse<T>> & { error?: undefined })
    | ({ success?: false } & { error?: ApiError })
    | null;

  if (response.ok && body && body.success === true) {
    return {
      ok: true,
      status: response.status,
      data: (body as SuccessResponse<T>).data,
      message: (body as SuccessResponse<T>).message ?? null,
      error: null,
    };
  }

  const error: ApiError =
    body && !body.success && (body as { error?: ApiError }).error
      ? (body as { error: ApiError }).error
      : response.status === 0
        ? { code: "NETWORK_ERROR", message: "Could not reach the backend API.", details: null }
        : {
            code: "INTERNAL_ERROR",
            message: `The service responded unexpectedly (${response.status}).`,
            details: null,
          };

  return { ok: false, status: response.status, data: null, message: null, error };
}

/** The caller supplies an access token; both server and client use this. */
export async function apiRequest<T>(
  token: string,
  path: string,
  init: RequestInit = {},
): Promise<ApiResult<T>> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body != null && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${apiBase()}${API_BASE}${path}`, {
      ...init,
      headers,
      cache: init.cache ?? "no-store",
    });
  } catch {
    return {
      ok: false,
      status: 0,
      data: null,
      message: null,
      error: {
        code: "NETWORK_ERROR",
        message: "Could not reach the backend service. Please try again in a moment.",
        details: null,
      },
    };
  }
  return parseApiResponse<T>(response);
}

export function apiRequestJson<T>(
  token: string,
  path: string,
  method: "GET" | "POST" | "PATCH" | "DELETE" = "GET",
  body?: unknown,
): Promise<ApiResult<T>> {
  return apiRequest<T>(token, path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export function authFailure(): ApiResult<never> {
  return {
    ok: false,
    status: 401,
    data: null,
    message: null,
    error: { code: "AUTH_REQUIRED", message: "Your session has expired. Please log in again.", details: null },
  };
}