// API proxy for the /api/pipelines/configs/[id] route
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/config/auth";
import { getApiUrl } from '@/lib/utils/urls';

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  console.log(`[API Proxy] GET pipelines/configs/${params.id}`);
  
  const session = await getServerSession(authOptions);
  const accessToken = session?.accessToken;
  
  if (!accessToken) {
    console.log('[API Proxy] No valid session, returning auth error');
    return NextResponse.json(
      { error: 'Unauthorized: Session expired or missing', type: 'auth_error' },
      { status: 401 }
    );
  }
  
  try {
    // Use the utility function to get the correct API URL
    const baseUrl = getApiUrl(`/pipelines/configs/${params.id}`);
    const urlObject = new URL(baseUrl);

    // Append existing search parameters from the incoming request
    const incomingSearchParams = new URL(req.url).searchParams;
    incomingSearchParams.forEach((value, key) => {
        urlObject.searchParams.append(key, value);
    });
    const url = urlObject.toString(); // Use the final URL string
    
    console.log(`[API Proxy] Redirecting to ${url}`);
    
    // Create headers for the request to the backend
    const headers = new Headers();
    for (const [key, value] of req.headers.entries()) {
      // Skip specific Next.js headers that we don't want to forward
      if (!['host', 'connection', 'content-length'].includes(key.toLowerCase())) {
        headers.append(key, value);
      }
    }
    
    // Add the authorization token from the session
    console.log('[API Proxy] Adding authorization token');
    headers.append('Authorization', `Bearer ${accessToken}`);
    
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
  console.log(`[API Proxy] PUT pipelines/configs/${params.id}`);
  
  const session = await getServerSession(authOptions);
  
  try {
    // Use the utility function to get the correct API URL
    const baseUrl = getApiUrl(`/pipelines/configs/${params.id}`);
    const urlObject = new URL(baseUrl);

    // Append existing search parameters from the incoming request
    const incomingSearchParams = new URL(req.url).searchParams;
    incomingSearchParams.forEach((value, key) => {
        urlObject.searchParams.append(key, value);
    });
    const url = urlObject.toString(); // Use the final URL string
    
    // Create headers for the request to the backend
    const headers = new Headers();
    headers.append('Content-Type', 'application/json');
    for (const [key, value] of req.headers.entries()) {
      // Skip specific Next.js headers that we don't want to forward
      if (!['host', 'connection', 'content-length', 'content-type'].includes(key.toLowerCase())) {
        headers.append(key, value);
      }
    }
    
    // Add the authorization token from the session
    if (session?.accessToken) {
      console.log('[API Proxy] Token available to forward with request');
      headers.append('Authorization', `Bearer ${session.accessToken}`);
    } else {
      console.log('[API Proxy] No session token found');
      return NextResponse.json({ error: 'Unauthorized: No session token found' }, { status: 401 });
    }
    
    // Extract the body of the request
    const body = await req.json().catch((err) => {
      console.error('[API Proxy] Error parsing JSON body:', err);
      return {};
    });
    
    // Log the request body for debugging (only in development)
    if (process.env.NODE_ENV === 'development') {
      console.log('[API Proxy] Sending body:', JSON.stringify(body, null, 2).substring(0, 500) + '...');
    }
    
    // Perform the request to the backend
    const response = await fetch(url, {
      method: 'PUT',
      headers,
      body: JSON.stringify(body),
      redirect: 'follow',
    });
    
    // Prepare the response
    const responseData = await response.text();
    console.log(`[API Proxy] Status: ${response.status}`);
    
    // If response is not successful, log more details
    if (!response.ok) {
      console.error(`[API Proxy] Error ${response.status} updating pipeline config:`, responseData);
    }
    
    // If it's JSON, try to parse it
    let jsonData;
    try {
      jsonData = JSON.parse(responseData);
    } catch (e) {
      console.error('[API Proxy] Error parsing JSON response:', e);
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
  console.log(`[API Proxy] DELETE pipelines/configs/${params.id}`);
  
  const session = await getServerSession(authOptions);
  
  try {
    // Use the utility function to get the correct API URL
    const baseUrl = getApiUrl(`/pipelines/configs/${params.id}`);
    const urlObject = new URL(baseUrl);

    // Append existing search parameters from the incoming request
    const incomingSearchParams = new URL(req.url).searchParams;
    incomingSearchParams.forEach((value, key) => {
        urlObject.searchParams.append(key, value);
    });
    const url = urlObject.toString(); // Use the final URL string
    
    // Create headers for the request to the backend
    const headers = new Headers();
    for (const [key, value] of req.headers.entries()) {
      // Skip specific Next.js headers that we don't want to forward
      if (!['host', 'connection', 'content-length'].includes(key.toLowerCase())) {
        headers.append(key, value);
      }
    }
    
    // Add the authorization token from the session
    if (session?.accessToken) {
      headers.append('Authorization', `Bearer ${session.accessToken}`);
    } else {
      console.log('[API Proxy] No session token found');
      return NextResponse.json({ error: 'Unauthorized: No session token found' }, { status: 401 });
    }
    
    // Perform the request to the backend
    const response = await fetch(url, {
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