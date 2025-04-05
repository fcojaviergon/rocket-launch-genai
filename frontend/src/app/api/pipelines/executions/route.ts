import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/config/auth';
import { getApiUrl } from '@/lib/utils/urls';
import { NextRequest, NextResponse } from 'next/server';

// GET handler: Lists pipeline executions
export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  const accessToken = session?.accessToken;

  if (!accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // Use the utility function to get the correct API URL
  const baseUrl = getApiUrl('/pipelines/executions');
  const urlObject = new URL(baseUrl);

  // Append query params from incoming request
  request.nextUrl.searchParams.forEach((value: string, key: string) => {
    urlObject.searchParams.append(key, value);
  });
  const url = urlObject.toString();

  console.log(`[API Proxy] GET ${url}`);

  try {
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to fetch data' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[API Proxy] Error:', error);
    return NextResponse.json({ error: 'An error occurred' }, { status: 500 });
  }
} 