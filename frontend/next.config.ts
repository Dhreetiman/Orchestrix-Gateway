import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async rewrites() {
    // Proxy API calls in development so the browser doesn't hit CORS.
    const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    return [
      { source: "/api/gateway/:path*", destination: `${api}/:path*` },
    ];
  },
};

export default config;
