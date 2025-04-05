import apiClient from '@/lib/api/client';

export interface Document {
  id: string;
  name: string;
  title?: string;
  content?: string;
  type: string;
  size: number;
  user_id?: string;
  created_at: string;
  updated_at?: string;
  processing_results?: any[];
  pipeline_executions?: any[];
}

export class DocumentService {
  /**
   * Gets all documents
   */
  static async getDocuments(): Promise<Document[]> {
    try {
      const response = await apiClient.get<Document[]>('/api/v1/documents');
      return response;
    } catch (error) {
      console.error('Error getting documents:', error);
      return [];
    }
  }

  /**
   * Gets a specific document by ID
   */
  static async getDocument(id: string): Promise<Document> {
    try {
      const response = await apiClient.get<Document>(`/api/v1/documents/${id}`);
      return response;
    } catch (error) {
      console.error(`Error getting document ${id}:`, error);
      throw error;
    }
  }

  /**
   * Deletes a document by ID
   */
  static async deleteDocument(id: string): Promise<boolean> {
    try {
      await apiClient.delete(`/api/v1/documents/${id}`);
      return true;
    } catch (error) {
      console.error(`Error deleting document ${id}:`, error);
      return false;
    }
  }

  /**
   * Processes a batch of documents with a specific pipeline
   */
  static async processBatch(documentIds: string[], pipelineId: string): Promise<boolean> {
    try {
      await apiClient.post('/api/v1/documents/process', {
        document_ids: documentIds,
        pipeline_id: pipelineId
      });
      return true;
    } catch (error) {
      console.error('Error processing documents:', error);
      return false;
    }
  }

  /**
  * Uploads a new document
   */
  static async uploadDocument(file: File, metadata?: Record<string, any>): Promise<Document> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      if (metadata) {
        formData.append('metadata', JSON.stringify(metadata));
      }
      
      const response = await apiClient.post<Document>('/api/v1/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      return response;
    } catch (error) {
      console.error('Error uploading document:', error);
      throw error;
    }
  }
} 