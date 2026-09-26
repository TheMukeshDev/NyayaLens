"use server";

import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";

export async function signup(formData: FormData) {
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");

  try {
    const supabase = await createClient();
    const { data, error } = await supabase.auth.signUp({ email, password });

    if (error) {
      redirect(`/signup?error=${encodeURIComponent(error.message)}`);
    }

    // If email confirmation is disabled, the user is signed in immediately.
    if (data.session) {
      redirect("/dashboard");
    }

    // Otherwise they must confirm their email before logging in.
    redirect("/login?signed_up=1");
  } catch (error) {
    // Redirect throws internally in Next.js; preserve that control flow.
    if (isRedirectError(error)) throw error;
    redirect(
      "/signup?error=" +
        encodeURIComponent(
          "Account service is unavailable. Check the Supabase URL and key in the deployment environment, or enable demo mode for testing.",
        ),
    );
  }
}

function isRedirectError(error: unknown): boolean {
  return (
    error instanceof Error &&
    "digest" in error &&
    typeof error.digest === "string" &&
    error.digest.startsWith("NEXT_REDIRECT")
  );
}
