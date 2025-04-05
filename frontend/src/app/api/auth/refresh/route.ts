import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    // Permitir tanto refreshToken como token para compatibilidad
    const refreshToken = body.refreshToken || body.token;
    
    if (!refreshToken) {
      console.error('Refresh token API called without token');
      return NextResponse.json({ error: 'Refresh token not provided' }, { status: 401 });
    }
    
    console.log('Refresh token API called with token:', refreshToken.substring(0, 20) + '...');
    
    // Get the backend URL from environment variables
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const INTERNAL_BACKEND_URL = process.env.INTERNAL_BACKEND_URL || backendUrl;

    // Usar INTERNAL_BACKEND_URL si está disponible (para llamadas server-side)
    const baseUrl = INTERNAL_BACKEND_URL;
    
    console.log(`Calling backend refresh endpoint at ${baseUrl}/api/v1/auth/refresh`);
    
    try {
      // Call the refresh token endpoint of the backend
      const response = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: refreshToken  // Formato esperado por el backend
        }),
        // No guardar en caché respuestas de token
        cache: 'no-store'
      });
      
      if (!response.ok) {
        let errorText = 'Error refreshing token';
        try {
          const errorData = await response.json();
          errorText = errorData.detail || JSON.stringify(errorData);
          console.error('Error en respuesta del backend (refresh token):', {
            status: response.status,
            errorText,
            errorData
          });
        } catch (e) {
          errorText = `Error ${response.status}: ${response.statusText}`;
          console.error('Error desconocido en respuesta del backend (refresh token):', {
            status: response.status,
            errorText,
            error: e
          });
        }
        
        // Limpiar el mensaje de error para evitar datos sensibles
        const sanitizedError = errorText.replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[TOKEN]');
        
        return NextResponse.json({ 
          error: sanitizedError
        }, { status: response.status });
      }
      
      const data = await response.json();
      console.log('Token refresh successful, new tokens received');
      
      if (!data.access_token || !data.refresh_token) {
        console.error('Invalid response from backend refresh endpoint:', 
          JSON.stringify(data).substring(0, 100) + '...');
        return NextResponse.json({ 
          error: 'Invalid response from authentication server' 
        }, { status: 500 });
      }
      
      return NextResponse.json(data);
    } catch (fetchError: any) {
      console.error('Network error in refresh token fetch:', fetchError.message);
      return NextResponse.json(
        { 
          error: 'Network error connecting to authentication server',
          message: fetchError.message
        },
        { status: 500 }
      );
    }
    
  } catch (error: any) {
    console.error('Error in refresh token API:', error);
    return NextResponse.json(
      { 
        error: error.message || 'Internal server error',
        stack: process.env.NODE_ENV === 'development' ? error.stack : undefined 
      },
      { status: 500 }
    );
  }
}
