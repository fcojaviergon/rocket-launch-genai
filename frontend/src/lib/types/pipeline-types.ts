/**
 * Types related to pipelines and processing
 */

// Basic pipeline
export interface Pipeline {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  user_id: string;
  config?: PipelineConfig;
}

// Pipeline configuration
export interface PipelineConfig {
  id?: string;
  name: string;
  description: string;
  steps: PipelineStep[];
  parameters?: Record<string, any>;
  metadata?: Record<string, any>;
  type?: string;
}

// Pipeline step
export interface PipelineStep {
  id: string;
  name: string;
  type: string;
  parameters?: Record<string, any>;
  next_steps?: string[];
  condition?: string;
}

// Pipeline execution
export interface PipelineExecution {
  id: string;
  pipeline_name: string;
  status: 'pending' | 'processing' | 'running' | 'completed' | 'failed';
  result?: any;
  results?: any;
  error?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  document_id?: string;
  parameters?: Record<string, any>;
  metadata?: Record<string, any>;
}

// Batch execution
export interface BatchExecution {
  id: string;
  pipeline_name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_items: number;
  processed_items: number;
  successful_items: number;
  failed_items: number;
  created_at: string;
  updated_at: string;
  document_ids: string[];
  executions: PipelineExecution[];
}

// Pipeline processing parameters
export interface PipelineProcessParams {
  pipelineName: string;
  documentId?: string;
  parameters?: Record<string, any>;
  asyncProcessing?: boolean;
}

// Batch processing parameters
export interface BatchProcessParams {
  pipelineName: string;
  documentIds: string[];
  parameters?: Record<string, any>;
}

// Compatibility interface for existing components
export interface PipelineInfo {
  id?: string;
  name: string;
  description: string;
  type?: string;
  steps: string[];
  parameters?: Record<string, any>;
  metadata?: Record<string, any>;
}
