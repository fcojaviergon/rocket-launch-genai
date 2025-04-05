// API proxy for the /api/pipelines/configs route
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/config/auth";
import { getApiUrl } from '@/lib/utils/urls';

export async function GET(req: NextRequest) {
  console.log(`[API Proxy] GET pipelines/configs`);
  
  const session = await getServerSession(authOptions);
  console.log('[API Proxy] Session object:', session ? 'exists' : 'null', 
              'accessToken:', session?.accessToken ? `present (${session.accessToken.substring(0, 10)}...)` : 'missing');
  
  // If no session or no access token, redirect to login
  if (!session || !session.accessToken) {
    console.log('[API Proxy] No valid session, redirecting to login');
    return NextResponse.json(
      { error: 'Unauthorized: Session expired or missing', type: 'auth_error' },
      { status: 401 }
    );
  }
  
  try {
    // Use the utility function to get the correct API URL
    const baseUrl = getApiUrl('/pipelines/configs');
    const urlObject = new URL(baseUrl);
    
    // Append query params from incoming request
    req.nextUrl.searchParams.forEach((value, key) => {
      urlObject.searchParams.append(key, value);
    });
    const url = urlObject.toString();
    
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
    headers.append('Authorization', `Bearer ${session.accessToken}`);
    
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

export async function POST(req: NextRequest) {
  console.log(`[API Proxy] POST pipelines/configs`);
  
  const session = await getServerSession(authOptions);
  
  try {
    // Use the utility function to get the correct API URL
    const url = getApiUrl('/pipelines/configs');
    
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
      console.log('[API Proxy] Adding authorization token');
      headers.append('Authorization', `Bearer ${session.accessToken}`);
    } else {
      console.log('[API Proxy] No session token found');
      return NextResponse.json({ error: 'Unauthorized: No session token found' }, { status: 401 });
    }
    
    // Extract the body of the request
    const body = await req.json().catch(() => ({}));
    
    // Perform the request to the backend
    const response = await fetch(url, {
      method: 'POST',
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