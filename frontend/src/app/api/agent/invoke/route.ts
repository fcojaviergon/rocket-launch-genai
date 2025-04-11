import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/config/auth';

export async function POST(request: Request) {
  try {
    // 1. Get request body (all parameters)
    const body = await request.json();
    const { query, conversation_id } = body;

    if (!query) {
        return NextResponse.json({ error: 'Query is required' }, { status: 400 });
    }

    // 2. Get user session and token
    const session = await getServerSession(authOptions);
    const accessToken = session?.accessToken;

    if (!session || !accessToken) {
      console.warn("[API Agent Invoke] No session or access token found.");
      return NextResponse.json({ 
        error: 'Session expired or invalid',
        type: 'auth_error' 
      }, { 
        status: 401,
        headers: {
          'Cache-Control': 'no-store, no-cache, must-revalidate',
          'Pragma': 'no-cache'
        }
      });
    }

    // 3. Get backend URL
    // Use INTERNAL_BACKEND_URL for server-side communication
    const backendUrl = process.env.INTERNAL_BACKEND_URL;
    if (!backendUrl) {
      console.error("FATAL: INTERNAL_BACKEND_URL is not defined in the server environment for /api/agent/invoke route.");
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
    }
    const url = `${backendUrl}/api/v1/agent/invoke`;

    // 4. Call the actual backend service
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Agent Invoke] Forwarding to backend: ${url} with query: "${query.substring(0, 50)}..."`);
      if (conversation_id) {
        console.log(`[API Agent Invoke] Using existing conversation_id: ${conversation_id}`);
      }
    }

    // Prepare request to backend - passing required fields only
    const backendBody = {
      query,
      conversation_id: conversation_id || null
      // user_id is obtained from the token in the backend
    };

    const backendResponse = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify(backendBody),
    });

    // 5. Handle backend response
    if (!backendResponse.ok) {
      console.error(`[API Agent Invoke] Backend error response: ${backendResponse.status}`);
      let errorMessage = `Backend request failed with status ${backendResponse.status}`;
      try {
        // Try to parse JSON error first
        const contentType = backendResponse.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await backendResponse.json();
          errorMessage = errorData.detail || JSON.stringify(errorData);
        } else {
          // Fallback to text if not JSON
          errorMessage = await backendResponse.text() || errorMessage;
        }
        
        // Specific handling for backend auth errors
        if (backendResponse.status === 401) {
            return NextResponse.json({ error: 'Authentication error with backend service', type: 'backend_auth_error' }, { status: 401 });
        }
      } catch (e) {
        console.error("[API Agent Invoke] Failed to parse backend error response:", e);
      }
      return NextResponse.json({ error: errorMessage }, { status: backendResponse.status });
    }

    // 6. Stream the response back to the client - don't try to parse to JSON
    // Check if we have a streaming response from the backend
    const contentType = backendResponse.headers.get('content-type');
    
    if (contentType?.includes('text/plain')) {
      // For streaming text responses, stream them directly back
      return new Response(backendResponse.body, {
        headers: {
          'Content-Type': 'text/plain',
          'Cache-Control': 'no-cache'
        }
      });
    } else {
      // For non-streaming responses, parse as JSON and return
      try {
        const data = await backendResponse.json();
        return NextResponse.json(data);
      } catch (e) {
        console.error("[API Agent Invoke] Failed to parse backend JSON response:", e);
        return NextResponse.json({ error: "Failed to parse backend response" }, { status: 500 });
      }
    }

  } catch (error: any) {
    console.error('[API Agent Invoke] Error:', error);
    const errorMessage = process.env.NODE_ENV === 'development' 
      ? error.message || 'Internal server error'
      : 'Internal server error';
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
} 