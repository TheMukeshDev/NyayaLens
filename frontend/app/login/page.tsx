import Link from "next/link";

import { Logo } from "@/components/logo";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { DEMO_EMAIL, DEMO_PASSWORD, isDemoMode } from "@/lib/supabase/config";

import { login } from "./actions";

export default async function LoginPage(props: PageProps<"/login">) {
  const searchParams = await props.searchParams;
  const error = typeof searchParams.error === "string" ? searchParams.error : undefined;
  const next = typeof searchParams.next === "string" ? searchParams.next : "/dashboard";
  const signedUp = searchParams.signed_up !== undefined;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 py-12">
      <div className="mb-8">
        <Logo href="/" />
      </div>

      <div className="w-full max-w-sm rounded-xl border border-line bg-surface p-8 shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight text-navy">Log in</h1>
        <p className="mt-1 text-sm text-muted">Welcome back to NyayaLens.</p>

        {signedUp ? (
          <Alert kind="success" title="Account created" className="mt-6">
            Check your email to confirm your account, then log in.
          </Alert>
        ) : null}

        {error ? <Alert kind="error" className="mt-6">{error}</Alert> : null}

        {isDemoMode() ? (
          <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-navy">
            <p className="font-semibold">Demo access</p>
            <p className="mt-1 text-xs text-muted">Use these credentials for the live demo:</p>
            <p className="mt-2 font-mono text-xs">Email: {DEMO_EMAIL}</p>
            <p className="font-mono text-xs">Password: {DEMO_PASSWORD}</p>
          </div>
        ) : null}

        <form action={login} className="mt-6 flex flex-col gap-4">
          <input type="hidden" name="next" value={next} />
          <Field label="Email" htmlFor="email" required>
            <Input
              id="email"
              type="email"
              name="email"
              autoComplete="email"
              required
            />
          </Field>
          <Field label="Password" htmlFor="password" required>
            <Input
              id="password"
              type="password"
              name="password"
              autoComplete="current-password"
              required
            />
          </Field>
          <Button type="submit" size="lg" className="mt-2">
            Log in
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          No account?{" "}
          <Link href="/signup" className="font-medium text-brand hover:underline">
            Sign up
          </Link>
        </p>
        <p className="mt-3 text-center text-xs text-muted">
          <Link href="/connection-test" className="hover:text-brand hover:underline">
            Check service connections
          </Link>
        </p>
      </div>

      <p className="mt-6 max-w-sm text-center text-xs text-muted">
        By continuing, you agree to use NyayaLens for informational analysis
        only — it is not a substitute for professional legal advice.
      </p>
    </main>
  );
}