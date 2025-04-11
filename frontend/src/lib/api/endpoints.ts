/**
 * Centralized definition of all API endpoints
 * This allows keeping all routes in a single place and facilitates changes
 */

// Get the API version from environment variables
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';
const API_PREFIX = `/api/${API_VERSION}`;

export const ENDPOINTS = {
  AUTH: {
    LOGIN: `${API_PREFIX}/auth/login`,
    REGISTER: `${API_PREFIX}/auth/register`,
    REFRESH: `${API_PREFIX}/auth/refresh`,
    ME: `${API_PREFIX}/auth/me`,
  },

  CHAT: {
    BASE: `${API_PREFIX}/chat`,
    CONVERSATIONS: `${API_PREFIX}/chat/conversations`,
    MESSAGES: `${API_PREFIX}/chat/messages`,
    STREAM: `${API_PREFIX}/chat/stream`,
    RAG: `${API_PREFIX}/chat/rag`,
  },
  
  DOCUMENTS: {
    BASE: `${API_PREFIX}/documents`,
    LIST: `${API_PREFIX}/documents`,
    DETAIL: (id: string) => `${API_PREFIX}/documents/${id}`,
    UPLOAD: `${API_PREFIX}/documents/upload`,
    DOWNLOAD: (id: string) => `${API_PREFIX}/documents/${id}/download`,
    PROCESS: (id: string) => `${API_PREFIX}/documents/${id}/process`,
    PROCESS_EMBEDDINGS: (id: string) => `${API_PREFIX}/documents/process-embeddings/${id}`,
    CREATE_EMBEDDINGS: (id: string) => `${API_PREFIX}/documents/embeddings/${id}`,
    SEARCH: `${API_PREFIX}/documents/search`,
  },

  USERS: {
    BASE: `${API_PREFIX}/users`,
    LIST: `${API_PREFIX}/users`,
    CREATE: `${API_PREFIX}/users`,
    DETAIL: (id: string) => `${API_PREFIX}/users/${id}`,
    UPDATE: (id: string) => `${API_PREFIX}/users/${id}`,
    DELETE: (id: string) => `${API_PREFIX}/users/${id}`,
    ME: `${API_PREFIX}/users/me`,
  },
  
  PIPELINES: {
    BASE: `${API_PREFIX}/pipelines`,
    LIST: `${API_PREFIX}/pipelines`,
    DETAIL: (id: string) => `${API_PREFIX}/pipelines/${id}`,
    CONFIG: `${API_PREFIX}/pipelines/configs`,
    CONFIG_DETAIL: (name: string) => `${API_PREFIX}/pipelines/configs/${name}`,
    PROCESS: `${API_PREFIX}/pipelines/executions`,
    BATCH_PROCESS: `${API_PREFIX}/pipelines/batch-process`,
    EXECUTION: (id: string) => `${API_PREFIX}/pipelines/executions/${id}`,
    EXECUTIONS_BY_DOCUMENT: (documentId: string) => `${API_PREFIX}/pipelines/executions/by-document/${documentId}`,
    BATCH: (id: string) => `${API_PREFIX}/pipelines/batch-process/${id}`,
  },
  
  STATS: {
    DASHBOARD: `${API_PREFIX}/stats/dashboard`,
    ANALYTICS: `${API_PREFIX}/stats/analytics`,
  },
  
  COMPLETIONS: {
    CREATE: `${API_PREFIX}/completions`,
  },

  AGENT: {
    INVOKE: `${API_PREFIX}/agent/invoke`,
  }
};
