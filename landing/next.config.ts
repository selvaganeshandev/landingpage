import type { NextConfig } from "next";

// The marketing site can hand out short report links (promptmaxx.co/audit/<token>);
// the report itself lives in the app. Same env var the audit form uses, same
// production default, so a build without env still points at the live app.
const APP_URL = (process.env.NEXT_PUBLIC_APP_URL || "https://app.promptmaxx.co").replace(/\/$/, "");

const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
  },
  async redirects() {
    return [
      {
        source: "/audit/:token",
        destination: `${APP_URL}/audit/:token`,
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
