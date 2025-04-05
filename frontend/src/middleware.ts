import { NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import type { NextRequest } from 'next/server';

// Definition of routes
const PUBLIC_ROUTES = new Set([
  '/',
  '/login',
  '/register',
  '/about',
  '/pricing',
  '/contact'
]);

const AUTH_ROUTES = new Set([
  '/login',
  '/register'
]);

const API_ROUTES = new Set([
  '/api/auth',
  '/api/chat',
  '/api/completions',
  '/api/documents'
]);

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Obtener el token y verificar su validez
  const token = await getToken({ 
    req: request,
    secret: process.env.NEXTAUTH_SECRET
  });
  
  // Si es una ruta pública, permitir acceso sin redireccionamiento
  // aunque haya un token problemático
  if (PUBLIC_ROUTES.has(pathname)) {
    // Verificar si el token tiene errores
    if (token?.error) {
      console.log("Token con error en ruta pública:", pathname, token.error);
      // En rutas públicas, no redirigimos aunque haya un token con error
    }
    return NextResponse.next();
  }

  // Si es una ruta de autenticación y el usuario está autenticado sin errores, redirigir al dashboard
  if (AUTH_ROUTES.has(pathname) && token && !token.error) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // Para rutas de API
  if (pathname.startsWith('/api/')) {
    // Siempre permitir rutas de NextAuth
    if (pathname.startsWith('/api/auth/')) {
      return NextResponse.next();
    }

    // Para otras rutas de API, requerir un token válido
    if (!token) {
      return NextResponse.json(
        { error: 'Authentication required', isAuthError: true },
        { status: 401 }
      );
    }

    // Si el token tiene un error o está expirado, requerir re-autenticación
    if (token.error || (token.accessTokenExpires && Date.now() > token.accessTokenExpires)) {
      return NextResponse.json(
        { error: 'Session expired', isAuthError: true, code: token.error || 'EXPIRED' },
        { status: 401 }
      );
    }

    return NextResponse.next();
  }

  // Rutas protegidas (dashboard, etc.)
  
  // Si no hay token, redirigir a login
  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('from', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Si el token tiene un error o está expirado, redirigir a login
  if (token.error || (token.accessTokenExpires && Date.now() > token.accessTokenExpires)) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('error', token.error || 'session_expired');
    loginUrl.searchParams.set('from', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

// Configure the routes to which the middleware applies
export const config = {
  matcher: [
    /*
     * Exclude routes:
     * - Static files (images, fonts, etc)
     * - API routes (including the streaming endpoint)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
