import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

import { DEMO_USER_COOKIE, isDemoMode, supabaseConfig } from "./config";

/**
 * Supabase client for Server Components, Server Actions and Route Handlers.
 *
 * In Next.js 16 `cookies()` is async, so this factory is async too. Session
 * cookies are read from the request and refreshed through the proxy.
 */
export async function createClient() {
  const cookieStore = await cookies();

  if (isDemoMode()) {
    return createDemoClient(cookieStore);
  }

  const { url, anonKey } = supabaseConfig();
  if (!url || !anonKey) {
    throw new Error(
      "Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY, or enable NEXT_PUBLIC_DEMO_MODE for a demo deployment.",
    );
  }

  return createServerClient(
    url,
    anonKey,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, options);
            });
          } catch {
            // `setAll` was called from a Server Component, where cookies are
            // read-only. Session refresh is handled by proxy.ts, so this can
            // be safely ignored.
          }
        },
      },
    },
  );
}

function createDemoClient(cookieStore: Awaited<ReturnType<typeof cookies>>) {
  function currentUser() {
    const email = cookieStore.get(DEMO_USER_COOKIE)?.value;
    return email ? { id: `demo-${email}`, email } : null;
  }

  return {
    auth: {
      async getUser() {
        return { data: { user: currentUser() } };
      },
      async getSession() {
        const user = currentUser();
        return {
          data: { session: user ? { access_token: `demo-${user.email}`, user } : null },
        };
      },
      async signUp({ email }: { email: string }) {
        cookieStore.set(DEMO_USER_COOKIE, email, { httpOnly: true, sameSite: "lax", path: "/" });
        return { data: { session: { access_token: `demo-${email}` } }, error: null };
      },
      async signInWithPassword({ email, password }: { email: string; password: string }) {
        if (!email || password.length < 6) {
          return { error: { message: "Enter a valid email and a password of at least 6 characters." } };
        }
        cookieStore.set(DEMO_USER_COOKIE, email, { httpOnly: true, sameSite: "lax", path: "/" });
        return { error: null };
      },
      async signOut() {
        cookieStore.delete(DEMO_USER_COOKIE);
        return { error: null };
      },
    },
  };
}
