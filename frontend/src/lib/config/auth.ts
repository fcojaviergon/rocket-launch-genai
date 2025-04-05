import { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { JWT } from 'next-auth/jwt';
import { getAuthUrl } from '@/lib/utils/urls';

// Extend NextAuth types
declare module "next-auth" {
  interface User {
    id: string;
    accessToken: string;
    refreshToken: string;
    role?: string;
  }
  
  interface Session {
    accessToken: string;
    error?: string;
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      role?: string;
    }
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken: string;
    refreshToken: string;
    role?: string;
    userId: string;
    error?: string;
    accessTokenExpires: number;
  }
}

// Function to refresh the token
async function refreshAccessToken(token: JWT): Promise<JWT> {
  try {
    console.log('Attempting to refresh token with refreshToken: ', token.refreshToken?.substring(0, 10) + '...');
    
    // Asegúrese de que NEXTAUTH_URL esté configurado correctamente en sus variables de entorno
    // o use window.location.origin si está disponible
    const baseUrl = process.env.NEXTAUTH_URL || 
      (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000');
      
    console.log(`Using base URL for refresh: ${baseUrl}`);
    
    const response = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken: token.refreshToken }), // Parámetro esperado por nuestra API route
      cache: 'no-store' // Importante: no cachear solicitudes de refresh
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error(`Error refreshing token: ${response.status} ${response.statusText}`, errorData);
      return {
        ...token,
        error: "RefreshTokenError"
      };
    }

    const data = await response.json();
    
    if (!data.access_token || !data.refresh_token) {
      console.error('Invalid response from token refresh endpoint', data);
      return {
        ...token,
        error: "InvalidRefreshResponse"
      };
    }

    console.log('Token refreshed successfully');
    
    const newAccessTokenExpires = Date.now() + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 1000;
    console.log(`New token will expire at: ${new Date(newAccessTokenExpires).toISOString()}`);

    return {
      ...token,
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      accessTokenExpires: newAccessTokenExpires,
      error: undefined
    };
  } catch (error) {
    console.error('Exception during token refresh:', error);
    return {
      ...token,
      error: "RefreshTokenError"
    };
  }
}

// Import backend settings to get token lifetime
// NOTE: This assumes direct access is possible or the value is available via env vars
// If not, consider passing ACCESS_TOKEN_EXPIRE_MINUTES from backend during login
const settings = {
  ACCESS_TOKEN_EXPIRE_MINUTES: parseInt(process.env.NEXT_PUBLIC_ACCESS_TOKEN_EXPIRE_MINUTES || '30', 10)
};

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }
        
        // Use the INTERNAL URL for server-side fetch. It MUST be defined.
        const internalApiUrl = process.env.INTERNAL_BACKEND_URL;
        if (!internalApiUrl) {
          console.error("FATAL: INTERNAL_BACKEND_URL is not defined in the server environment.");
          // In a real app, you might throw an error or handle this more gracefully
          // depending on whether local non-Docker execution needs specific handling.
          // For now, returning null to prevent login.
          return null;
        }
        // Ensure the path structure is correct - assuming login is at /api/v1/auth/login relative to the base API URL
        const loginUrl = `${internalApiUrl}/api/v1/auth/login`;
        
        console.log(`Attempting server-side authentication to: ${loginUrl}`);

        try {
          const response = await fetch(loginUrl, { // Use the verified internal URL
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
              username: credentials.email,
              password: credentials.password,
            })
          });
          
          if (!response.ok) {
            const errorBody = await response.text(); // Get error body for debugging
            console.error(`Authentication error: ${response.status} from ${loginUrl}. Body: ${errorBody}`);
            return null;
          }
          
          const data = await response.json();
          
          if (!data.access_token || !data.refresh_token || !data.user) {
            console.error('Invalid server response:', data);
            return null;
          }
          
          return {
            id: data.user.id,
            email: data.user.email,
            name: data.user.full_name,
            role: data.user.role,
            accessToken: data.access_token,
            refreshToken: data.refresh_token
          };
        } catch (error) {
          console.error('Authentication error:', error);
          return null;
        }
      }
    })
  ],
  callbacks: {
    async jwt({ token, user, account, trigger }) {
      // Log entry into the callback
      console.log(`JWT Callback: Trigger=${trigger}, User=${!!user}, Account=${!!account}, TokenError=${token.error}`);
      
      // Initial sign in
      if (account && user) {
        console.log("JWT Callback: Initial Sign in");
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        token.userId = user.id;
        token.role = user.role;
        token.accessTokenExpires = Date.now() + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 1000;
        token.error = undefined; // Clear errors on successful sign in
        console.log(`JWT Initial Token expires at: ${new Date(token.accessTokenExpires).toISOString()}`);
        return token;
      }

      // 1. If there's already a refresh error, don't try again.
      if (token.error) {
        console.warn(`JWT Callback: Token has error '${token.error}', returning immediately.`);
        return token;
      }
      
      // 2. If essential tokens are missing (user likely logged out or cookie invalid/missing),
      //    don't attempt refresh. Return the token as is (likely minimal/empty).
      if (!token.accessToken || !token.refreshToken || !token.accessTokenExpires) {
         console.log("JWT Callback: Missing essential token fields, skipping expiry check and refresh attempt.");
         // Optionally clear the error if it wasn't a refresh error
         // if (token.error !== "RefreshTokenError" && token.error !== "InvalidRefreshResponse") {
         //   token.error = undefined;
         // }
         return token;
      }

      // Log before checking expiry
      const now = Date.now();
      const expires = token.accessTokenExpires;
      const bufferTime = 5 * 60 * 1000; // 5 minutes in milliseconds
      const shouldRefresh = now >= (expires - bufferTime);
      console.log(`JWT Callback: Checking expiry. Now=${new Date(now).toISOString()}, Expires=${new Date(expires).toISOString()}, Buffer=${bufferTime/1000}s, ShouldRefresh=${shouldRefresh}`);

      // If access token hasn't expired yet (considering buffer), return current token
      if (!shouldRefresh) {
         // console.log("JWT Callback: Token still valid."); // Keep this commented for less noise
        return token;
      }

      // Access token has expired or is about to expire, try to refresh it.
      console.log("JWT Callback: Token expired or expiring soon, attempting refresh.");
      // We already checked for refreshToken existence above, but double-check doesn't hurt.
      if (!token.refreshToken) {
          console.error("JWT Callback: No refresh token available (should have been caught earlier). Cannot refresh.");
          // Set error and return. Session callback will propagate this.
          return { ...token, error: "NoRefreshToken" };
      }

      // Call the refresh function
      console.log("JWT Callback: Calling refreshAccessToken...");
      return refreshAccessToken(token);
    },
    async session({ session, token }) {
      // Log entry and token details passed
      // Be careful logging sensitive parts of the token even here
      console.log(`Session Callback: Received token with Error=${token.error}, Expires=${new Date(token.accessTokenExpires || 0).toISOString()}`); 
      
      // The `token` object here is the output from the `jwt` callback.
      // Assign properties to the `session` object which is exposed to the client.
      // IMPORTANT: Never expose the refresh token to the client-side!
      session.accessToken = token.accessToken;
      session.user.id = token.userId;
      session.user.role = token.role;
      session.error = token.error; // Propagate errors (like RefreshTokenError) to the client

      // Log status for debugging
      // console.log(`Session Callback: Assigning token to session. Error: ${session.error || 'None'}`);

      return session;
    }
  },
  pages: {
    signIn: '/login',
    error: '/login'
  },
  session: {
    strategy: 'jwt',
    updateAge: 20 * 60, // 20 minutos (antes de que el token de 30 minutos expire)
  },
  debug: process.env.NODE_ENV === 'development'
}; 