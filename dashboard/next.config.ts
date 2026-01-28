import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  transpilePackages: ['geist'],
  reactStrictMode: false, // Disable to prevent double API calls in development
};

export default nextConfig;
