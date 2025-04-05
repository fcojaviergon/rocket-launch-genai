'use client';

import { useCallback, useEffect } from 'react';
import { signIn, signOut, useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/providers/auth-provider';
import { LoginCredentials, RegisterData } from '../../types/auth-types';
import { api } from '../../api';

interface UseAuthOptions {
  required?: boolean;
  redirectTo?: string;
  redirectIfAuthenticated?: boolean;
  redirectAuthenticatedTo?: string;
}

/**
 * Comprehensive authentication hook that handles authentication state, 
 * redirects, and auth actions
 */
export function useAuthActions(options: UseAuthOptions = {}) {
  const { 
    required = false, 
    redirectTo = '/login',
    redirectIfAuthenticated = false,
    redirectAuthenticatedTo = '/dashboard'
  } = options;
  
  const router = useRouter();
  const { session, isLoading, isAuthenticated } = useAuth();
  const { status } = useSession();
  
  // Handle authentication redirects
  useEffect(() => {
    if (isLoading) return; // Don't redirect during loading
    
    // Redirect if auth is required but user is not authenticated
    if (required && !isAuthenticated) {
      router.push(redirectTo);
    }
    
    // Redirect if user is authenticated but should be elsewhere
    if (redirectIfAuthenticated && isAuthenticated) {
      router.push(redirectAuthenticatedTo);
    }
  }, [isAuthenticated, isLoading, required, redirectIfAuthenticated, redirectTo, redirectAuthenticatedTo, router]);

  const login = useCallback(async (credentials: LoginCredentials) => {
    try {
      const result = await signIn('credentials', {
        ...credentials,
        redirect: false,
      });

      if (result?.error) {
        throw new Error(result.error);
      }

      return result;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }, []);

  const register = useCallback(async (userData: RegisterData) => {
    try {
      const newUser = await api.auth.register(userData);
      return newUser;
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await signOut({ 
        redirect: true, 
        callbackUrl: '/login' 
      });
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
    }
  }, []);

  return {
    session,
    user: session?.user,
    isLoading,
    isAuthenticated,
    login,
    register,
    logout,
    status // Include raw next-auth status for more detailed state handling
  };
} 