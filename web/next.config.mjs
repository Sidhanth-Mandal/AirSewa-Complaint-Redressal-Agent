import createNextIntlPlugin from "next-intl/plugin";
const withNextIntl = createNextIntlPlugin("./i18n/request.ts");
const API = process.env.API_URL || "http://127.0.0.1:8000";
/** @type {import('next').NextConfig} */
const nextConfig = {
  compress: false, // keeps SSE streams unbuffered through the dev proxy
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/:path*` }];
  },
};
export default withNextIntl(nextConfig);
