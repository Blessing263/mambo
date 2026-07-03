/** @type {import('next').NextConfig} */
const API_BASE = process.env.RUZIVO_API_BASE || "http://127.0.0.1:8770";

const nextConfig = {
  reactStrictMode: true,
  // Proxy /api/* to the RAG backend so the browser talks same-origin (works for
  // local and remote/tunnelled demos, and keeps SSE streaming intact).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_BASE}/:path*` }];
  },
};

export default nextConfig;
