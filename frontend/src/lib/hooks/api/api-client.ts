'use client';

import { useSession } from 'next-auth/react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useCallback, useMemo } from 'react';

interface ApiOptions {
  baseUrl?: string;
  headers?: Record<string, string>;
}

// Define the response types for the different endpoints
type ApiResponse<T = any> = T;

// Class to handle API errors
export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// Main hook to access the API
export function useApi(options: ApiOptions = {}) {
  const { data: session, status: sessionStatus } = useSession();
  const router = useRouter();
  
  // Flag to track if session is fully loaded
  const isSessionReady = sessionStatus === 'authenticated' && !!session?.accessToken;
  const isSessionLoading = sessionStatus === 'loading';
  
  // Get the base URL of the API
  const getBaseUrl = useCallback(() => {
    return options.baseUrl || process.env.NEXT_PUBLIC_BACKEND_URL || '';
  }, [options.baseUrl]);
  
  // Get the API version (v1, v2, etc.)
  const getApiVersion = useCallback(() => {
    const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1';
    return `/api/${version}`;
  }, []);
  
  // Function to handle response errors
  const handleResponseError = useCallback(async (response: Response) => {
    try {
      const errorData = await response.json().catch(() => null);
      
      // Show validation error information if we are in development
      if (response.status === 422 && errorData?.detail) {
        // If detail is an array (common format in FastAPI)
        const validationErrors = Array.isArray(errorData.detail) 
          ? errorData.detail.map((err: any) => 
              `Campo ${err.loc?.join('.')} - ${err.msg}`
            ).join(', ')
          : JSON.stringify(errorData.detail);
        
        throw new ApiError(
          `Validation error: ${validationErrors}`,
          response.status
        );
      }
      
      if (response.status === 401) {
        // Just throw the error. NextAuth session handling should take over.
        // If the refresh fails later, the session object will get an error flag,
        // which can be used by UI components or context providers to redirect.
        throw new ApiError('Session expired or user not authenticated', 401);
      }
      
      throw new ApiError(
        errorData?.detail || `Error ${response.status}: ${response.statusText}`,
        response.status
      );
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        `Error ${response.status}: ${response.statusText}`,
        response.status
      );
    }
  }, [router]);
  
  // Function to perform HTTP requests
  const fetchApi = useCallback(async <T>(
    endpoint: string,
    method: string = 'GET',
    data?: any,
    customHeaders: Record<string, string> = {}
  ): Promise<ApiResponse<T>> => {
    // Check if session is loading - don't make requests until we know if user is authenticated
    if (isSessionLoading) {
      throw new ApiError('Authentication is still loading', 0);
    }
    
    // For protected endpoints, ensure we have a valid session before proceeding
    if (!endpoint.includes('/auth/login') && !endpoint.includes('/auth/register')) {
      if (!isSessionReady) {
        router.push('/login');
        throw new ApiError('Authentication required', 401);
      }
    }
    
    try {
      // Get the base URL
      const url = `${getBaseUrl()}${getApiVersion()}${endpoint}`;
      
      // Default headers
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...customHeaders
      };
      
      // Add authentication token if it is available
      if (session?.accessToken) {
        headers['Authorization'] = `Bearer ${session.accessToken}`;
      }
      
      // Request configuration
      const config: RequestInit = {
        method,
        headers,
        credentials: 'include',
        body: data ? JSON.stringify(data) : undefined,
      };
      
      // Perform the request
      const response = await fetch(url, config);
      
      // Handle the response
      if (!response.ok) {
        throw await handleResponseError(response);
      }
      
      // For 204 No Content responses (common in DELETE operations), return an empty object
      if (response.status === 204) {
        return {} as T;
      }
      
      // For normal responses, parse JSON
      const responseData = await response.json();
      return responseData;
    } catch (error) {
      if (!(error instanceof ApiError)) {
        console.error('Error in API request:', error);
      }
      throw error;
    }
  }, [getBaseUrl, getApiVersion, handleResponseError, isSessionLoading, isSessionReady, router, session]);
  
  // Definition of the available endpoints
  const api = {
    // Authentication
    auth: {
      login: useCallback((email: string, password: string) => 
        fetchApi('/auth/login', 'POST', { email, password }), [fetchApi]),
      
      register: useCallback((name: string, email: string, password: string) => 
        fetchApi('/auth/register', 'POST', { name, email, password }), [fetchApi]),
      
      forgotPassword: useCallback((email: string) => 
        fetchApi('/auth/forgot-password', 'POST', { email }), [fetchApi]),
      
      resetPassword: useCallback((token: string, password: string) => 
        fetchApi('/auth/reset-password', 'POST', { token, password }), [fetchApi]),
      
      me: useCallback(() => fetchApi('/auth/me', 'GET'), [fetchApi]),
    },
    
    // Documents
    documents: {
      getAll: useCallback(() => fetchApi('/documents'), [fetchApi]),
      
      get: useCallback((id: string) => fetchApi(`/documents/${id}`), [fetchApi]),
      
      create: useCallback((data: any) => fetchApi('/documents', 'POST', data), [fetchApi]),
      
      update: useCallback((id: string, data: any) => 
        fetchApi(`/documents/${id}`, 'PUT', data), [fetchApi]),
      
      delete: useCallback((id: string) => fetchApi(`/documents/${id}`, 'DELETE'), [fetchApi]),
      
      download: useCallback((id: string, filename?: string) => {
        if (!isSessionReady) {
          toast.error('Authentication required to download files');
          return;
        }
        
        const downloadUrl = `${getBaseUrl()}${getApiVersion()}/documents/${id}/download`;
        
        fetch(downloadUrl, {
          headers: {
            'Authorization': `Bearer ${session!.accessToken}`
          }
        })
        .then(response => {
          if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
          }
          return response.blob();
        })
        .then(blob => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename || `document-${id}`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        })
        .catch(error => {
          console.error('Error downloading document:', error);
          toast.error('Error downloading document');
        });
      }, [fetchApi, getApiVersion, getBaseUrl, isSessionReady, session]),
      
      upload: useCallback(async (file: File, onProgress?: (progress: number) => void) => {
        if (!isSessionReady) {
          throw new ApiError('Authentication required to upload files', 401);
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        return new Promise<any>((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          const apiVersion = getApiVersion();
          xhr.open('POST', `${getBaseUrl()}${apiVersion}/documents/upload`);
          
          xhr.setRequestHeader('Authorization', `Bearer ${session!.accessToken}`);
          
          // Configure event listeners
          xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable && onProgress) {
              const progress = Math.round((event.loaded / event.total) * 100);
              onProgress(progress);
            }
          });
          
          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              try {
                const response = JSON.parse(xhr.responseText);
                resolve(response);
              } catch (e) {
                reject(new ApiError('Error processing the response', xhr.status));
              }
            } else {
              let errorData;
              try {
                errorData = JSON.parse(xhr.responseText);
              } catch (e) {
                errorData = { message: 'Error uploading the file' };
              }
              
              reject(new ApiError(
                errorData.message || errorData.detail || 'Error uploading the file', 
                xhr.status,
                errorData
              ));
            }
          };
          
          xhr.onerror = () => {
            reject(new ApiError('Network error when uploading the file', 0));
          };
          
          xhr.send(formData);
        });
      }, [fetchApi, getApiVersion, getBaseUrl, isSessionReady, session]),
    },
    
    // Pipelines
    pipelines: {
      getConfigs: useCallback(() => fetchApi('/pipelines/configs'), [fetchApi]),
      
      getConfig: useCallback((id: string) => 
        fetchApi(`/pipelines/configs/${id}`), [fetchApi]),
      
      createConfig: useCallback((data: any) => 
        fetchApi('/pipelines/configs', 'POST', data), [fetchApi]),
      
      updateConfig: useCallback((id: string, data: any) => 
        fetchApi(`/pipelines/configs/${id}`, 'PUT', data), [fetchApi]),
      
      deleteConfig: useCallback((id: string) => 
        fetchApi(`/pipelines/configs/${id}`, 'DELETE'), [fetchApi]),
      
      getPipelines: useCallback(() => fetchApi('/pipelines'), [fetchApi]),
      
      getPipeline: useCallback((id: string) => 
        fetchApi(`/pipelines/${id}`), [fetchApi]),
      
      createPipeline: useCallback((data: any) => 
        fetchApi('/pipelines', 'POST', data), [fetchApi]),
      
      updatePipeline: useCallback((id: string, data: any) => 
        fetchApi(`/pipelines/${id}`, 'PUT', data), [fetchApi]),
      
      deletePipeline: useCallback((id: string) => 
        fetchApi(`/pipelines/${id}`, 'DELETE'), [fetchApi]),
      
      process: useCallback((data: any) => 
        fetchApi('/pipelines/executions', 'POST', data), [fetchApi]),
      
      processBatch: useCallback((pipelineId: string, documentIds: string[]) => 
        fetchApi('/pipelines/batch-process', 'POST', { pipeline_id: pipelineId, document_ids: documentIds }), [fetchApi]),
      
      getExecutionStatus: useCallback((executionId: string) => 
        fetchApi(`/pipelines/executions/${executionId}`), [fetchApi]),
      
      getBatchStatus: useCallback((batchId: string) => 
        fetchApi(`/pipelines/batch/${batchId}`), [fetchApi]),
      
      cancelExecution: useCallback((executionId: string) => 
        fetchApi(`/pipelines/executions/${executionId}/cancel`, 'POST'), [fetchApi]),
    },
    
    // Utility clients to perform arbitrary requests
    get: useCallback(<T>(endpoint: string, headers?: Record<string, string>) => 
      fetchApi<T>(endpoint, 'GET', undefined, headers), [fetchApi]),
    
    post: useCallback(<T>(endpoint: string, data: any, headers?: Record<string, string>) => 
      fetchApi<T>(endpoint, 'POST', data, headers), [fetchApi]),
    
    put: useCallback(<T>(endpoint: string, data: any, headers?: Record<string, string>) => 
      fetchApi<T>(endpoint, 'PUT', data, headers), [fetchApi]),
    
    patch: useCallback(<T>(endpoint: string, data: any, headers?: Record<string, string>) => 
      fetchApi<T>(endpoint, 'PATCH', data, headers), [fetchApi]),
    
    delete: useCallback(<T>(endpoint: string, headers?: Record<string, string>) => 
      fetchApi<T>(endpoint, 'DELETE', undefined, headers), [fetchApi]),
  };

  // Memoize the API object
  const apiMemo = useMemo(() => api, [fetchApi, getBaseUrl, getApiVersion, isSessionReady, session]);

  // Memoize the final returned object
  const result = useMemo(() => ({
    ...apiMemo,
    isSessionReady,
    isSessionLoading,
    sessionStatus
  }), [apiMemo, isSessionReady, isSessionLoading, sessionStatus]);

  return result;
} 