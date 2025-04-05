'use client';

import { useState } from 'react';
import { useApi } from '@/lib/hooks/api';
import { PipelineExecution } from '@/lib/types/pipeline-types';
import { toast } from 'sonner';
import { Document } from '@/lib/services/documents';
import { useSWRConfig } from 'swr';

// Type for the batch processing response
export interface BatchProcessResponse {
  job_id: string;
  status: string;
  total_documents: number;
}

interface ExecutionResult {
  success: Document[];
  failed: Document[];
  inProgress: Document[];
}

interface UsePipelineExecutionProps {
  onComplete?: () => void;
}

// Type for the pipeline execution parameters
interface ExecutePipelineParams {
  documentIds: string[];
  pipelineId: string;
  onSuccess?: () => void;
}

export function usePipelineExecution({ onComplete }: UsePipelineExecutionProps = {}) {
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [executions, setExecutions] = useState<Record<string, PipelineExecution>>({});
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<ExecutionResult>({
    success: [],
    failed: [],
    inProgress: []
  });
  const api = useApi();
  const { mutate } = useSWRConfig();
  const [isExecuting, setIsExecuting] = useState(false);

  /**
   * Processes a document with a pipeline
   */
  const processPipeline = async (
    documentId: string,
    pipelineId: string,
    asyncProcessing = true,
    parameters?: Record<string, any>
  ): Promise<PipelineExecution> => {
    try {
      setIsProcessing(true);
      setError(null);

      // Prepare the data for processing
      const requestData = {
        document_id: documentId,
        pipeline_id: pipelineId,
        async_processing: asyncProcessing,
        parameters: parameters || {}
      };

      // Call the API to process the document
      const response = await api.pipelines.process(requestData);
      
      // Verify that the response is a valid object
      if (response && typeof response === 'object' && 'id' in response) {
        const execution = response as PipelineExecution;
        
        // Update the state with the new execution
        setExecutions(prevExecutions => ({
          ...prevExecutions,
          [execution.id]: execution
        }));
        
        // Add the pipeline name if it is not present (it may come from the selector)
        if (!execution.pipeline_name) {
          // We would need to get the pipeline name from the global state or pass it
          // For now, we leave it empty if it does not come from the API
        }
        
        return execution;
      } else {
        throw new Error('Invalid response format when processing document');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error when processing document');
      setError(error);
      throw error;
    } finally {
      setIsProcessing(false);
    }
  };

  /**
   * Gets the status of an execution by its ID
   */
  const getExecutionStatus = async (executionId: string): Promise<PipelineExecution> => {
    try {
      setIsProcessing(true);
      setError(null);

      // Call the API to get the status of the execution
      const response = await api.pipelines.getExecutionStatus(executionId);
      
      // Verify that the response is a valid object
      if (response && typeof response === 'object' && 'id' in response) {
        const execution = response as PipelineExecution;
        
        // Update the state with the updated execution
        setExecutions(prevExecutions => ({
          ...prevExecutions,
          [execution.id]: execution
        }));
        
        return execution;
      } else {
        throw new Error('Invalid response format when getting execution status');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error when getting execution status');
      setError(error);
      throw error;
    } finally {
      setIsProcessing(false);
    }
  };

  /**
   * Cancels an in-process execution
   */
  const cancelExecution = async (executionId: string): Promise<PipelineExecution> => {
    try {
      setIsProcessing(true);
      setError(null);

      // Call the API to cancel the execution
      const response = await api.pipelines.cancelExecution(executionId);
      
      // Verify that the response is a valid object
      if (response && typeof response === 'object' && 'id' in response) {
        const execution = response as PipelineExecution;
        
        // Update the state with the cancelled execution
        setExecutions(prevExecutions => ({
          ...prevExecutions,
          [execution.id]: execution
        }));
        
        return execution;
      } else {
        throw new Error('Invalid response format when cancelling execution');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error when cancelling execution');
      setError(error);
      throw error;
    } finally {
      setIsProcessing(false);
    }
  };

  /**
   * Get all executions currently in the state
   */
  const getExecutions = () => {
    return Object.values(executions);
  };

  /**
   * Get a specific execution by ID from the local state
   */
  const getExecution = (executionId: string) => {
    return executions[executionId] || null;
  };

  /**
   * Function to execute a pipeline with selected documents
   */
  const executePipeline = async ({ documentIds, pipelineId, onSuccess }: ExecutePipelineParams) => {
    try {
      setIsExecuting(true);
      
      // Import directly
      const { api } = await import('@/lib/api');
      
      // Use the UUID IDs directly without conversion
      const response = await api.pipelines.batchProcess({
        document_ids: documentIds,
        pipeline_id: pipelineId,
      });

      if (onSuccess) {
        onSuccess();
      }

      mutate(['/indexes'], true);
      mutate(['/documents'], true);
      
      return response;
    } catch (error: any) {
      const errorMessage = error?.error || 'Failed to process documents';
      toast.error(errorMessage);
      throw error;
    } finally {
      setIsExecuting(false);
    }
  };

  return {
    isProcessing,
    error,
    executions,
    progress,
    results,
    processPipeline,
    executePipeline,
    getExecutionStatus,
    cancelExecution,
    getExecutions,
    getExecution,
    reset: () => {
      setIsProcessing(false);
      setProgress(0);
      setResults({
        success: [],
        failed: [],
        inProgress: []
      });
    },
    isExecuting
  };
} 