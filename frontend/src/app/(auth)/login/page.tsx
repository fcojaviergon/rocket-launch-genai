'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Loader2 } from 'lucide-react';
import { getBackendUrl } from '@/lib/utils/urls';

// Inner component that uses useSearchParams
function LoginContent() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Handle URL parameters for errors
  useEffect(() => {
    const errorParam = searchParams.get('error');
    if (errorParam) {
      // Map error codes to user-friendly messages
      const errorMessages: Record<string, string> = {
        'session_expired': 'Your session has expired. Please log in again.',
        'token_refresh_failed': 'Authentication token could not be refreshed. Please log in again.',
        'no_token': 'No authentication token found. Please log in again.',
        'refresh_failed': 'Unable to refresh your session. Please log in again.',
        'auth_failed': 'Authentication failed. Please log in again.',
        'Credentials': 'Invalid email or password.',
        'CredentialsSignin': 'Invalid email or password.',
        'default': 'An error occurred. Please try again.'
      };
      
      setError(errorMessages[errorParam] || errorMessages.default);
    }
    
    // Handle successful registration message
    if (searchParams.get('registered') === 'true') {
      setError(''); // Clear any errors
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const result = await signIn('credentials', {
        redirect: false,
        email,
        password,
        callbackUrl: '/dashboard'
      });

      if (result?.error) {
        if (result.error === 'CredentialsSignin') {
          setError('Incorrect email or password');
        } else {
          setError(result.error || 'Error logging in');
        }
      } else if (result?.url) {
        setTimeout(() => {
          const redirectUrl = result.url || '/dashboard';
          router.push(redirectUrl);
          router.refresh();
        }, 100);
      } else {
        setTimeout(() => {
          router.push('/dashboard');
          router.refresh();
        }, 100);
      }
    } catch (error) {
      console.error('Error during login:', error);
      setError('Error logging in');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-sm space-y-6 p-4">
      <div className="space-y-2 text-center">
        <h1 className="text-3xl font-bold">Log in</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Enter your credentials to access
        </p>
      </div>
      
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="email">Email</label>
          <Input
            id="email"
            type="email"
            placeholder="user@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label htmlFor="password">Password</label>
       
          </div>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading...
            </>
          ) : (
            'Log in'
          )}
        </Button>
      </form>
      <div className="text-center text-sm">
        Don't have an account?{' '}
        <Link href="/register" className="underline">
          Register
        </Link>
      </div>
    </div>
  );
}

// Main page component wraps the inner component with Suspense
export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Suspense fallback={<div className="flex h-32 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}>
        <LoginContent />
      </Suspense>
    </div>
  );
}
