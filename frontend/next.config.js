/** @type {import('next').NextConfig} */

/**
 * Security Headers Configuration
 *
 * CSP Notes:
 * - 'unsafe-inline' for scripts: Required by Next.js for inline scripts in dev mode
 * - 'unsafe-eval' for scripts: Required by Next.js for HMR and some optimizations
 * - 'unsafe-inline' for styles: Required by Tailwind CSS for dynamic styles
 *
 * Mitigations:
 * - DOMPurify sanitizes all user-generated HTML (DocumentViewerModal, DocumentCard)
 * - frame-ancestors 'none' prevents clickjacking
 * - object-src 'none' prevents plugin-based attacks
 * - upgrade-insecure-requests forces HTTPS in production
 */
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      // Scripts: unsafe-inline/eval required by Next.js - mitigated by DOMPurify sanitization
      "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
      // Styles: unsafe-inline required by Tailwind CSS
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https: blob:",  // Added blob: for image previews
      "font-src 'self' data:",
      "connect-src 'self' https://*.supabase.co https://*.up.railway.app http://localhost:8000 http://localhost:3000",
      "frame-ancestors 'none'",  // Prevent clickjacking
      "base-uri 'self'",
      "form-action 'self'",
      "object-src 'none'",  // Prevent plugin-based attacks (Flash, Java)
      "worker-src 'self' blob:",  // For web workers if needed
      "media-src 'self' https:",  // For video/audio content
      process.env.NODE_ENV === 'production' ? "upgrade-insecure-requests" : "",
    ].filter(Boolean).join('; ')
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY'
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  },
  {
    key: 'X-XSS-Protection',
    value: '1; mode=block'
  },
  {
    key: 'Referrer-Policy',
    value: 'strict-origin-when-cross-origin'
  },
  {
    key: 'Permissions-Policy',
    value: 'geolocation=(), microphone=(), camera=()'
  }
];

const nextConfig = {
  reactStrictMode: true,
  // Enable standalone output for Docker deployment
  output: 'standalone',
  // Proxy API requests to backend in development
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: process.env.NEXT_PUBLIC_API_URL
          ? `${process.env.NEXT_PUBLIC_API_URL}/:path*`
          : "http://localhost:8000/:path*",
      },
    ];
  },
  // Add security headers to all responses
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ];
  },
};

module.exports = nextConfig;

















