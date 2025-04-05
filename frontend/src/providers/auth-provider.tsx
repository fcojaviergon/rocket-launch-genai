'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { Session } from 'next-auth';
import { useSession } from 'next-auth/react';
import { useRouter, usePathname } from 'next/navigation';

interface AuthContextType {
  session: Session | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  authError: string | null;
}

const AuthContext = createContext<AuthContextType>({
  session: null,
  isLoading: true,
  isAuthenticated: false,
  authError: null
});

// Definir rutas públicas que no requieren autenticación
const PUBLIC_ROUTES = new Set([
  '/',
  '/login',
  '/register',
  '/about',
  '/pricing',
  '/contact'
]);

export function AuthProvider({ 
  children,
  requireAuth = false,
  redirectTo = '/login'
}: { 
  children: React.ReactNode;
  requireAuth?: boolean;
  redirectTo?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: session, status } = useSession({
    required: false
  });

  const [authError, setAuthError] = useState<string | null>(null);

  // Verificar si la ruta actual es pública
  const isPublicRoute = PUBLIC_ROUTES.has(pathname || '');

  // Check if session has an error and handle it
  useEffect(() => {
    if (session?.error) {
      console.warn('Session error detected:', session.error);
      setAuthError(session.error);
      
      // No redireccionar si estamos en una ruta pública
      if (isPublicRoute) {
        console.log('Ignoring session error on public route:', pathname);
        return;
      }
      
      // Map of error codes to URL parameters
      const errorMap: Record<string, string> = {
        'RefreshTokenError': 'token_refresh_failed',
        'NoRefreshToken': 'no_token',
        'InvalidRefreshResponse': 'refresh_failed',
        'RefreshAccessTokenError': 'session_expired',
      };
      
      // If there's a token error, redirect to login with appropriate error parameter
      const errorParam = errorMap[session.error] || 'session_expired';
      router.push(`/login?error=${errorParam}`);
    } else {
      setAuthError(null);
    }
  }, [session, router, pathname, isPublicRoute]);

  // Handle authentication requirements
  useEffect(() => {
    // Don't redirect during loading
    if (status === 'loading') return;
    
    // Redirect if auth is required but user is not authenticated
    if (requireAuth && status !== 'authenticated') {
      const url = new URL(redirectTo, window.location.origin);
      url.searchParams.set('from', pathname || '/');
      router.push(url.toString());
    }
  }, [status, requireAuth, redirectTo, router, pathname]);

  const value = {
    session,
    isLoading: status === 'loading',
    isAuthenticated: status === 'authenticated',
    authError
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook to use Auth context
export const useAuth = () => useContext(AuthContext); 