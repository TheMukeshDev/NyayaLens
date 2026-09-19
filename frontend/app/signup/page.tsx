import Link from "next/link";

import { Logo } from "@/components/logo";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";

import { signup } from "./actions";

export default async function SignupPage(props: PageProps<"/signup">) {
  const searchParams = await props.searchParams;
  const error = typeof searchParams.error === "string" ? searchParams.error : undefined;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 py-12">
      <div className="mb-8">
        <Logo href="/" />
      </div>

      <div className="w-full max-w-sm rounded-xl border border-line bg-surface p-8 shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight text-navy">Create an account</h1>
        <p className="mt-1 text-sm text-muted">Sign up to start using NyayaLens.</p>

        {error ? <Alert kind="error" className="mt-6">{error}</Alert> : null}

        <form action={signup} className="mt-6 flex flex-col gap-4">
          <Field label="Email" htmlFor="email" required>
            <Input
              id="email"
              type="email"
              name="email"
              autoComplete="email"
              required
            />
          </Field>
          <Field label="Password" htmlFor="password" required hint="At least 6 characters.">
            <Input
              id="password"
              type="password"
              name="password"
              autoComplete="new-password"
              minLength={6}
              required
            />
          </Field>
          <Button type="submit" size="lg" className="mt-2">
            Sign up
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-brand hover:underline">
            Log in
          </Link>
        </p>
      </div>

      <p className="mt-6 max-w-sm text-center text-xs text-muted">
        By creating an account, you agree to use NyayaLens for informational
        analysis only — it is not a substitute for professional legal advice.
      </p>
    </main>
  );
}