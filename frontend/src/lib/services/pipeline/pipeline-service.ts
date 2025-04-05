import { PipelineInfo, PipelineConfig } from '../../types/pipeline-types';
import { api } from '../../api';

/**
 * Service centralized for operations with Pipelines (compatibility)
 * This implementation is for maintaining compatibility with components that
 * have not yet been migrated to use the usePipelines hook
 */
export type { PipelineInfo };
export type PipelineStepConfig = {
  id: string;
  name: string;
  type: string;
  parameters?: Record<string, any>;
};

export const pipelineService = {
  /**
   * Get all available pipelines
   */
  async getPipelines(): Promise<Record<string, PipelineInfo>> {
    try {
      const response = await api.pipelines.getAll();
      
      // Convert the array to an object to maintain compatibility
      const pipelinesMap: Record<string, PipelineInfo> = {};
      
      if (Array.isArray(response)) {
        response.forEach((config: PipelineConfig) => {
          pipelinesMap[config.name] = {
            name: config.name,
            description: config.description,
            // Extract only the names of the steps to maintain compatibility
            steps: config.steps.map(step => step.name),
            parameters: config.parameters,
            metadata: config.metadata
          };
        });
      } else if (response && (response as any).data && Array.isArray((response as any).data)) {
        (response as any).data.forEach((config: PipelineConfig) => {
          pipelinesMap[config.name] = {
            name: config.name,
            description: config.description,
            steps: config.steps.map(step => step.name),
            parameters: config.parameters,
            metadata: config.metadata
          };
        });
      }
      
      return pipelinesMap;
    } catch (error) {
      console.error('Error getting pipelines:', error);
      return {};
    }
  },
  
  /**
   * Get pipeline configuration by name
   */
  async getPipelineConfig(name: string): Promise<PipelineConfig | null> {
    try {
      const config = await api.pipelines.getConfig(name);
      return config as PipelineConfig;
    } catch (error) {
      console.error(`Error getting pipeline configuration ${name}:`, error);
      return null;
    }
  },
  
  /**
   * Get all pipeline configurations
   */
  async getPipelineConfigs(): Promise<PipelineConfig[]> {
    try {
      const configs = await api.pipelines.getConfigs();
      return configs as PipelineConfig[];
    } catch (error) {
      console.error('Error getting pipeline configurations:', error);
      return [];
    }
  },
  
  /**
   * Create pipeline configuration
   */
  async createPipelineConfig(config: PipelineConfig): Promise<PipelineConfig> {
    const result = await api.pipelines.createConfig(config);
    return result as PipelineConfig;
  },
  
  /**
   * Update pipeline configuration
   */
  async updatePipelineConfig(name: string, config: PipelineConfig): Promise<PipelineConfig> {
    const result = await api.pipelines.updateConfig(name, config);
    return result as PipelineConfig;
  },
  
  /**
   * Delete pipeline configuration
   */
  async deletePipelineConfig(name: string): Promise<boolean> {
    try {
      await api.pipelines.deleteConfig(name);
      return true;
    } catch (error) {
      console.error(`Error deleting pipeline configuration ${name}:`, error);
      return false;
    }
  },
  
  /**
   * Process document with pipeline
   */
  async processDocument(documentId: string, pipelineId: string): Promise<any> {
    return await api.pipelines.process({
      pipeline_id: pipelineId,
      document_id: documentId,
      async_processing: true
    });
  },
  
  /**
   * Process document with pipeline (full parameters version)
   */
  async processDocumentWithParams(params: {
    documentId: string;
    pipelineId: string;
    asyncProcessing?: boolean;
    parameters?: Record<string, any>;
  }): Promise<any> {
    return await api.pipelines.process({
      pipeline_id: params.pipelineId,
      document_id: params.documentId,
      async_processing: params.asyncProcessing !== false,
      parameters: params.parameters || {}
    });
  },
  
  /**
   * Process batch of documents
   */
  async batchProcessDocuments(params: {
    documentIds: string[];
    pipelineId: string;
    parameters?: Record<string, any>;
  }): Promise<any> {
    return await api.pipelines.batchProcess({
      pipeline_id: params.pipelineId,
      document_ids: params.documentIds,
    });
  },
  
  /**
   * Create pipeline
   */
  async createPipeline(pipeline: Omit<PipelineInfo, 'id'>): Promise<PipelineInfo> {
    const result = await api.pipelines.create(pipeline);
    return result as PipelineInfo;
  },
  
  /**
   * Update pipeline
   */
  async updatePipeline(id: string, pipeline: Partial<PipelineInfo>): Promise<PipelineInfo> {
    const result = await api.pipelines.update(id, pipeline);
    return result as PipelineInfo;
  },
  
  /**
   * Delete pipeline
   */
  async deletePipeline(id: string): Promise<boolean> {
    try {
      await api.pipelines.delete(id);
      return true;
    } catch (error) {
      console.error(`Error deleting pipeline ${id}:`, error);
      return false;
    }
  },
}; 