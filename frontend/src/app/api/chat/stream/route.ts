import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/config/auth';

export async function POST(request: Request) {
  try {
    // Get the request body
    const body = await request.json();
    
    // Get the session using getServerSession
    const session = await getServerSession(authOptions);
    const accessToken = session?.accessToken;
    
    if (!session || !accessToken) {
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
    
    // Remove any accessToken from the body for security
    const { accessToken: _, ...requestBody } = body;
    
    // Get the backend URL from environment variables
    // Use INTERNAL_BACKEND_URL for server-side communication within Docker
    const backendUrl = process.env.INTERNAL_BACKEND_URL;
    if (!backendUrl) {
      console.error("FATAL: INTERNAL_BACKEND_URL is not defined in the server environment for /api/chat/stream route.");
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
    }
    const url = `${backendUrl}/api/v1/chat/stream`;
    
    // Only log minimal info in development
    if (process.env.NODE_ENV === 'development') {
      console.log("[API Stream] Connecting to backend");
    }
    
    // Call the backend
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify(requestBody),
    });
    
    if (!response.ok) {
      // Log error info (no sensitive data)
      console.error(`[API Stream] Error response: ${response.status}`);
      
      // Handle authentication errors specifically
      if (response.status === 401) {
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
      
      // For other errors, try to get structured error data
      let errorMessage;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || 'Backend request failed';
      } catch (e) {
        // Fallback to status text if JSON parsing fails
        errorMessage = `Error ${response.status}: ${response.statusText}`;
      }
      
      return NextResponse.json({ error: errorMessage }, { status: response.status });
    }
    
    // Create a ReadableStream from the backend response for streaming
    const readable = response.body;
    if (!readable) {
      throw new Error('Could not get backend stream');
    }
    
    // Create a stream transformer to pass through the data
    const stream = new ReadableStream({
      async start(controller) {
        const reader = readable.getReader();
        
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              controller.close();
              break;
            }
            
            controller.enqueue(value);
          }
        } catch (error) {
          console.error("Stream processing error");
          controller.error(error);
        }
      }
    });

    // Return the streaming response
    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive'
      }
    });
    
  } catch (error: any) {
    console.error('Chat streaming API error');
    
    // Don't expose detailed error info in production
    const errorMessage = process.env.NODE_ENV === 'development' 
      ? error.message || 'Internal server error'
      : 'Internal server error';
    
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
} 