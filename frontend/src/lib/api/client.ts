import axios from 'axios';
import { getSession } from 'next-auth/react';
import { getBackendUrl } from '@/lib/utils/urls';

interface ProgressEvent {
  loaded: number;
  total?: number;
}

class ApiClient {
  private client;
  private isDevelopment: boolean;

  constructor() {
    this.isDevelopment = process.env.NODE_ENV === 'development';
    this.client = axios.create({
      baseURL: getBackendUrl(),
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Only log requests in development mode
    if (this.isDevelopment) {
      // Interceptor for logging requests (without sensitive data)
      this.client.interceptors.request.use((config) => {
        // Create a deep copy for logging
        const sanitizedConfig = JSON.parse(JSON.stringify(config));
        
        // Remove sensitive data from logs
        if (sanitizedConfig.headers?.Authorization) {
            sanitizedConfig.headers.Authorization = 'Bearer [REDACTED]';
        }
        
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      });

      // Interceptor for logging responses (without sensitive data)
      this.client.interceptors.response.use(
        (response) => {
          console.log(`API Response: ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`);
          return response;
        },
        (error) => {
          console.error(`API Error: ${error.response?.status || 'Unknown'} ${error.config?.method?.toUpperCase() || 'Unknown'} ${error.config?.url || 'Unknown'}`);
          return Promise.reject(error);
        }
      );
    }

    this.client.interceptors.request.use(
      this.handleRequestAuthorization,
      this.handleRequestError
    );

    this.client.interceptors.response.use(
      (response: any) => response,
      this.handleResponseError
    );
  }
  
  private handleRequestAuthorization = async (config: any) => {
    try {
      // Get current session
      let session = await getSession();
      
      // Debug session
      console.log("NextAuth Session for API call:", JSON.stringify(session));
      
      if (!session) {
        return Promise.reject({
          message: 'No active session',
          status: 401
        });
      }
      
      if (!session?.accessToken) {
        // If there is no access token but there is a session, it is possible that we need to update
        // This should not normally happen, but we handle it just in case
        console.warn('Session without access token, redirecting to login');
        
        if (typeof window !== 'undefined') {
          window.location.href = '/login?error=no_token';
        }
        
        return Promise.reject({
          message: 'No token in session',
          status: 401
        });
      }

      // Force refresh session before continuing - this will trigger NextAuth's refresh logic
      // This preemptive refresh helps prevent expired token issues
      try {
        await fetch('/api/auth/session', { 
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          cache: 'no-store'
        });
        
        // Get potentially refreshed session
        const refreshedSession = await getSession();
        
        if (refreshedSession?.accessToken && refreshedSession.accessToken !== session.accessToken) {
          console.log("Token was refreshed during request preparation");
          session = refreshedSession;
        }
      } catch (refreshError) {
        console.warn("Failed to refresh session preemptively:", refreshError);
        // Continue with current session
      }

      // Check if there is an error in the session that indicates that the token could not be refreshed
      if (session.error) {
        console.warn(`Session error: ${session.error}, redirecting to login`);
        
        if (typeof window !== 'undefined') {
          window.location.href = '/login?error=token_refresh_failed';
        }
        
        return Promise.reject({
          message: `Session error: ${session.error}`,
          status: 401
        });
      }

      if (!config.headers) {
        config.headers = {};
      }

      config.headers.Authorization = `Bearer ${session.accessToken}`;
      console.log("Sending token to backend:", session.accessToken);
      
      return config;
      
    } catch (error) {
      console.error('Error getting session:', error);
      return Promise.reject({
        message: 'Error getting session',
        status: 401,
        error
      });
    }
  };
  
  private handleRequestError = (error: any) => {
    return Promise.reject({
      message: 'Request error',
      status: error?.response?.status || 500,
      error
    });
  };
  
  private handleResponseError = async (error: any) => {
    if (!error.response) {
      return Promise.reject({
        message: 'Network error or server unavailable',
        status: 500
      });
    }

    const { status, data, config } = error.response;
    
    // Handle authentication errors (401)
    if (status === 401 && !config._retry) {
      // Mark this request as a retry to avoid infinite loops
      config._retry = true;
      
      try {
        // Try to get a new session to force token refresh
        const session = await getSession();
        
        // If there is a session but with an error, the refresh token has failed
        if (session?.error) {
          console.error('Session has an error, redirecting to login:', session.error);
          
          // Redirect to login (in the client)
          if (typeof window !== 'undefined') {
            // Force redirect to login page immediately
            window.location.href = '/login?error=session_expired';
            return new Promise(() => {}); // Never resolve to prevent further execution
          }
          
          return Promise.reject({
            message: 'Session expired. Please log in again.',
            status: 401
          });
        }
        
        // If the session exists and has no errors, retry the original request
        if (session?.accessToken) {
          // Try exactly once to refresh the token
          const refreshedSession = await fetch('/api/auth/session', { 
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            cache: 'no-store'
          }).then(res => res.json());
          
          // If we still have the same token after trying to refresh, redirect to login
          if (refreshedSession?.accessToken === session.accessToken) {
            console.error('Token refresh failed - token remains the same');
            if (typeof window !== 'undefined') {
              window.location.href = '/login?error=token_refresh_failed';
              return new Promise(() => {});
            }
          }
          
          // Update the token in the configuration
          config.headers.Authorization = `Bearer ${refreshedSession?.accessToken || session.accessToken}`;
          
          // Retry the original request with the new token
          return this.client(config);
        } else {
          // No access token in the session, redirect to login
          console.error('No access token in session after refresh attempt');
          if (typeof window !== 'undefined') {
            window.location.href = '/login?error=no_token';
            return new Promise(() => {}); // Never resolve to prevent further execution
          }
        }
      } catch (refreshError) {
        console.error('Error updating session:', refreshError);
        // Redirect to login on any error during refresh
        if (typeof window !== 'undefined') {
          window.location.href = '/login?error=refresh_error';
          return new Promise(() => {}); // Never resolve to prevent further execution
        }
      }
    } else if (status === 401) {
      // This is a retry that still failed, redirect to login
      console.error('Authentication retry failed, redirecting to login');
      if (typeof window !== 'undefined') {
        window.location.href = '/login?error=auth_failed';
        return new Promise(() => {}); // Never resolve to prevent further execution
      }
    }
    
    return Promise.reject({
      message: data?.detail || data?.message || 'Request error',
      status
    });
  };

  async get<T>(url: string, config?: any): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: any): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: any): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: any): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  async upload(url: string, file: File, onProgress?: (progress: number) => void): Promise<any> {
    const session = await getSession();
    if (!session?.accessToken) {
      throw new Error('No token in session');
    }

    const formData = new FormData();
    formData.append('file', file);

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
        Authorization: `Bearer ${session.accessToken}`,
      },
      onUploadProgress(progressEvent: ProgressEvent) {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    };

    const response = await this.client.post(url, formData, config);
    return response.data;
  }
}

const apiClient = new ApiClient();
export default apiClient;
