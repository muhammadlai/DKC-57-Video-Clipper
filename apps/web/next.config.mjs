/** @type {import('next').NextConfig} */
const backendOrigin = process.env.BACKEND_ORIGIN || "http://127.0.0.1:8000";

const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    // allow importing @aitzaz/types and @aitzaz/shared from the monorepo
    externalDir: true,
  },
  async rewrites() {
    return [
      // Proxy the FastAPI backend so the browser stays same-origin
      // (cookies, no CORS headaches, works on any preview domain).
      {
        source: "/api/v1/:path*",
        destination: `${backendOrigin}/api/v1/:path*`,
      },
      {
        source: "/api/health",
        destination: `${backendOrigin}/api/health`,
      },
    ];
  },
};

export default nextConfig;
