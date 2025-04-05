import { headers } from 'next/headers'; // Import headers to check server-side context

export const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

// Helper to check if running on the server
const isServer = typeof window === 'undefined';

export function getBackendUrl() {
  if (isServer) {
    // Server-side code (e.g., API routes, Server Components) uses INTERNAL URL
    const internalUrl = process.env.INTERNAL_BACKEND_URL;
    if (!internalUrl) {
      console.error("FATAL: INTERNAL_BACKEND_URL is not defined in the server environment.");
      // Fallback or throw error - adjust based on deployment needs
      // Using public URL as a fallback might work locally but fail in Docker
      return process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'; // Keep fallback for safety?
    }
    return internalUrl;
  } else {
    // Client-side code uses PUBLIC URL
    const publicUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    return publicUrl;
  }
}

export function getApiUrl(path: string) {
  // Use the correct base URL based on context
  const baseUrl = getBackendUrl(); 
  // Ensure path starts with a slash
  const formattedPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}/api/${API_VERSION}${formattedPath}`;
}

export function getAuthUrl() {
  // getApiUrl now correctly handles the context
  return getApiUrl('/auth');
} 