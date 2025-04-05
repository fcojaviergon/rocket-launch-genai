// API proxy for the /api/pipelines/[id] route
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/config/auth';
import { getApiUrl } from '@/lib/utils/urls';

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  console.log(`[API Proxy] GET pipelines/${params.id}`);
  
  const session = await getServerSession(authOptions);
  const accessToken = session?.accessToken;

  if (!accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // Use the utility function to get the correct API URL
  const baseUrl = getApiUrl(`/pipelines/${params.id}`);
  const urlObject = new URL(baseUrl);
  
  // Add query parameters from the incoming request
  for (const [key, value] of req.nextUrl.searchParams.entries()) {
    urlObject.searchParams.append(key, value);
  }
  const url = urlObject.toString(); // Final URL string
  
  try {
    console.log(`[API Proxy] Redirecting to ${url}`);
    
    // Create headers for the request to the backend
    const headers = new Headers();
    for (const [key, value] of req.headers.entries()) {
      // Skip specific Next.js headers that we don't want to forward
      if (!['host', 'connection', 'content-length'].includes(key.toLowerCase())) {
        headers.append(key, value);
      }
    }
    
    // Perform the request to the backend
    const response = await fetch(url, {
      method: 'GET',
      headers,
      redirect: 'follow',
    });
    
    // Prepare the response
    const responseData = await response.text();
    console.log(`[API Proxy] Status: ${response.status}`);
    
    // If it's JSON, try to parse it
    let jsonData;
    try {
      jsonData = JSON.parse(responseData);
    } catch (e) {
      // If it's not JSON, return the text
      return new NextResponse(responseData, {
        status: response.status,
        statusText: response.statusText,
        headers: {
          'Content-Type': 'text/plain',
        },
      });
    }
    
    // Return the response as JSON
    return NextResponse.json(jsonData, {
      status: response.status,
      statusText: response.statusText,
    });
    
  } catch (error) {
    console.error('[API Proxy] Error:', error);
    return NextResponse.json(
      { error: 'Error processing the request' },
      { status: 500 }
    );
  }
}

export async function PUT(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  console.log(`[API Proxy] PUT pipelines/${params.id}`);
  
  const session = await getServerSession(authOptions);
  const accessToken = session?.accessToken;

  if (!accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const url = getApiUrl(`/pipelines/${params.id}`);
  
  try {
    // Create headers for the request to the backend
    const headers = new Headers();
    headers.append('Content-Type', 'application/json');
    for (const [key, value] of req.headers.entries()) {
      // Skip specific Next.js headers that we don't want to forward
      if (!['host', 'connection', 'content-length', 'content-type'].includes(key.toLowerCase())) {
        headers.append(key, value);
      }
    }
    
    // Extract the body of the request
    const body = await req.json().catch(() => ({}));
    
    // Perform the request to the backend
    const response = await fetch(url.toString(), {
      method: 'PUT',
      headers,
      body: JSON.stringify(body),
      redirect: 'follow',
    });
    
    // Prepare the response
    const responseData = await response.text();
    console.log(`[API Proxy] Status: ${response.status}`);
    
    // If it's JSON, try to parse it
    let jsonData;
    try {
      jsonData = JSON.parse(responseData);
    } catch (e) {
      // If it's not JSON, return the text
      return new NextResponse(responseData, {
        status: response.status,
        statusText: response.statusText,
        headers: {
          'Content-Type': 'text/plain',
        },
      });
    }
    
    // Return the response as JSON
    return NextResponse.json(jsonData, {
      status: response.status,
      statusText: response.statusText,
    });
    
  } catch (error) {
    console.error('[API Proxy] Error:', error);
    return NextResponse.json(
      { error: 'Error processing the request' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  console.log(`[API Proxy] DELETE pipelines/${params.id}`);
  
  const session = await getServerSession(authOptions);
  const accessToken = session?.accessToken;

  if (!accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const url = getApiUrl(`/pipelines/${params.id}`);
  
  try {
    // Create headers for the request to the backend
    const headers = new Headers();
    for (const [key, value] of req.headers.entries()) {
      // Skip specific Next.js headers that we don't want to forward
      if (!['host', 'connection', 'content-length'].includes(key.toLowerCase())) {
        headers.append(key, value);
      }
    }
    
    // Perform the request to the backend
    const response = await fetch(url.toString(), {
      method: 'DELETE',
      headers,
      redirect: 'follow',
    });
    
    // Prepare the response
    const responseData = await response.text();
    console.log(`[API Proxy] Status: ${response.status}`);
    
    // If the response is empty, return a 204
    if (!responseData) {
      return new NextResponse(null, {
        status: 204,
      });
    }
    
    // If it's JSON, try to parse it
    let jsonData;
    try {
      jsonData = JSON.parse(responseData);
    } catch (e) {
      // If it's not JSON, return the text
      return new NextResponse(responseData, {
        status: response.status,
        statusText: response.statusText,
        headers: {
          'Content-Type': 'text/plain',
        },
      });
    }
    
    // Return the response as JSON
    return NextResponse.json(jsonData, {
      status: response.status,
      statusText: response.statusText,
    });
    
  } catch (error) {
    console.error('[API Proxy] Error:', error);
    return NextResponse.json(
      { error: 'Error processing the request' },
      { status: 500 }
    );
  }
} 