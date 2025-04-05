import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/config/auth';
import { getApiUrl } from '@/lib/utils/urls';

export async function POST(request: Request) {
  // verify authentication
  const session = await getServerSession(authOptions);
  
  // Verify if we have a valid session with access token
  if (!session || !session.accessToken) {
    console.error('No active session or access token');
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  
  try {
    const body = await request.json();
    
    // Validate and prepare parameters
    const requestBody = {
      prompt: body.prompt,
      model: body.model || 'gpt-3.5-turbo',
      max_tokens: body.max_tokens || 256,
      temperature: body.temperature !== undefined ? body.temperature : 0.7,
      top_p: body.top_p !== undefined ? body.top_p : 1.0,
      frequency_penalty: body.frequency_penalty !== undefined ? body.frequency_penalty : 0.0,
      presence_penalty: body.presence_penalty !== undefined ? body.presence_penalty : 0.0,
      stop: body.stop || undefined
    };
    
    // Use the utility function to get the correct API URL
    const apiUrl = getApiUrl('/chat/completions'); // Use utility

    console.log('Calling completions at:', apiUrl);
    console.log('Access token available:', !!session.accessToken);
    
    // Call the backend
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.accessToken}`
      },
      body: JSON.stringify(requestBody),
    });
    
    console.log('Backend response:', response.status);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error in request to backend');
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Error:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
