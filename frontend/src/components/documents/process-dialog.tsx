'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { PipelineSelector } from '@/components/pipelines/execution/pipeline-selector';
import { usePipelineExecution } from '@/lib/hooks/pipelines';
import { useRouter } from 'next/navigation';

interface DocumentProcessDialogProps {
  documentId: string;
  documentName?: string;
  onSuccess?: () => void;
  pipelineId?: string;
  tab?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DocumentProcessDialog({ 
  documentId, 
  documentName, 
  onSuccess, 
  pipelineId,
  tab,
  open,
  onOpenChange
}: DocumentProcessDialogProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPipeline, setSelectedPipeline] = useState<string | undefined>(pipelineId);
  const { processPipeline } = usePipelineExecution();
  const router = useRouter();

  // Process document
  const processDocument = async () => {
    if (!selectedPipeline) {
      toast.error('Select a pipeline first');
      return;
    }

    try {
      setIsLoading(true);
      const execution = await processPipeline(documentId, selectedPipeline, true);
      
      toast.success('Document sent for processing');
      
      if (onSuccess) onSuccess();
      onOpenChange(false);

      // Redirect to the document page with the execution ID for monitoring
      if (execution && execution.id) {
        // Add the execution to the document page immediately
        // through localStorage for component communication
        try {
          const newExecution = {
            id: execution.id,
            pipeline_name: execution.pipeline_name || selectedPipeline,
            status: execution.status || 'pending',
            created_at: execution.created_at || new Date().toISOString(),
            updated_at: execution.updated_at || new Date().toISOString(),
          };
          
          // Save in localStorage so the page detects it
          localStorage.setItem('new_execution', JSON.stringify(newExecution));
          
          // Redirect with router.push instead of window.location.href
          if (tab && tab === 'executions') {
            router.push(`/dashboard/documents/${documentId}?execution_id=${execution.id}&tab=executions`);
          } else {
            router.push(`/dashboard/documents/${documentId}?execution_id=${execution.id}`);
          }
        } catch (e) {
          // In case of error, simply redirect
          router.push(`/dashboard/documents/${documentId}?execution_id=${execution.id}`);
        }
      }
    } catch (error: any) {
      console.error('Error processing document:', error);
      toast.error(error.message || 'Error processing document');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Process Document
          </DialogTitle>
          <DialogDescription>
            Select a pipeline to process the document "{documentName}"
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <PipelineSelector 
            onSelect={(id) => setSelectedPipeline(id)} 
            selectedId={selectedPipeline}
          />
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={processDocument} disabled={isLoading || !selectedPipeline}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Process
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 