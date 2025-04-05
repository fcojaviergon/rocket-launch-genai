'use client';

import { useState } from 'react';
import { useApi } from '@/lib/hooks/api';
import { BatchExecution } from '@/lib/types/pipeline-types';

export function useBatchExecution() {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [batches, setBatches] = useState<Record<string, BatchExecution>>({});
  const api = useApi();

  /**
   * Processes a batch of documents through a pipeline
   */
  const processBatch = async (
    pipelineId: string, 
    documentIds: string[]
  ): Promise<BatchExecution> => {
    try {
      setLoading(true);
      setError(null);

      // Call the API to process the batch
      const response = await api.pipelines.processBatch(pipelineId, documentIds);
      
      // Verify that the response is an object with id
      if (response && typeof response === 'object' && 'id' in response) {
        const batch = response as BatchExecution;
        
        // Update the state with the new batch
        setBatches(prevBatches => ({
          ...prevBatches,
          [batch.id]: batch
        }));
        
        return batch;
      } else {
        throw new Error('Invalid response format when processing batch');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error when processing batch');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Gets the status of a batch by its ID
   */
  const getBatchStatus = async (batchId: string): Promise<BatchExecution> => {
    try {
      setLoading(true);
      setError(null);

      // Call the API to get the status of the batch
      const response = await api.pipelines.getBatchStatus(batchId);
      
      // Verify that the response is an object with id
      if (response && typeof response === 'object' && 'id' in response) {
        const batch = response as BatchExecution;
        
        // Update the state with the updated batch
        setBatches(prevBatches => ({
          ...prevBatches,
          [batch.id]: batch
        }));
        
        return batch;
      } else {
        throw new Error('Invalid response format when getting batch status');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error when getting batch status');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Cancels a batch in process
   */
  const cancelBatch = async (batchId: string): Promise<BatchExecution> => {
    try {
      setLoading(true);
      setError(null);

      // Call the API to cancel the batch
      const response = await api.pipelines.cancelExecution(batchId);
      
      // Verify that the response is an object with id
      if (response && typeof response === 'object' && 'id' in response) {
        const batch = response as BatchExecution;
        
        // Update the state with the cancelled batch
        setBatches(prevBatches => ({
          ...prevBatches,
          [batch.id]: batch
        }));
        
        return batch;
      } else {
        throw new Error('Invalid response format when cancelling batch');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error when cancelling batch');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Get batches currently in the state
   */
  const getBatches = () => {
    return Object.values(batches);
  };

  /**
  * Get a specific batch by ID from the state
   */
  const getBatch = (batchId: string) => {
    return batches[batchId] || null;
  };

  return {
    loading,
    error,
    batches: getBatches(),
    processBatch,
    getBatchStatus,
    cancelBatch,
    getBatch
  };
} 