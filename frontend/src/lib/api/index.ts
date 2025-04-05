import apiClient from './client';
import { ENDPOINTS } from './endpoints';

/**
 * Centralized API that exposes all methods to interact with the backend
 * Organized by domain (auth, documents, pipelines)
 */
export const api = {
  // Authentication
  auth: {
    login: (credentials: { email: string; password: string }) => 
      apiClient.post(ENDPOINTS.AUTH.LOGIN, credentials),
    
    register: (userData: { email: string; password: string; name: string }) => 
      apiClient.post(ENDPOINTS.AUTH.REGISTER, userData),
    
    refreshToken: (token: string) => 
      apiClient.post(ENDPOINTS.AUTH.REFRESH, { token }),
    
    getMe: () => 
      apiClient.get(ENDPOINTS.AUTH.ME),
  },
  
  // Users
  users: {
    getAll: (page: number = 1, pageSize: number = 10, search?: string) => {
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('page_size', pageSize.toString());
      if (search) params.append('search', search);
      
      return apiClient.get(`${ENDPOINTS.USERS.LIST}?${params.toString()}`);
    },
    
    getById: (id: string) => 
      apiClient.get(ENDPOINTS.USERS.DETAIL(id)),
    
    create: (userData: { 
      email: string; 
      password: string; 
      full_name: string;
      role?: string;
      is_active?: boolean;
    }) => 
      apiClient.post(ENDPOINTS.USERS.CREATE, userData),
    
    update: (id: string, userData: {
      email?: string;
      full_name?: string;
      password?: string;
      role?: string;
      is_active?: boolean;
    }) => 
      apiClient.put(ENDPOINTS.USERS.UPDATE(id), userData),
    
    delete: (id: string) => 
      apiClient.delete(ENDPOINTS.USERS.DELETE(id)),
    
    getMe: () => 
      apiClient.get(ENDPOINTS.USERS.ME),
    
    updateMe: (userData: {
      email?: string;
      full_name?: string;
    }) => 
      apiClient.put(ENDPOINTS.USERS.ME, userData),
    
    updateMyPassword: (passwordData: {
      current_password: string;
      new_password: string;
    }) => 
      apiClient.put(`${ENDPOINTS.USERS.ME}/password`, passwordData),
  },
  
  // Chat
  chat: {
    getConversations: () => 
      apiClient.get(ENDPOINTS.CHAT.CONVERSATIONS),
    
    getConversation: (id: string) => 
      apiClient.get(`${ENDPOINTS.CHAT.CONVERSATIONS}/${id}`),
    
    createConversation: (title: string) => 
      apiClient.post(ENDPOINTS.CHAT.CONVERSATIONS, { title }),
    
    updateConversation: (id: string, title: string) => 
      apiClient.put(`${ENDPOINTS.CHAT.CONVERSATIONS}/${id}`, { title }),
    
    deleteConversation: (id: string) => 
      apiClient.delete(`${ENDPOINTS.CHAT.CONVERSATIONS}/${id}`),
    
    sendMessage: (data: {
      content: string;
      conversation_id?: string;
      model?: string;
      temperature?: number;
    }) => 
      apiClient.post(ENDPOINTS.CHAT.BASE, data),
      
    streamMessage: (data: {
      content: string;
      conversation_id?: string;
      model?: string;
      temperature?: number;
    }) => 
      // This returns a stream, it must be handled specially
      apiClient.post(ENDPOINTS.CHAT.STREAM, data),
      
    ragQuery: (data: {
      query: string;
      conversation_id?: string;
    }) => 
      apiClient.post(ENDPOINTS.CHAT.RAG, data),
  },
  
  // Documents
  documents: {
    getAll: () => 
      apiClient.get(ENDPOINTS.DOCUMENTS.LIST),
    
    getById: (id: string) => 
      apiClient.get(`${ENDPOINTS.DOCUMENTS.DETAIL(id)}?include_executions=true&include_results=true`),
    
    upload: (file: File, onProgress?: (progress: number) => void) => {
      const config = onProgress ? {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent: any) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(percentCompleted);
          }
        }
      } : { headers: { 'Content-Type': 'multipart/form-data' } };
      
      const formData = new FormData();
      formData.append('file', file, file.name);
      
      return apiClient.post(ENDPOINTS.DOCUMENTS.UPLOAD, formData, config);
    },
    
    download: (id: string) => 
      apiClient.get(ENDPOINTS.DOCUMENTS.DOWNLOAD(id), { responseType: 'blob' }),
    
    delete: (id: string) => 
      apiClient.delete(ENDPOINTS.DOCUMENTS.DETAIL(id)),
    
    process: (documentId: string, pipelineName: string, asyncProcessing: boolean = true) => 
      apiClient.post(ENDPOINTS.DOCUMENTS.PROCESS(documentId), {
        pipeline_name: pipelineName,
        async_processing: asyncProcessing
      }),
      
    // New methods for embeddings and RAG
    processEmbeddings: (documentId: string, params: { 
      model?: string; 
      chunk_size?: number; 
      chunk_overlap?: number; 
    }) => 
      apiClient.post(ENDPOINTS.DOCUMENTS.PROCESS_EMBEDDINGS(documentId), params),
      
    createEmbeddings: (documentId: string, data: { 
      embeddings: number[][]; 
      chunks_text: string[]; 
      model?: string; 
    }) => 
      apiClient.post(ENDPOINTS.DOCUMENTS.CREATE_EMBEDDINGS(documentId), data),
      
    search: (params: { 
      query: string; 
      model?: string; 
      limit?: number; 
      min_similarity?: number; 
    }) => 
      apiClient.post(ENDPOINTS.DOCUMENTS.SEARCH, params),
  },
  
  // Pipelines
  pipelines: {
    getAll: () => 
      apiClient.get(ENDPOINTS.PIPELINES.LIST),
    
    getById: (id: string) => 
      apiClient.get(ENDPOINTS.PIPELINES.DETAIL(id)),
    
    create: (data: any) => 
      apiClient.post(ENDPOINTS.PIPELINES.BASE, data),
    
    update: (id: string, data: any) => 
      apiClient.put(ENDPOINTS.PIPELINES.DETAIL(id), data),
    
    delete: (id: string) => 
      apiClient.delete(ENDPOINTS.PIPELINES.DETAIL(id)),
    
    // Configurations
    getConfigs: () => 
      apiClient.get(ENDPOINTS.PIPELINES.CONFIG),
    
    getConfig: (name: string) => 
      apiClient.get(ENDPOINTS.PIPELINES.CONFIG_DETAIL(name)),
    
    createConfig: (data: any) => 
      apiClient.post(ENDPOINTS.PIPELINES.CONFIG, data),
    
    updateConfig: (name: string, data: any) => 
      apiClient.put(ENDPOINTS.PIPELINES.CONFIG_DETAIL(name), data),
    
    deleteConfig: (name: string) => 
      apiClient.delete(ENDPOINTS.PIPELINES.CONFIG_DETAIL(name)),
    
    // Processing
    process: (data: {
      document_id: string;
      pipeline_id: string;
      async_processing?: boolean;
      parameters?: Record<string, any>;
    }) => 
      apiClient.post(ENDPOINTS.PIPELINES.PROCESS, data),
    
    batchProcess: ({
      document_ids,
      pipeline_id,
    }: {
      document_ids: string[];
      pipeline_id: string;
    }) => {
      return apiClient.post(ENDPOINTS.PIPELINES.BATCH_PROCESS, {
        document_ids,
        pipeline_id,
      });
    },
    
    getExecutionStatus: (id: string) => 
      apiClient.get(ENDPOINTS.PIPELINES.EXECUTION(id)),

    getExecutionsByDocument: (documentId: string) =>
      apiClient.get(ENDPOINTS.PIPELINES.EXECUTIONS_BY_DOCUMENT(documentId)),
    
    getBatchStatus: (id: string) => 
      apiClient.get(ENDPOINTS.PIPELINES.BATCH(id)),
    
    cancelBatch: (id: string) => 
      apiClient.delete(ENDPOINTS.PIPELINES.BATCH(id)),
  },
  
  // Completions
  completions: {
    create: (data: any) => 
      apiClient.post(ENDPOINTS.COMPLETIONS.CREATE, data),
  },

  stats: {
    getDashboard: () => 
      apiClient.get(ENDPOINTS.STATS.DASHBOARD),
    
    getAnalytics: () => 
      apiClient.get(ENDPOINTS.STATS.ANALYTICS),
  },
};

export { apiClient, ENDPOINTS };
