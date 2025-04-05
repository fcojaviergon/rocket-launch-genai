// API proxy for the /api/documents/[id] route
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/config/auth';
import { getApiUrl } from '@/lib/utils/urls'; // Import the updated utility

// Removed BACKEND_URL constant

// GET handler: Retrieves a document
export async function GET(
  request: NextRequest, // Changed type to NextRequest to access nextUrl
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions);
  const accessToken = session?.accessToken;

  if (!accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // Use the utility function to get the correct API URL
  const baseUrl = getApiUrl(`/documents/${params.id}`);
  const urlObject = new URL(baseUrl);

  // Add query parameters from the incoming request
  for (const [key, value] of request.nextUrl.searchParams.entries()) {
    urlObject.searchParams.append(key, value);
  }
  const url = urlObject.toString(); // Final URL string

  console.log(`[API Proxy] GET ${url}`);
  
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });
    
    // Check if the response is JSON, otherwise return as text/blob
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      return NextResponse.json(data, { status: response.status });
    } else {
      // For non-JSON (like file downloads), stream the response body
      const blob = await response.blob();
      return new NextResponse(blob, {
        status: response.status,
        headers: {
          'Content-Type': contentType || 'application/octet-stream',
          'Content-Disposition': response.headers.get('content-disposition') || `attachment; filename="${params.id}"`
        }
      });
    }
  } catch (error: any) {
    console.error('[API Proxy] Error:', error);
    return NextResponse.json({ error: error.message || 'Error fetching document' }, { status: 500 });
  }
}

// PUT handler: Updates a document (often requires multipart/form-data)
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions);
  const accessToken = session?.accessToken;

  if (!accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const baseUrl = getApiUrl(`/documents/${params.id}`); // Use utility
  const url = baseUrl; // PUT usually doesn't need query params from original request

  console.log(`[API Proxy] PUT ${url}`);

  try {
    // Forward the request body and relevant headers
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        // Let fetch handle Content-Type for FormData
        // 'Content-Type': request.headers.get('Content-Type') || 'application/json',
      },
      body: request.body, // Stream the body
      // duplex: 'half' // Temporarily removed due to potential TS type issue
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });

  } catch (error: any) {
    console.error('[API Proxy] Error:', error);
    return NextResponse.json({ error: error.message || 'Error updating document' }, { status: 500 });
  }
}


// DELETE handler: Deletes a document
export async function DELETE(
  request: NextRequest, 
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions);
  const accessToken = session?.accessToken;

  if (!accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const url = getApiUrl(`/documents/${params.id}`); // Use utility

  console.log(`[API Proxy] DELETE ${url}`);

  try {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    // DELETE might return 204 No Content or JSON
    if (response.status === 204) {
        return new NextResponse(null, { status: 204 });
    }
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });

  } catch (error: any) {
    console.error('[API Proxy] Error:', error);
    return NextResponse.json({ error: error.message || 'Error deleting document' }, { status: 500 });
  }
} 