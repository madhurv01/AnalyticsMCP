/** @type {import('next').NextConfig} */
const API_TARGET = process.env.API_PROXY_TARGET || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Serve the API under the web origin so session cookies are same-origin.
    return [
      { source: "/api/:path*", destination: `${API_TARGET}/api/:path*` },
      { source: "/mcp/:path*", destination: `${API_TARGET}/mcp/:path*` },
    ];
  },
};
export default nextConfig;
