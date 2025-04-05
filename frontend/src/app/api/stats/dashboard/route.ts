import { NextRequest, NextResponse } from 'next/server';
import { headers } from 'next/headers';
import { getBackendUrl } from '@/lib/utils/urls'; // Import the updated utility

// Removed BACKEND_URL constant, will use getBackendUrl()
export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const requestHeaders = headers();
  const authorization = requestHeaders.get('authorization');

  // Check if BACKEND_URL is available from the utility
  const backendUrl = getBackendUrl();
  if (!backendUrl) {
      console.error("FATAL: Backend URL could not be determined in /api/stats/dashboard route.");
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
  }
  const url = `${backendUrl}/api/v1/stats/dashboard`; // Construct URL using the utility

  if (!authorization) {
      return NextResponse.json({ error: 'Authorization header is missing' }, { status: 401 });
  }

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        authorization: authorization,
      },
      redirect: 'follow',
    });
    
    // Prepare the response
    const data = await response.json();
    
    return NextResponse.json(data, {
      status: response.status,
      statusText: response.statusText,
    });
    
  } catch (error) {
    console.error('Error in statistics proxy:', error);
    return NextResponse.json(
      { error: 'Error getting statistics' },
      { status: 500 }
    );
  }
} 