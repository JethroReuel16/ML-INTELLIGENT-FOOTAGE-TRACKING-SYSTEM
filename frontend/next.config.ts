import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for Docker / bare-metal deployment.
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  async redirects() {
    return [
      // Unauthenticated visitors are sent on to /login by the app shell.
      { source: "/", destination: "/dashboard", permanent: false },
      // Legacy pages folded into Case history.
      { source: "/videos", destination: "/history", permanent: true },
      { source: "/evidence", destination: "/history", permanent: true },
      { source: "/searches", destination: "/history", permanent: true },
      { source: "/searches/results", destination: "/history", permanent: true },
      { source: "/searches/processing", destination: "/history", permanent: true },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
