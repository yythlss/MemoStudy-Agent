const backend = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // Folder imports are proxied through Next.js before reaching FastAPI.
    // Raise its 10 MB default so PDFs and other study materials can be uploaded.
    proxyClientMaxBodySize: "200mb",
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
