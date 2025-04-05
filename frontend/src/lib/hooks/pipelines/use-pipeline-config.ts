'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { toast } from 'sonner';
import { useApi } from '@/lib/hooks/api';
import { PipelineConfig } from '@/lib/types/pipeline-types';

export function usePipelineConfig() {
  const [configs, setConfigs] = useState<PipelineConfig[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const api = useApi();
  const router = useRouter();
  const { status } = useSession();
  const fetchAttemptsRef = useRef(0);
  const MAX_RETRY_ATTEMPTS = 3;
  const loadedOnceRef = useRef(false);

  const loadPipelines = useCallback(async () => {
    if (loadedOnceRef.current || status !== 'authenticated') {
        if (loadedOnceRef.current) console.log("loadPipelines: Skipping, already loaded once.");
        else console.log("loadPipelines: Skipping, not authenticated.");
        if (isLoading) setIsLoading(false);
        return;
    }

    if (fetchAttemptsRef.current >= MAX_RETRY_ATTEMPTS) {
      console.log(`Maximum of ${MAX_RETRY_ATTEMPTS} attempts reached`);
      setError(`Could not load configurations after ${MAX_RETRY_ATTEMPTS} attempts`);
      return;
    }

    setIsLoading(true);
    setError(null);
    fetchAttemptsRef.current += 1;

    try {
      console.log(`Loading pipeline configurations (attempt ${fetchAttemptsRef.current})`);
      console.log('Using api.pipelines.getConfigs()');
      
      try {
        console.log('API client:', api);
        console.log('api.pipelines:', api.pipelines);
      } catch (e) {
        console.error('Error inspecting API client:', e);
      }
      
      const response = await api.pipelines.getConfigs();
      console.log('Configurations loaded (raw):', response);
      
      if (Array.isArray(response)) {
        console.log('Response is an array with', response.length, 'elements');
        setConfigs(response as PipelineConfig[]);
        loadedOnceRef.current = true;
      } else {
        console.error('Unexpected response when getting pipelines:', response);
        console.error('Response type:', typeof response);
        toast.error('Error loading pipelines: unexpected format');
        setConfigs([]);
        loadedOnceRef.current = false;
      }
      
      setError(null);
      fetchAttemptsRef.current = 0;
    } catch (err: any) {
      console.error('Error loading configurations:', err);
      
      if (err.status === 401 || err.message?.includes('401') || err.message?.includes('No autenticado') || err.message?.includes('expirada')) {
        console.error('Authentication error when loading pipelines');
        toast.error('Session expired or user not authenticated');
        setError('Session expired or user not authenticated');
        
        if (typeof window !== 'undefined') {
          setTimeout(() => {
            router.push('/login');
          }, 1500);
        }
        
        fetchAttemptsRef.current = MAX_RETRY_ATTEMPTS;
      } else {
        toast.error(`Error: ${err.message || 'Unknown error'}`);
        setError(`Error loading configurations: ${err.message || 'Unknown error'}`);
      }
      setConfigs([]);
    } finally {
      setIsLoading(false);
    }
  }, [status, api, router, isLoading]);

  useEffect(() => {
    console.log(`usePipelineConfig Effect: status=${status}, loadedOnce=${loadedOnceRef.current}`);
    if (status === 'authenticated' && !loadedOnceRef.current) {
        console.log("usePipelineConfig: Triggering initial load.");
        loadPipelines();
    } else if (status !== 'authenticated') {
        console.log("usePipelineConfig: Status not authenticated, resetting loaded flag and configs.");
        loadedOnceRef.current = false;
        setConfigs([]);
    }
  }, [status, loadPipelines]);

  const createPipeline = useCallback(async (config: PipelineConfig) => {
    setIsLoading(true);
    try {
      const response = await api.pipelines.createConfig(config);
      
      if (response && typeof response === 'object') {
        await loadPipelines();
        return response as PipelineConfig;
      } else {
        throw new Error('Unexpected response when creating pipeline');
      }
    } catch (err: any) {
      console.error('Error creating pipeline:', err);
      const error = err instanceof Error ? err : new Error('Unknown error when creating pipeline');
      setError(error.message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [api, loadPipelines]);

  const updatePipeline = useCallback(async (name: string, config: PipelineConfig) => {
    setIsLoading(true);
    try {
      const response = await api.pipelines.updateConfig(name, config);
      
      if (response && typeof response === 'object') {
        await loadPipelines();
        return response as PipelineConfig;
      } else {
        throw new Error('Unexpected response when updating pipeline');
      }
    } catch (err: any) {
      console.error('Error updating pipeline:', err);
      const error = err instanceof Error ? err : new Error('Unknown error when updating pipeline');
      setError(error.message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [api, loadPipelines]);

  const deletePipeline = useCallback(async (name: string) => {
    setIsLoading(true);
    try {
      await api.pipelines.deleteConfig(name);
      await loadPipelines();
      return true;
    } catch (err: any) {
      console.error('Error deleting pipeline:', err);
      const error = err instanceof Error ? err : new Error('Unknown error when deleting pipeline');
      setError(error.message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [api, loadPipelines]);

  const getPipeline = useCallback((id: string): PipelineConfig | undefined => {
    return configs.find(p => p.id === id);
  }, [configs]);

  const getPipelineByName = useCallback((name: string): PipelineConfig | undefined => {
    return configs.find(p => p.name === name);
  }, [configs]);

  const getPipelinesByType = useCallback((type: string): PipelineConfig[] => {
    return configs.filter(p => p.type === type);
  }, [configs]);

  const isDocumentTypeCompatible = useCallback((documentType: string, pipelineId: string): boolean => {
    const pipeline = getPipeline(pipelineId);
    
    if (!pipeline) return false;
    
    if (!pipeline.type) return true;
    
    return pipeline.type === documentType;
  }, [getPipeline]);

  return {
    configs,
    isLoading,
    error,
    loadPipelines,
    createPipeline,
    updatePipeline,
    deletePipeline,
    getPipeline,
    getPipelineByName,
    getPipelinesByType,
    isDocumentTypeCompatible
  };
} 