import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PipelineSelector } from './pipeline-selector';
import { Progress } from '@/components/ui/progress';
import { Document } from '@/lib/services/documents';
import { toast } from 'sonner';
import { Zap, CheckCircle, XCircle, Loader2, AlertCircle, PlusCircle } from 'lucide-react';
import { usePipelineExecution } from '@/lib/hooks/pipelines/use-pipeline-execution';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuth } from '@/lib/hooks/auth';
import { usePipelineConfig } from '@/lib/hooks/pipelines/use-pipeline-config';
import { useApi } from '@/lib/hooks/api';

interface ProcessDocumentsProps {
  documents: Document[];
  onProcessComplete: () => void;
}

export function ProcessDocuments({ documents, onProcessComplete }: ProcessDocumentsProps) {
  const [selectedPipeline, setSelectedPipeline] = useState<string>('');
  const [isCreatingPipeline, setIsCreatingPipeline] = useState(false);
  const { 
    executePipeline, 
    isProcessing, 
    progress, 
    results,
    error: processingError 
  } = usePipelineExecution({
    onComplete: onProcessComplete
  });
  const { isAuthenticated } = useAuth();
  const { configs, loadPipelines } = usePipelineConfig();
  const api = useApi();

  console.log('ProcessDocuments - state:', { 
    selectedPipeline, 
    isProcessing, 
    progress, 
    isAuthenticated,
    documentsCount: documents?.length || 0,
    configsCount: configs?.length || 0
  });
  
  // Automatically select the first pipeline if none is selected
  useEffect(() => {
    if (configs && configs.length > 0 && !selectedPipeline && configs[0].id) {
      console.log('ProcessDocuments - Automatically selecting the first pipeline:', configs[0].id);
      setSelectedPipeline(configs[0].id);
    }
  }, [configs, selectedPipeline]);

  // Check if there are no pipelines available
  const noPipelines = !isProcessing && configs.length === 0;

  // Create a test pipeline when there are none
  const createTestPipeline = async () => {
    try {
      setIsCreatingPipeline(true);
      console.log('Creating a test pipeline from ProcessDocuments...');
      
      // Create a basic test pipeline
      const testPipeline = {
        name: "Pipeline de Extracción",
        description: "Pipeline para extraer información de documentos",
        type: "pdf",
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
      const response = await api.pipelines.createConfig(testPipeline) as any;
      console.log('Test pipeline created:', response);
      
      // Reload the pipeline list
      await loadPipelines();
      
      // If created correctly, automatically select it
      if (response && response.id) {
        setSelectedPipeline(response.id);
        toast.success('Pipeline created and selected');
      } else {
        toast.success('Pipeline created correctly');
      }
    } catch (err) {
      console.error('Error creating test pipeline:', err);
      toast.error('Error creating test pipeline');
    } finally {
      setIsCreatingPipeline(false);
    }
  };

  const handleProcess = async () => {
    if (!selectedPipeline) {
      toast.error('Select a pipeline to process the documents');
      return;
    }

    console.log('Starting processing with pipeline:', selectedPipeline);
    console.log('Documents to process:', documents);
    
    try {
      const result = await executePipeline({
        pipelineId: selectedPipeline,
        documentIds: documents.map(doc => doc.id)
      });
      console.log('Execution result:', result);
    } catch (error) {
      console.error('Error in handleProcess:', error);
    }
  };

  // Callback para la selección de pipeline
  const handlePipelineSelect = (id: string) => {
    console.log('Pipeline selected:', id);
    setSelectedPipeline(id);
  };

  if (!isAuthenticated) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Process documents</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4 mr-2" />
            <AlertDescription>
              You must login to process documents
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (processingError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Processing error</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4 mr-2" />
            <AlertDescription>
              {processingError instanceof Error 
                ? processingError.message 
                : 'Error processing documents'}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Process {documents.length} documents</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <Label>Select a pipeline</Label>
            <PipelineSelector 
              onSelect={handlePipelineSelect}
              selectedId={selectedPipeline}
            />
            
            {noPipelines && (
              <div className="mt-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  className="w-full"
                  onClick={createTestPipeline}
                  disabled={isCreatingPipeline}
                >
                  {isCreatingPipeline ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Creating pipeline...
                    </>
                  ) : (
                    <>
                      <PlusCircle className="h-4 w-4 mr-2" />
                      Create automatically pipeline
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
          
          {isProcessing && (
            <div className="space-y-4 mt-4">
              <Progress value={progress} className="h-2" />
              <p className="text-sm text-center text-muted-foreground">
                Processing document {results.success.length + results.failed.length} of {documents.length}
              </p>
              
              <div className="flex justify-between text-sm mt-4">
                <div className="flex items-center">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-1" />
                  <span>Processed: {results.success.length}</span>
                </div>
                <div className="flex items-center">
                  <XCircle className="h-4 w-4 text-red-500 mr-1" />
                  <span>Failed: {results.failed.length}</span>
                </div>
              </div>
            </div>
          )}
          
          <div className="flex justify-end mt-4">
            <Button 
              onClick={handleProcess}
              disabled={isProcessing || !selectedPipeline}
              className="w-full"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4 mr-2" />
                  Start processing
                </>
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
} 