export const DEMO_USER_COOKIE = "nyayalens-demo-user";
export const DEMO_EMAIL = "demo@nyayalens.com";
export const DEMO_PASSWORD = "NyayaDemo2026!";
export const DEMO_SESSION_MAX_AGE = 60 * 60 * 24 * 7;

export function isDemoMode(): boolean {
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") return true;

  // A demo deployment must still render when Vercel has not received the
  // optional public Supabase variables yet. Real Supabase is used whenever
  // both values are present and demo mode is explicitly disabled.
  const { url, anonKey } = supabaseConfig();
  return !url || !anonKey;
}

export function supabaseConfig() {
  return {
    url: process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
    anonKey:
      process.env.SUPABASE_ANON_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  };
}