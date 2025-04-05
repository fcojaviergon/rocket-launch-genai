/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  env: {
    NEXTAUTH_URL: process.env.NEXTAUTH_URL || 'http://localhost:3000',
    BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000',
  },
  // Configuración simple de CORS
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,OPTIONS,PATCH,DELETE,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version' }
        ]
      }
    ];
  },
  // Docker configuration
  output: 'standalone',
  // Copy global CSS to the standalone output
  outputFileTracing: true,
  experimental: {
    // Enable copying of assets to standalone output
    outputFileTracingExcludes: {
      '*': [
        // Exclude misc development files
        '.github/**',
        '.vscode/**',
        'e2e/**',
        'tests/**',
      ],
    },
    outputFileTracingIncludes: {
      '/': ['./src/**/*'],
    },
    esmExternals: 'loose',
  },
  // Skip TypeScript checking
  typescript: {
    ignoreBuildErrors: true,
  },
  // Disable strict checking
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Configure webpack
  webpack: (config) => {
    config.watchOptions = {
      aggregateTimeout: 5000,
      poll: 1000,
    };
    return config;
  },
}

module.exports = nextConfig
