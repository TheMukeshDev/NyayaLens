import { createBrowserClient } from "@supabase/ssr";

import { supabaseConfig } from "./config";

/**
 * Supabase client for use in Client Components (browser).
 *
 * Only the publishable anon key is used here; it is safe to expose. All
 * privileged operations happen server-side.
 */
export function createClient() {
  const { url, anonKey } = supabaseConfig();
  return createBrowserClient(
    url || "https://demo.invalid",
    anonKey || "demo-anon-key",
  );
}
