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
  processing_status?: string;
  error_message?: string;
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
      
      // --- ADD LOGGING HERE ---
      console.log('Upload successful. Response:', response); 
      if (!response || !response.id) {
         console.error('CRITICAL: Document ID missing in upload response!');
         // Maybe return or throw here depending on desired behavior
      } else {
         console.log(`Attempting to trigger embeddings for document ID: ${response.id}`);
         // --- Trigger embedding process asynchronously (fire and forget) ---
         try {
           // We don't await this, just trigger it
           apiClient.post(`/api/v1/documents/process-embeddings/${response.id}`, {})
             .then(() => {
               console.log(`Successfully SENT trigger for embedding processing for document ${response.id}`); // Clarify log
             })
             .catch(embeddingError => {
               console.error(`Frontend CATCH: Failed to trigger embedding processing for document ${response.id}:`, embeddingError);
             });
         } catch (triggerError) {
           // Catch potential synchronous errors if the apiClient call itself fails immediately
           console.error(`Frontend TRY/CATCH: Error attempting to trigger embedding processing for document ${response.id}:`, triggerError);
         }
      }
      // --- End Trigger ---

      return response; // Make sure this is the original response
    } catch (error) {
      console.error('Error uploading document:', error);
      throw error;
    }
  }

  /**
   * Triggers reprocessing of embeddings for a document.
   */
  static async reprocessEmbeddings(id: string, model?: string, chunkSize?: number, chunkOverlap?: number): Promise<{ status: string; message: string; document_id: string; model: string; chunk_size: number; chunk_overlap: number }> {
    try {
      // Construct query parameters for model, chunk_size, chunk_overlap if provided
      const params = new URLSearchParams();
      if (model) params.append('model', model);
      if (chunkSize !== undefined) params.append('chunk_size', String(chunkSize));
      if (chunkOverlap !== undefined) params.append('chunk_overlap', String(chunkOverlap));
      const queryString = params.toString();
      
      const response = await apiClient.post<{ status: string; message: string; document_id: string; model: string; chunk_size: number; chunk_overlap: number }>(`/api/v1/documents/reprocess-embeddings/${id}${queryString ? '?' + queryString : ''}`);
      return response; // Now matches the actual expected response
    } catch (error) {
      console.error(`Error triggering reprocessing for document ${id}:`, error);
      // Re-throw or handle specific error types if needed
      throw error; 
    }
  }
} 