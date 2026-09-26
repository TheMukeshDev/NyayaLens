import { NextResponse } from "next/server";

import { handleDemoRequest, type DemoHttpResponse } from "@/lib/demo/api";
import { isDemoMode } from "@/lib/supabase/config";

/**
 * Demo-mode API surface.
 *
 * The browser has no way to import the in-memory demo workspace from
 * `lib/demo/api` — that module lives in the server graph only, and the Server
 * Components need the same state the Client Components mutate. This catch-all
 * is the seam between the two: `lib/api/client.ts` rewrites the call to
 * `/api/demo/...` and everything else stays exactly as it is.
 *
 * It only exists while demo mode is on, and it never touches the network.
 */

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ path?: string[] }> };

function respond(result: DemoHttpResponse) {
  if (result.raw) {
    return new NextResponse(String(result.body), {
      status: result.status,
      headers: { "Content-Type": result.contentType ?? "text/plain; charset=utf-8" },
    });
  }
  return NextResponse.json(result.body, { status: result.status });
}

async function handle(
  request: Request,
  context: RouteContext,
  method: string,
): Promise<NextResponse> {
  if (!isDemoMode()) {
    return NextResponse.json(
      {
        success: false,
        error: {
          code: "NOT_FOUND",
          message: "The demo API is only available when demo mode is enabled.",
          details: null,
        },
      },
      { status: 404 },
    );
  }

  const { path = [] } = await context.params;
  const url = new URL(request.url);

  let body: unknown;
  if (method !== "GET" && method !== "HEAD") {
    const raw = await request.text();
    if (raw) {
      try {
        body = JSON.parse(raw);
      } catch {
        body = undefined;
      }
    }
  }

  return respond(handleDemoRequest(method, `/${path.join("/")}${url.search}`, body));
}

export async function GET(request: Request, context: RouteContext) {
  return handle(request, context, "GET");
}

export async function POST(request: Request, context: RouteContext) {
  return handle(request, context, "POST");
}

export async function PATCH(request: Request, context: RouteContext) {
  return handle(request, context, "PATCH");
}

export async function DELETE(request: Request, context: RouteContext) {
  return handle(request, context, "DELETE");
}
