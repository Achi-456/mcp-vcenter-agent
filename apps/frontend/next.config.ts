import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: process.env.API_INTERNAL_URL 
          ? `${process.env.API_INTERNAL_URL}/api/v1/:path*`
          : 'http://fastapi.agentic-app.svc.cluster.local:8000/api/v1/:path*'
      }
    ]
  }
}

export default nextConfig
