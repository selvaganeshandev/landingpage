import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: { unoptimized: true },
  // The page is a lead form for a partner site: keep it out of search indexes
  // until PivotRoots decides otherwise (the <meta name="robots"> in layout.tsx
  // says the same for crawlers that ignore headers).
  async headers() {
    return [{ source: "/(.*)", headers: [{ key: "X-Robots-Tag", value: "noindex" }] }];
  },
};

export default nextConfig;
