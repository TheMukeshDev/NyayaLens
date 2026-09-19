import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next.js 16 allows only one `next dev` process per project directory. The
  // Playwright E2E suite runs its own dev server alongside any server the
  // developer already has open, so it points Next at a separate build directory
  // via NEXT_DIST_DIR. Unset, this stays the default `.next`.
  distDir: process.env.NEXT_DIST_DIR || undefined,
};

export default nextConfig;
