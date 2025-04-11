import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/config/auth';

export async function GET(request: Request) {
  try {
    // Get user session and token
    const session = await getServerSession(authOptions);
    const accessToken = session?.accessToken;

    if (!session || !accessToken) {
      console.warn("[API Agent Conversations] No session or access token found.");
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

    // Get backend URL
    const backendUrl = process.env.INTERNAL_BACKEND_URL;
    if (!backendUrl) {
      console.error("FATAL: INTERNAL_BACKEND_URL is not defined in the server environment for /api/agent/conversations route.");
      
      // In development, return mock data
      if (process.env.NODE_ENV === 'development') {
        console.log("[DEV MODE] Returning mock conversation data");
        return NextResponse.json([
          {
            id: "mock-1",
            title: "Getting started with the agent",
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          },
          {
            id: "mock-2",
            title: "Help with coding",
            messages: [],
            created_at: new Date(Date.now() - 86400000).toISOString(), // yesterday
            updated_at: new Date(Date.now() - 86400000).toISOString()
          }
        ]);
      }
      
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
    }
    
    const url = `${backendUrl}/api/v1/agent/conversations`;

    // Call the actual backend service
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Agent Conversations] Forwarding to backend: ${url}`);
    }

    const backendResponse = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    // Handle backend response
    if (!backendResponse.ok) {
      console.error(`[API Agent Conversations] Backend error response: ${backendResponse.status}`);
      
      // In development, return mock data for testing even if backend fails
      if (process.env.NODE_ENV === 'development') {
        console.log("[DEV MODE] Returning mock conversation data after backend error");
        return NextResponse.json([
          {
            id: "mock-1",
            title: "Getting started with the agent",
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          },
          {
            id: "mock-2",
            title: "Help with coding",
            messages: [],
            created_at: new Date(Date.now() - 86400000).toISOString(), // yesterday
            updated_at: new Date(Date.now() - 86400000).toISOString()
          }
        ]);
      }
      
      let errorMessage = `Backend request failed with status ${backendResponse.status}`;
      try {
        const errorData = await backendResponse.json();
        errorMessage = errorData.detail || errorMessage;
        if (backendResponse.status === 401) {
            return NextResponse.json({ error: 'Authentication error with backend service', type: 'backend_auth_error' }, { status: 401 });
        }
      } catch (e) {
        console.error("[API Agent Conversations] Failed to parse backend error JSON.");
      }
      return NextResponse.json({ error: errorMessage }, { status: backendResponse.status });
    }

    // Return successful backend response to the frontend
    const data = await backendResponse.json();
    return NextResponse.json(data);

  } catch (error: any) {
    console.error('[API Agent Conversations] Error:', error);
    
    // In development, return mock data even if there's an error
    if (process.env.NODE_ENV === 'development') {
      console.log("[DEV MODE] Returning mock conversation data after error");
      return NextResponse.json([
        {
          id: "mock-1",
          title: "Getting started with the agent",
          messages: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        {
          id: "mock-2",
          title: "Help with coding",
          messages: [],
          created_at: new Date(Date.now() - 86400000).toISOString(), // yesterday
          updated_at: new Date(Date.now() - 86400000).toISOString()
        }
      ]);
    }
    
    const errorMessage = process.env.NODE_ENV === 'development' 
      ? error.message || 'Internal server error'
      : 'Internal server error';
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    // Get user session and token
    const session = await getServerSession(authOptions);
    const accessToken = session?.accessToken;

    if (!session || !accessToken) {
      console.warn("[API Agent Conversations Create] No session or access token found.");
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

    // Get request body
    const body = await request.json();
    
    // Get backend URL
    const backendUrl = process.env.INTERNAL_BACKEND_URL;
    if (!backendUrl) {
      console.error("FATAL: INTERNAL_BACKEND_URL is not defined in the server environment for /api/agent/conversations route.");
      
      // In development, return mock data
      if (process.env.NODE_ENV === 'development') {
        console.log("[DEV MODE] Creating mock conversation with title:", body?.title);
        return NextResponse.json({
          id: `mock-${Date.now()}`,
          title: body?.title || "New conversation",
          messages: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        });
      }
      
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
    }
    
    const url = `${backendUrl}/api/v1/agent/conversations`;

    // Call the actual backend service
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Agent Conversations Create] Forwarding to backend: ${url}`);
    }

    const backendResponse = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify(body)
    });

    // Handle backend response
    if (!backendResponse.ok) {
      console.error(`[API Agent Conversations Create] Backend error response: ${backendResponse.status}`);
      
      // In development, return mock data for testing even if backend fails
      if (process.env.NODE_ENV === 'development') {
        console.log("[DEV MODE] Creating mock conversation after backend error");
        return NextResponse.json({
          id: `mock-${Date.now()}`,
          title: body?.title || "New conversation",
          messages: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        });
      }
      
      let errorMessage = `Backend request failed with status ${backendResponse.status}`;
      try {
        const errorData = await backendResponse.json();
        errorMessage = errorData.detail || errorMessage;
        if (backendResponse.status === 401) {
            return NextResponse.json({ error: 'Authentication error with backend service', type: 'backend_auth_error' }, { status: 401 });
        }
      } catch (e) {
        console.error("[API Agent Conversations Create] Failed to parse backend error JSON.");
      }
      return NextResponse.json({ error: errorMessage }, { status: backendResponse.status });
    }

    // Return successful backend response to the frontend
    const data = await backendResponse.json();
    return NextResponse.json(data);

  } catch (error: any) {
    console.error('[API Agent Conversations Create] Error:', error);
    
    // In development, return mock data even if there's an error
    if (process.env.NODE_ENV === 'development') {
      console.log("[DEV MODE] Creating mock conversation after error");
      return NextResponse.json({
        id: `mock-${Date.now()}`,
        title: "New conversation",
        messages: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
    }
    
    const errorMessage = typeof process.env.NODE_ENV === 'string' && process.env.NODE_ENV === 'development' 
      ? error.message || 'Internal server error'
      : 'Internal server error';
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
} 