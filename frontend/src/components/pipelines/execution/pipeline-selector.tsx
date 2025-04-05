'use client';

import React, { useEffect, useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Loader2 } from 'lucide-react';
import { usePipelineConfig } from '@/lib/hooks/pipelines/use-pipeline-config';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useSession } from 'next-auth/react';
import { useApi } from '@/lib/hooks/api';
import { toast } from 'sonner';

interface PipelineSelectorProps {
  onSelect: (pipelineId: string) => void;
  selectedId?: string;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
}

export function PipelineSelector({
  onSelect,
  selectedId,
  disabled = false,
  className = '',
  placeholder = 'Select pipeline...',
}: PipelineSelectorProps) {
  const { configs, isLoading, error, loadPipelines } = usePipelineConfig();
  const [noResults, setNoResults] = useState(false);
  const { status } = useSession();

  //console.log('PipelineSelector - state:', { configs, isLoading, error, authStatus: status });

  // Effect to determine if there are no results when the loading finishes
  useEffect(() => {
    if (!isLoading && configs.length === 0) {
      setNoResults(true);
      console.log('PipelineSelector - No configurations available');
    } else {
      setNoResults(false);
      if (configs.length > 0) {
        console.log('PipelineSelector - Configurations available:', configs);
        
        // If there are pipelines available and no one is selected, automatically select the first one
        if (configs.length > 0 && !selectedId && configs[0].id) {
          console.log('PipelineSelector - Automatically selecting the first pipeline:', configs[0].id);
          onSelect(configs[0].id);
        }
      }
    }
  }, [isLoading, configs, selectedId, onSelect]);

  // Function to manually reload
  const handleRetryLoad = () => {
    console.log('Attempting to reload configurations...');
    loadPipelines();
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Loading pipelines...</span>
      </div>
    );
  }

  // Show authentication error
  if (status !== 'authenticated') {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          You must login to see the pipelines
        </AlertDescription>
      </Alert>
    );
  }

  // Show general error
  if (error) {
    return (
      <div>
        <Alert className="mb-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <button
          onClick={handleRetryLoad}
          className="text-sm text-blue-500 hover:underline"
          disabled={isLoading}
        >
          {isLoading ? 'Loading...' : 'Retry load'}
        </button>
      </div>
    );
  }

  // Show no results message
  if (noResults) {
    return (
      <div>
        <div className="mb-2">
          <Select
            onValueChange={onSelect}
            disabled={disabled || configs.length === 0}
          >
            <SelectTrigger className={className}>
              <SelectValue placeholder="No pipelines available" />
            </SelectTrigger>
            <SelectContent>
              {configs.map((pipeline) => (
                <SelectItem key={pipeline.id || ''} value={pipeline.id || ''}>
                  {pipeline.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <div className="flex flex-col gap-2 mt-3">
          <Alert className="mb-2">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              No pipelines available. Please create one first.
            </AlertDescription>
          </Alert>
          
          <div className="flex flex-col gap-2">
            <button
              onClick={handleRetryLoad}
              className="text-sm text-blue-500 hover:underline"
              disabled={isLoading}
            >
              {isLoading ? 'Loading...' : 'Retry load'}
            </button>
            
            <button
              onClick={async () => {
                try {
                  console.log('Creating a test pipeline...');
                  // Create a basic test pipeline
                  const testPipeline = {
                    name: "Test Pipeline",
                    description: "Automatically created test pipeline",
                    type: "text",
                    steps: [
                      {
                        name: "extractor",
                        type: "processor",
                        config: {
                          model: "gpt-3.5-turbo"
                        }
                      }
                    ],
                    metadata: {}
                  };
                  
                  // Call the API to create the pipeline
                  const api = useApi();
                  const response = await api.pipelines.createConfig(testPipeline) as any;
                  console.log('Test pipeline created:', response);
                  
                  // Reload the pipeline list
                  loadPipelines();
                  
                  toast.success('Test pipeline created correctly');
                } catch (err) {
                  console.error('Error creating test pipeline:', err);
                  toast.error('Error creating test pipeline');
                }
              }}
              className="text-sm text-green-500 hover:underline"
            >
              Create test pipeline
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <Select
      onValueChange={onSelect}
      disabled={disabled || configs.length === 0}
    >
      <SelectTrigger className={className}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {configs.map((pipeline) => (
          <SelectItem key={pipeline.id || ''} value={pipeline.id || ''}>
            {pipeline.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
} 