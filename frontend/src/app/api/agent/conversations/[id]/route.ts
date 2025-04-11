import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/config/auth';

// Get a specific conversation
export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    // Get user session and token
    const session = await getServerSession(authOptions);
    const accessToken = session?.accessToken;

    if (!session || !accessToken) {
      console.warn("[API Agent Conversation] No session or access token found.");
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
      console.error("FATAL: INTERNAL_BACKEND_URL is not defined in the server environment for /api/agent/conversations/[id] route.");
      
      // In development, return mock data
      if (process.env.NODE_ENV === 'development') {
        console.log("[DEV MODE] Returning mock conversation data for ID:", id);
        return NextResponse.json({
          id,
          title: id.includes("mock-1") ? "Getting started with the agent" : "Help with coding",
          messages: [
            { 
              id: "msg-1", 
              role: "user", 
              content: "Hello, how can you help me?", 
              created_at: new Date(Date.now() - 3600000).toISOString() 
            },
            { 
              id: "msg-2", 
              role: "assistant", 
              content: "Hi! I'm your AI assistant. I can help with coding questions, research, and more. What would you like to work on today?", 
              created_at: new Date(Date.now() - 3590000).toISOString() 
            },
            { 
              id: "msg-3", 
              role: "thinking", 
              content: "The user is asking about my capabilities. I should provide a helpful response that outlines what I can do.", 
              created_at: new Date(Date.now() - 3595000).toISOString() 
            }
          ],
          created_at: new Date(Date.now() - 7200000).toISOString(),
          updated_at: new Date(Date.now() - 3590000).toISOString()
        });
      }
      
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
    }
    
    const url = `${backendUrl}/api/v1/agent/conversations/${id}`;

    // Call the actual backend service
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Agent Conversation] Forwarding to backend: ${url}`);
    }

    const backendResponse = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    // Handle backend response
    if (!backendResponse.ok) {
      console.error(`[API Agent Conversation] Backend error response: ${backendResponse.status}`);
      
      // In development, return mock data for testing even if backend fails
      if (process.env.NODE_ENV === 'development') {
        console.log("[DEV MODE] Returning mock conversation data after backend error for ID:", id);
        return NextResponse.json({
          id,
          title: id.includes("mock-1") ? "Getting started with the agent" : "Help with coding",
          messages: [
            { 
              id: "msg-1", 
              role: "user", 
              content: "Hello, how can you help me?", 
              created_at: new Date(Date.now() - 3600000).toISOString() 
            },
            { 
              id: "msg-2", 
              role: "assistant", 
              content: "Hi! I'm your AI assistant. I can help with coding questions, research, and more. What would you like to work on today?", 
              created_at: new Date(Date.now() - 3590000).toISOString() 
            }
          ],
          created_at: new Date(Date.now() - 7200000).toISOString(),
          updated_at: new Date(Date.now() - 3590000).toISOString()
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
        console.error("[API Agent Conversation] Failed to parse backend error JSON.");
      }
      return NextResponse.json({ error: errorMessage }, { status: backendResponse.status });
    }

    // Return successful backend response to the frontend
    const data = await backendResponse.json();
    return NextResponse.json(data);

  } catch (error: any) {
    console.error('[API Agent Conversation] Error:', error);
    
    // In development, return mock data even if there's an error
    if (process.env.NODE_ENV === 'development') {
      const id = params?.id || 'unknown-id';
      console.log("[DEV MODE] Returning mock conversation data after error for ID:", id);
      return NextResponse.json({
        id,
        title: "Mock conversation after error",
        messages: [
          { 
            id: "msg-1", 
            role: "user", 
            content: "Hello, how can you help me?", 
            created_at: new Date(Date.now() - 3600000).toISOString() 
          },
          { 
            id: "msg-2", 
            role: "assistant", 
            content: "Hi! I'm your AI assistant. I can help with coding questions, research, and more. What would you like to work on today?", 
            created_at: new Date(Date.now() - 3590000).toISOString() 
          }
        ],
        created_at: new Date(Date.now() - 7200000).toISOString(),
        updated_at: new Date(Date.now() - 3590000).toISOString()
      });
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

// Update a conversation (title)
export async function PUT(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    // Get user session and token
    const session = await getServerSession(authOptions);
    const accessToken = session?.accessToken;

    if (!session || !accessToken) {
      console.warn("[API Agent Conversation] No session or access token found.");
      return NextResponse.json({ 
        error: 'Session expired or invalid',
        type: 'auth_error' 
      }, { 
        status: 401
      });
    }

    // Get the request body
    const body = await request.json();
    
    // Get backend URL
    const backendUrl = process.env.INTERNAL_BACKEND_URL;
    if (!backendUrl) {
      console.error("FATAL: INTERNAL_BACKEND_URL is not defined in the server environment for /api/agent/conversations/[id] route.");
      
      // In development, return mock success
      if (process.env.NODE_ENV === 'development') {
        console.log("[DEV MODE] Mocking conversation update for ID:", id, body);
        return NextResponse.json({
          id,
          title: body.title || "Updated conversation",
          updated_at: new Date().toISOString()
        });
      }
      
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
    }
    
    const url = `${backendUrl}/api/v1/agent/conversations/${id}/title`;

    // Call the actual backend service
    const backendResponse = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ title: body.title })
    });

    // Handle backend response
    if (!backendResponse.ok) {
      console.error(`[API Agent Conversation] Backend error response: ${backendResponse.status}`);
      
      // In development, return mock success even if backend fails
      if (process.env.NODE_ENV === 'development') {
        console.log("[DEV MODE] Mocking conversation update after backend error for ID:", id);
        return NextResponse.json({
          id,
          title: body.title || "Updated conversation",
          updated_at: new Date().toISOString()
        });
      }
      
      let errorMessage = `Backend request failed with status ${backendResponse.status}`;
      try {
        const errorData = await backendResponse.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        console.error("[API Agent Conversation] Failed to parse backend error JSON.");
      }
      return NextResponse.json({ error: errorMessage }, { status: backendResponse.status });
    }

    // Return successful backend response to the frontend
    const data = await backendResponse.json();
    return NextResponse.json(data);

  } catch (error: any) {
    console.error('[API Agent Conversation Update] Error:', error);
    
    // In development, return mock success even if there's an error
    if (process.env.NODE_ENV === 'development') {
      const id = params?.id || 'unknown-id';
      console.log("[DEV MODE] Mocking conversation update after error for ID:", id);
      return NextResponse.json({
        id,
        title: "Updated conversation after error",
        updated_at: new Date().toISOString()
      });
    }
    
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

// Delete a conversation
export async function DELETE(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    // Get user session and token
    const session = await getServerSession(authOptions);
    const accessToken = session?.accessToken;

    if (!session || !accessToken) {
      console.warn("[API Agent Conversation] No session or access token found.");
      return NextResponse.json({ 
        error: 'Session expired or invalid',
        type: 'auth_error' 
      }, { 
        status: 401
      });
    }

    // Get backend URL
    const backendUrl = process.env.INTERNAL_BACKEND_URL;
    if (!backendUrl) {
      console.error("FATAL: INTERNAL_BACKEND_URL is not defined in the server environment for /api/agent/conversations/[id] route.");
      
      // In development, return mock success
      if (process.env.NODE_ENV === 'development') {
        console.log("[DEV MODE] Mocking conversation deletion for ID:", id);
        return new NextResponse(null, { status: 204 });
      }
      
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
    }
    
    const url = `${backendUrl}/api/v1/agent/conversations/${id}`;

    // Call the actual backend service
    const backendResponse = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    // Handle backend response
    if (!backendResponse.ok) {
      console.error(`[API Agent Conversation] Backend error response: ${backendResponse.status}`);
      
      // In development, return mock success even if backend fails
      if (process.env.NODE_ENV === 'development') {
        console.log("[DEV MODE] Mocking conversation deletion after backend error for ID:", id);
        return new NextResponse(null, { status: 204 });
      }
      
      let errorMessage = `Backend request failed with status ${backendResponse.status}`;
      try {
        const errorData = await backendResponse.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        console.error("[API Agent Conversation] Failed to parse backend error JSON.");
      }
      return NextResponse.json({ error: errorMessage }, { status: backendResponse.status });
    }

    // Return successful deletion response
    return new NextResponse(null, { status: 204 });

  } catch (error: any) {
    console.error('[API Agent Conversation Delete] Error:', error);
    
    // In development, return mock success even if there's an error
    if (process.env.NODE_ENV === 'development') {
      console.log("[DEV MODE] Mocking conversation deletion after error");
      return new NextResponse(null, { status: 204 });
    }
    
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
} 