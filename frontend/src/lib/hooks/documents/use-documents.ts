'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import type { Document } from '@/lib/types/document-types';
import { toast } from 'sonner';
import { useApi } from '../api/api-client';

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const apiClient = useApi();
  const router = useRouter();

  // Handle session loading check
  const checkSessionBeforeAction = useCallback(() => {
    if (apiClient.isSessionLoading) {
      toast.error('Please wait while authentication is loading');
      return false;
    }
    
    if (!apiClient.isSessionReady) {
      toast.error('Authentication required');
      router.push('/login');
      return false;
    }
    
    return true;
  }, [apiClient.isSessionLoading, apiClient.isSessionReady, router]);

  const fetchDocuments = useCallback(async () => {
    if (!checkSessionBeforeAction()) return [];
    
    try {
      setIsLoading(true);
      setError(null);
      const data = await apiClient.documents.getAll();
      setDocuments(data as Document[]);
      return data;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Error loading documents');
      setError(error);
      toast.error(`Failed to load documents: ${error.message}`);
      return [];
    } finally {
      setIsLoading(false);
    }
  }, [apiClient.documents, checkSessionBeforeAction]);

  const getDocument = useCallback(async (id: string) => {
    if (!checkSessionBeforeAction()) return null;
    
    try {
      setIsLoading(true);
      setError(null);
      const data = await apiClient.documents.get(id);
      return data as Document;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(`Error loading document ${id}`);
      setError(error);
      toast.error(`Failed to load document: ${error.message}`);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [apiClient.documents, checkSessionBeforeAction]);

  const uploadDocument = useCallback(async (file: File, onProgress?: (progress: number) => void) => {
    if (!checkSessionBeforeAction()) return null;

    let uploadedDoc: Document | null = null;

    try {
      setIsLoading(true);
      setError(null);

      uploadedDoc = await apiClient.documents.upload(file, onProgress) as Document;

      await fetchDocuments();
      toast.success('Document uploaded successfully');

      // --- Trigger embedding process after successful upload ---
      if (uploadedDoc && uploadedDoc.id) {
        console.log(`Attempting to trigger embeddings for document ID: ${uploadedDoc.id}`);
        try {
          api.documents.processEmbeddings(uploadedDoc.id, {})
            .then(() => {
              console.log(`Successfully SENT trigger for embedding processing for document ${uploadedDoc?.id}`);
              toast.info(`Embedding processing started for ${uploadedDoc?.title}`);
            })
            .catch((embeddingError: any) => {
              console.error(`Frontend CATCH: Failed to trigger embedding processing for document ${uploadedDoc?.id}:`, embeddingError);
              toast.error(`Failed to start embedding processing for ${uploadedDoc?.title}`);
            });
        } catch (triggerError) {
           console.error(`Frontend TRY/CATCH: Error attempting to trigger embedding processing for document ${uploadedDoc?.id}:`, triggerError);
           toast.error(`Error initiating embedding processing for ${uploadedDoc?.title}`);
        }
      } else {
        console.error('CRITICAL: Document ID missing after successful upload! Cannot trigger embeddings.');
        toast.warning('Document uploaded, but could not start embedding processing (missing ID).');
      }
      // --- End Trigger ---

      return uploadedDoc;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Error uploading document');
      setError(error);
      toast.error(`Failed to upload document: ${error.message}`);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [apiClient.documents, checkSessionBeforeAction, fetchDocuments]);

  const downloadDocument = useCallback((id: string, filename?: string) => {
    if (!checkSessionBeforeAction()) return false;
    
    try {
      setIsLoading(true);
      apiClient.documents.download(id, filename);
      return true;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(`Error downloading document ${id}`);
      setError(error);
      toast.error(`Failed to download document: ${error.message}`);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [apiClient.documents, checkSessionBeforeAction]);

  const deleteDocument = useCallback(async (id: string) => {
    if (!checkSessionBeforeAction()) return false;
    
    try {
      setIsLoading(true);
      setError(null);
      await apiClient.documents.delete(id);
      toast.success('Document deleted successfully');
      await fetchDocuments(); // Update the list of documents
      return true;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(`Error deleting document ${id}`);
      setError(error);
      toast.error(`Failed to delete document: ${error.message}`);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [apiClient.documents, checkSessionBeforeAction, fetchDocuments]);

  const processDocument = useCallback(async (
    documentId: string, 
    pipelineName: string, 
    asyncProcessing: boolean = true
  ) => {
    if (!checkSessionBeforeAction()) return null;
    
    try {
      setIsLoading(true);
      setError(null);
      const result = await apiClient.pipelines.process({
        document_id: documentId,
        pipeline_id: pipelineName,
        async_processing: asyncProcessing
      });
      toast.success('Document processing started');
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(`Error processing document ${documentId}`);
      setError(error);
      toast.error(`Failed to process document: ${error.message}`);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [apiClient.pipelines, checkSessionBeforeAction]);

  return {
    documents,
    isLoading,
    error,
    isSessionReady: apiClient.isSessionReady,
    isSessionLoading: apiClient.isSessionLoading,
    fetchDocuments,
    getDocument,
    uploadDocument,
    downloadDocument,
    deleteDocument,
    processDocument
  };
} 