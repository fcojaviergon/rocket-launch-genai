import { useState, useCallback } from 'react';
import { api } from '@/lib/api';

/**
 * Interface for completion parameters
 */
export interface CompletionParams {
  prompt: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  stop?: string[];
}

/**
 * Interface for completion responses
 */
export interface CompletionResponse {
  id: string;
  created: number;
  model: string;
  // Possible response in choices format (standard OpenAI)
  choices?: {
    text: string;
    index: number;
    finish_reason: string;
  }[];
  // Possible direct backend response format
  text?: string;
  finish_reason?: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

/**
 * Custom hook to manage completions
 */
export function useCompletions() {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [result, setResult] = useState<CompletionResponse | null>(null);

  /**
   * Create a completion
   */
  const createCompletion = useCallback(async (params: CompletionParams) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await api.completions.create(params);
      setResult(response as CompletionResponse);
      return response as CompletionResponse;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Error creating completion'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    isLoading,
    error,
    result,
    createCompletion
  };
} 