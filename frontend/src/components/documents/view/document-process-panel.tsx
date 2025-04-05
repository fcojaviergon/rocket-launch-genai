'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { PipelineSelector } from '@/components/pipelines/execution/pipeline-selector';
import { usePipelineExecution } from '@/lib/hooks/pipelines';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface DocumentProcessPanelProps {
  documentId: string;
  documentName: string;
  onProcessed?: () => void;
}

export function DocumentProcessPanel({ documentId, documentName, onProcessed }: DocumentProcessPanelProps) {
  const [selectedPipeline, setSelectedPipeline] = useState<string | undefined>(undefined);
  const { processPipeline, isProcessing } = usePipelineExecution();
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleProcessClick = async () => {
    if (!selectedPipeline) {
      toast.error('Select a pipeline first');
      return;
    }

    setIsLoading(true);
    try {
      const execution = await processPipeline(documentId, selectedPipeline, true);
      toast.success('Document sent for processing');
      
      setSelectedPipeline(undefined);
      if (onProcessed) onProcessed();

      if (execution && execution.id) {
        try {
          const newExecution = {
            id: execution.id,
            pipeline_name: execution.pipeline_name || 'Desconocido',
            status: execution.status || 'pending',
            created_at: execution.created_at || new Date().toISOString(),
            updated_at: execution.updated_at || new Date().toISOString(),
          };
          localStorage.setItem('new_execution', JSON.stringify(newExecution));
          router.push(`/dashboard/documents/${documentId}?execution_id=${execution.id}&tab=executions`);
        } catch (e) {
          router.push(`/dashboard/documents/${documentId}?execution_id=${execution.id}&tab=executions`);
        }
      }
    } catch (error: any) {
      console.error('Error processing document from panel:', error);
      toast.error(error.message || 'Error processing document');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <PipelineSelector 
        selectedId={selectedPipeline}
        onSelect={(id) => setSelectedPipeline(id)}
      />
      
      <Button 
        className="w-full" 
        onClick={handleProcessClick}
        disabled={!selectedPipeline || isLoading || isProcessing}
      >
        {(isLoading || isProcessing) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Process document
      </Button>
      
      {!selectedPipeline && (
        <p className="text-sm text-muted-foreground">
          Select a pipeline to process this document
        </p>
      )}
    </div>
  );
} 