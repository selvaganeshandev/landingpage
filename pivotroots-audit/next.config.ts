import type { NextConfig } from "next";

// Serve under a sub-path when the host shares its domain with other apps, e.g.
// NEXT_PUBLIC_BASE_PATH=/pmx-landingpage behind clients.welocalhost.com/pmx-landingpage
// (proxy must NOT strip the prefix). Build-time: changing it needs a rebuild.
const basePath = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/$/, "");

const nextConfig: NextConfig = {
  basePath,
  images: { unoptimized: true },
  // The page is a lead form for a partner site: keep it out of search indexes
  // until PivotRoots decides otherwise (the <meta name="robots"> in layout.tsx
  // says the same for crawlers that ignore headers).
  async headers() {
    return [{ source: "/(.*)", headers: [{ key: "X-Robots-Tag", value: "noindex" }] }];
  },
};

export default nextConfig;
