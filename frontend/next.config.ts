import type { NextConfig } from "next";

/**
 * Backend origin used for the same-origin API proxy.
 *
 * When `NEXT_PUBLIC_API_URL` is set the browser talks to the backend directly
 * and CORS applies. When it is not set, the browser calls the same-origin
 * `/backend/*` path below and Next.js forwards it to this origin server-side,
 * so a misconfigured deployment degrades to a working (if slightly slower)
 * single-origin setup instead of every request failing.
 */
const apiProxyTarget = (process.env.API_PROXY_TARGET ?? "").trim().replace(/\/+$/, "");

const nextConfig: NextConfig = {
  // Next.js 16 allows only one `next dev` process per project directory. The
  // Playwright E2E suite runs its own dev server alongside any server the
  // developer already has open, so it points Next at a separate build directory
  // via NEXT_DIST_DIR. Unset, this stays the default `.next`.
  distDir: process.env.NEXT_DIST_DIR || undefined,
  compress: true,
  poweredByHeader: false,
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },
  async rewrites() {
    if (!apiProxyTarget) return [];
    return [{ source: "/backend/:path*", destination: `${apiProxyTarget}/:path*` }];
  },
};

export default nextConfig;
