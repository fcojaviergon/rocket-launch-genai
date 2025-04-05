// API proxy to redirect frontend requests to the backend
import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/config/auth";
import { getBackendUrl } from "@/lib/utils/urls"; // Import the updated utility

// Define headers that should never be forwarded to the backend
const SKIP_HEADERS = [
  'connection',
  'transfer-encoding',
  'host',
  'content-length',
  'next-router-prefetch',
  'next-router-state-tree',
  'next-url',
  'x-middleware-prefetch',
];

// Export handlers for all HTTP methods
export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleApiProxy(request, params.path, 'GET');
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleApiProxy(request, params.path, 'POST');
}

export async function PUT(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleApiProxy(request, params.path, 'PUT');
}

export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleApiProxy(request, params.path, 'DELETE');
}

export async function PATCH(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleApiProxy(request, params.path, 'PATCH');
}

/**
 * Unified API proxy handler that forwards requests to the backend
 * with authentication and proper headers
 */
async function handleApiProxy(request: NextRequest, pathSegments: string[], method: string) {
  try {
    // Build the target URL for the backend
    const path = pathSegments.join('/');
    const queryString = request.nextUrl.search;
    const backendUrl = getBackendUrl();
    if (!backendUrl) {
      console.error("FATAL: Backend URL could not be determined in the catch-all API route.");
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
    }
    const targetUrl = new URL(`/api/${path}${queryString}`, backendUrl);
    
    // Get authentication token from cookies
    const cookieStore = cookies();
    const authToken = cookieStore.get('next-auth.session-token')?.value ||
                      cookieStore.get('__Secure-next-auth.session-token')?.value;
    
    if (!authToken) {
      return NextResponse.json(
        { error: 'Unauthorized', message: 'Authentication required' },
        { status: 401 }
      );
    }
    
    // Copy headers to forward to the backend
    const headers = new Headers();
    headers.set('Authorization', `Bearer ${authToken}`);
    
    // Copy all headers from the original request except those that should be skipped
    for (const [key, value] of request.headers.entries()) {
      if (!SKIP_HEADERS.includes(key.toLowerCase())) {
        headers.set(key, value);
      }
    }
    
    // Get the request body for non-GET requests
    let body: ArrayBuffer | null | undefined = undefined;
    if (method !== 'GET' && method !== 'HEAD') {
      // For multipart form data, we need to clone the request and extract the body
      if (request.headers.get('content-type')?.includes('multipart/form-data')) {
        try {
          // Clone the request to get the form data
          const formData = await request.formData();
          body = formData as unknown as ArrayBuffer;
        } catch (error) {
          console.error('Error reading form data:', error);
        }
      } else {
        // For other content types, read as array buffer
        try {
          body = await request.arrayBuffer();
        } catch (error) {
          console.error('Error reading request body:', error);
        }
      }
    }
    
    // Forward the request to the backend
    const response = await fetch(targetUrl, {
      method,
      headers,
      body,
    });
    
    // Forward the response back to the client
    const responseData = await response.arrayBuffer();
    
    // Copy response headers but skip those that should not be forwarded
    const responseHeaders = new Headers();
    for (const [key, value] of response.headers.entries()) {
      if (!SKIP_HEADERS.includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    }
    
    return new NextResponse(responseData, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error: any) {
    console.error('API proxy error:', error);
    
    // Only return minimal error information in production
    const errorMessage = process.env.NODE_ENV === 'development'
      ? error.message || 'Internal server error'
      : 'Internal server error';
    
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
} 