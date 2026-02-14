import type { NextConfig } from "next";

const backendPort = process.env.BACKEND_PORT ?? "13579";

const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      allowedOrigins: ["localhost:24680", "192.168.1.166:24680"]
    }
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `http://127.0.0.1:${backendPort}/api/:path*`,
      },
    ]
  },
};

export default nextConfig;
