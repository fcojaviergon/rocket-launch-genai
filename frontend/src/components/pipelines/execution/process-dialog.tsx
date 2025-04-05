'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2, FileText, Image, BarChart2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { PipelineSelector } from './pipeline-selector';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { usePipelineExecution } from '@/lib/hooks/pipelines';
import { useRouter } from 'next/navigation';

interface ProcessDialogProps {
  isOpen: boolean;
  onClose: () => void;
  documentId: string;
  documentName: string;
  onProcessed?: () => void;
  selectedPipeline?: string;
}

export function ProcessDialog({ 
  isOpen, 
  onClose, 
  documentId, 
  documentName, 
  onProcessed, 
  selectedPipeline = 'document_analysis' 
}: ProcessDialogProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [pipeline, setPipeline] = useState(selectedPipeline);
  const { processPipeline, isProcessing } = usePipelineExecution();
  const router = useRouter();

  // Determine the type of pipeline
  const getPipelineType = (pipelineName: string): string => {
    if (pipelineName.toLowerCase().includes('image')) {
      return 'image';
    } else if (pipelineName.toLowerCase().includes('data')) {
      return 'data';
    } else {
      return 'document';
    }
  };

  // Render the icon according to the pipeline type
  const renderPipelineIcon = (type: string) => {
    switch (type) {
      case 'image':
        return <Image className="h-5 w-5 text-purple-500" />;
      case 'data':
        return <BarChart2 className="h-5 w-5 text-green-500" />;
      case 'document':
      default:
        return <FileText className="h-5 w-5 text-blue-500" />;
    }
  };

  // Check document compatibility with the pipeline
  const isDocumentCompatible = (): boolean => {
    const pipelineType = getPipelineType(pipeline);
    const fileExt = documentName.split('.').pop()?.toLowerCase() || '';
    
    if (pipelineType === 'image') {
      return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(fileExt);
    } else if (pipelineType === 'data') {
      return ['csv', 'xlsx', 'xls', 'json', 'txt'].includes(fileExt);
    }
    
    return true; // Document pipelines can process any type
  };

  // Process document
  const processDocument = async () => {
    try {
      if (!isDocumentCompatible()) {
        toast.error(`The selected pipeline is not compatible with this file type (${documentName})`);
        return;
      }
      
      setIsLoading(true);
      const execution = await processPipeline(documentId, pipeline, true);
      
      toast.success('Document sent for processing');
      
      onProcessed?.();
      onClose();
      
      // Redirect to the document page with the execution ID for monitoring
      if (execution && execution.id) {
        toast.success('Process started successfully!');
        router.push(`/dashboard/documents/${documentId}?execution_id=${execution.id}`);
      }
    } catch (error: any) {
      console.error('Error processing document:', error);
      toast.error(error.message || 'Error processing the document');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {renderPipelineIcon(getPipelineType(pipeline))}
            Process Document
          </DialogTitle>
          <DialogDescription>
            Select a pipeline to process the document "{documentName}"
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <PipelineSelector 
            onSelect={setPipeline} 
            selectedId={selectedPipeline}
          />
          
          {!isDocumentCompatible() && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                {getPipelineType(pipeline) === 'image' 
                  ? 'This pipeline is designed to process image files (.jpg, .png, etc.).' 
                  : 'This pipeline is designed to process data files (.csv, .xlsx, .json, etc.).'}
              </AlertDescription>
            </Alert>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={processDocument} disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Process
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 