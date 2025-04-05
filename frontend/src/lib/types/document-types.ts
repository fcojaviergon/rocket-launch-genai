/**
 * Types related to documents
 */

// Basic document
export interface Document {
  id: string;
  title: string;
  content: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  file_path?: string;
  file_type?: string;
  file_size?: number;
  // Processing results and executions
  processing_results?: Array<{
    id: string;
    pipeline_name: string;
    summary?: string;
    keywords?: string[];
    token_count?: number;
    created_at: string;
    result?: any;
  }>;
  pipeline_executions?: Array<{
    id: string;
    pipeline_name?: string;
    status: string;
    created_at: string;
    updated_at?: string;
    completed_at?: string;
    error?: string;
    results?: any;
  }>;
}

// Document upload response
export interface DocumentUploadResponse {
  id: string;
  title: string;
  user_id: string;
  created_at: string;
}

// Document processing result
export interface DocumentProcessResult {
  id: string;
  document_id: string;
  pipeline_name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: any;
  error?: string;
  created_at: string;
  updated_at: string;
  execution_id?: string;
}

// Document upload parameters
export interface DocumentUploadParams {
  file: File;
  title?: string;
  description?: string;
}

// Document processing parameters
export interface DocumentProcessParams {
  documentId: string;
  pipelineName: string;
  asyncProcessing?: boolean;
  parameters?: Record<string, any>;
}
