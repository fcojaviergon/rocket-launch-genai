import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/config/auth';

// Backend URL
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    console.log(`[API Proxy] GET pipelines/executions/${params.id}`);
    
    // Verify authentication
    const session = await getServerSession(authOptions);
    if (!session) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const executionId = params.id;
    if (!executionId) {
      return NextResponse.json(
        { error: 'Execution ID not provided' },
        { status: 400 }
      );
    }

    // Build the complete URL for the backend
    const url = `${BACKEND_URL}/api/v1/pipelines/executions/${executionId}`;
    
    // Get token from the session
    const token = session.accessToken;
    
    // Make the request to the backend
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      console.error(`[API Proxy] Error ${response.status} when getting execution ${executionId}`);
      const errorText = await response.text();
      
      return NextResponse.json(
        { error: `Error ${response.status}: ${errorText}` },
        { status: response.status }
      );
    }
    
    // Convert the response to JSON
    const data = await response.json();
    
    // Return the data
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Error when getting execution status:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
} 