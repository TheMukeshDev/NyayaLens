import Link from "next/link";
import { CheckCircle2, CircleAlert, ExternalLink, ShieldCheck, Wifi } from "lucide-react";

import { Logo } from "@/components/logo";
import { isDemoMode, supabaseConfig } from "@/lib/supabase/config";

type CheckResult = {
  name: string;
  status: "connected" | "demo" | "failed" | "not-configured";
  explanation: string;
  detail: string;
};

async function checkBackend(): Promise<CheckResult> {
  const baseUrl = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
  if (!baseUrl) {
    return {
      name: "NyayaLens backend",
      status: "not-configured",
      explanation: "The frontend has no backend URL configured.",
      detail: "Set NEXT_PUBLIC_API_URL to the deployed backend origin.",
    };
  }

  try {
    const response = await fetch(`${baseUrl}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return {
      name: "NyayaLens backend",
      status: "connected",
      explanation: "The frontend can reach the backend health route.",
      detail: `${baseUrl}/health responded with HTTP ${response.status}.`,
    };
  } catch (error) {
    return {
      name: "NyayaLens backend",
      status: "failed",
      explanation: "The frontend cannot reach the configured backend.",
      detail: `${baseUrl}/health failed: ${error instanceof Error ? error.message : "network error"}.`,
    };
  }
}

async function checkSupabase(): Promise<CheckResult> {
  if (isDemoMode()) {
    return {
      name: "Supabase Auth",
      status: "demo",
      explanation: "Demo mode is active, so signup and login use a local seven-day cookie.",
      detail: "No Supabase request is made. Disable NEXT_PUBLIC_DEMO_MODE to test real Supabase Auth.",
    };
  }

  const { url, anonKey } = supabaseConfig();
  if (!url || !anonKey) {
    return {
      name: "Supabase Auth",
      status: "not-configured",
      explanation: "Supabase URL or anon key is missing from the frontend deployment.",
      detail: "Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.",
    };
  }

  try {
    const response = await fetch(`${url.replace(/\/+$/, "")}/auth/v1/settings`, {
      headers: { apikey: anonKey },
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return {
      name: "Supabase Auth",
      status: "connected",
      explanation: "The frontend can reach Supabase Auth.",
      detail: `${url}/auth/v1/settings responded with HTTP ${response.status}.`,
    };
  } catch (error) {
    return {
      name: "Supabase Auth",
      status: "failed",
      explanation: "The configured Supabase Auth endpoint is unreachable.",
      detail: `${url}/auth/v1/settings failed: ${error instanceof Error ? error.message : "network error"}.`,
    };
  }
}

function StatusIcon({ status }: { status: CheckResult["status"] }) {
  if (status === "connected" || status === "demo") {
    return <CheckCircle2 className="size-5 text-success" aria-hidden="true" />;
  }
  return <CircleAlert className="size-5 text-warning" aria-hidden="true" />;
}

export default async function ConnectionTestPage() {
  const checks = await Promise.all([checkSupabase(), checkBackend()]);

  return (
    <main className="min-h-screen bg-canvas px-4 py-10 text-ink sm:px-6 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between">
          <Logo href="/" />
          <Link href="/login" className="text-sm font-medium text-brand hover:underline">
            Back to login
          </Link>
        </div>

        <div className="mt-12">
          <div className="flex items-center gap-3 text-brand">
            <Wifi className="size-5" aria-hidden="true" />
            <span className="text-sm font-semibold">Deployment diagnostics</span>
          </div>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-navy">Connection test</h1>
          <p className="mt-2 max-w-2xl text-muted">
            This page checks each service separately and explains what your current result means.
            It never displays private keys.
          </p>
        </div>

        <div className="mt-8 space-y-4">
          {checks.map((check) => (
            <article key={check.name} className="rounded-xl border border-line bg-surface p-5 shadow-sm">
              <div className="flex items-start gap-3">
                <StatusIcon status={check.status} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h2 className="font-semibold text-navy">{check.name}</h2>
                    <span className="rounded-full bg-canvas px-2.5 py-1 text-xs font-medium uppercase tracking-wide text-muted">
                      {check.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-ink">{check.explanation}</p>
                  <p className="mt-2 wrap-break-word font-mono text-xs leading-5 text-muted">{check.detail}</p>
                </div>
              </div>
            </article>
          ))}
        </div>

        <section className="mt-6 rounded-xl border border-blue-100 bg-blue-50 p-5">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 size-5 shrink-0 text-brand" aria-hidden="true" />
            <div>
              <h2 className="font-semibold text-navy">How to read this result</h2>
              <p className="mt-2 text-sm leading-6 text-muted">
                For the hosted demo, Supabase should show <strong>demo</strong> and the backend should show <strong>connected</strong>.
                For real accounts, set demo mode to false and both Supabase and the backend must show <strong>connected</strong>.
              </p>
              <Link href="/workspace" className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-brand hover:underline">
                Open the document demo <ExternalLink className="size-3.5" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}