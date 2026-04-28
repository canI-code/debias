/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // ─── Cloudflare Pages deployment ────────────────────────────────────────────
  // Generates a plain static `out/` directory.
  // Cloudflare Pages build settings: Build command = `npm run build`, Output = `out`
  output: "export",
  trailingSlash: true, // Cloudflare serves /chat/ → /chat/index.html

  // Static export does not support Next.js Image Optimization server.
  // Images are served as-is from /public.
  images: {
    unoptimized: true,
  },

  // Allow NEXT_PUBLIC_API_URL to be set in Cloudflare Pages env vars at build time.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "",
  },
};

export default nextConfig;
