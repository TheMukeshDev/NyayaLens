import type { ReactNode } from "react";

import { SkipLink } from "@/components/ui/skip-link";
import { createClient } from "@/lib/supabase/server";

import { MarketingFooter } from "./footer";
import { MarketingNav } from "./marketing-nav";

export async function MarketingLayout({ children }: { children: ReactNode }) {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <SkipLink />
      <MarketingNav loggedIn={session !== null} />
      <main id="main-content" className="flex-1">{children}</main>
      <MarketingFooter />
    </div>
  );
}