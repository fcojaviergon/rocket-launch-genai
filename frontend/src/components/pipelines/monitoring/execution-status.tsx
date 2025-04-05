'use client';

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react';
import { usePipelineExecution } from '@/lib/hooks/pipelines';
import { PipelineExecution } from '@/lib/types/pipeline-types';
import { toast } from 'sonner';
import { api } from '@/lib/api';

interface ExecutionStatusProps {
  executionId: string;
  onComplete?: (result: any) => void;
  refreshInterval?: number;  // In milliseconds
  showDetails?: boolean;
}

// Function to determine the type of status
const getExecutionStatusType = (status: string | undefined): 'completed' | 'failed' | 'running' | 'pending' | 'unknown' => {
  if (!status) return 'unknown';
  
  const statusLower = status.toLowerCase();
  
  if (statusLower.includes('complet') || statusLower === 'completed' || statusLower === 'success') {
    return 'completed';
  } else if (statusLower.includes('fail') || statusLower === 'failed' || statusLower === 'error') {
    return 'failed';
  } else if (statusLower.includes('process') || statusLower.includes('run') || statusLower === 'running' || statusLower === 'processing') {
    return 'running';
  } else if (statusLower.includes('pend') || statusLower === 'pending' || statusLower === 'waiting') {
    return 'pending';
  } else {
    return 'unknown';
  }
};

export function ExecutionStatus({
  executionId,
  onComplete,
  refreshInterval = 3000,  // Default 3 seconds
  showDetails = true
}: ExecutionStatusProps) {
  const [execution, setExecution] = useState<PipelineExecution | null>(null);
  const [isPolling, setIsPolling] = useState(true);
  const [progress, setProgress] = useState(0);
  const { getExecutionStatus } = usePipelineExecution();
  const [isLocalLoading, setIsLocalLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const onCompleteCalled = useRef(false);

  // Function to get the execution status directly using the API
  const fetchStatusDirectly = async () => {
    try {
      setIsLocalLoading(true);
      setError(null);
      
      console.log(`Getting status for execution ID: ${executionId}`);
      
      // Use directly the API
      const status = await api.pipelines.getExecutionStatus(executionId);
      
      console.log('Status obtained directly:', status);
      
      // Ensure the status is of the expected type
      if (status && typeof status === 'object' && 'status' in status) {
        setExecution(status as PipelineExecution);
        
        // Calculate progress
        const typedStatus = status as PipelineExecution;
        const statusType = getExecutionStatusType(typedStatus.status);
        
        if (statusType === 'completed') {
          setProgress(100);
          setIsPolling(false);
          if (!onCompleteCalled.current && onComplete) {
            console.log('Calling onComplete for the first time');
            onCompleteCalled.current = true;
            onComplete(typedStatus.result);
          }
        } else if (statusType === 'failed') {
          setProgress(100);
          setIsPolling(false);
          if (!onCompleteCalled.current) {
            onCompleteCalled.current = true;
            // Do not call onComplete in case of failure, only mark as called
          }
          const errorMsg = typedStatus.error || 'Unknown error';
          console.error('Processing failed:', errorMsg);
          toast.error('Processing failed: ' + errorMsg);
        } else if (statusType === 'running') {
          // If there is progress information in the metadata
          if (typedStatus.metadata?.progress) {
            setProgress(Number(typedStatus.metadata.progress));
          } else {
            // Indeterminate progress, show generic something
            setProgress((prev) => Math.min(prev + 5, 90));
          }
        } else if (statusType === 'pending') {
          // For pending
          setProgress(10);
        } else {
          // Unknown status
          setProgress(0);
          console.warn('Unknown execution status:', typedStatus.status);
        }
      } else {
        console.error('Unexpected response format:', status);
        setError('Error in response format');
      }
    } catch (error: any) {
      console.error('Error getting status:', error);
      
      // More detailed information about the error
      const errorMsg = error.message || 'Error checking the processing status';
      console.error('Full error message:', errorMsg);
      
      setError(errorMsg);
      
      // If we have failed many times, stop trying
      if (retryCount > 3) {
        setIsPolling(false);
        toast.error('Could not check the status after several attempts');
      } else {
        setRetryCount(prev => prev + 1);
      }
    } finally {
      setIsLocalLoading(false);
    }
  };

  // Function to get the status using the hook
  const fetchStatus = async () => {
    try {
      setIsLocalLoading(true);
      setError(null);
      
      console.log(`Getting status for execution: ${executionId} (using hook)`);
      
      // First we try to use the hook
      const status = await getExecutionStatus(executionId);
      
      console.log('Status obtained with hook:', status);
      
      // If we get here, the hook worked correctly
      if (status && typeof status === 'object' && 'status' in status) {
        setExecution(status as PipelineExecution);
        
        // Calculate progress
        const typedStatus = status as PipelineExecution;
        const statusType = getExecutionStatusType(typedStatus.status);
        
        if (statusType === 'completed') {
          setProgress(100);
          setIsPolling(false);
          if (!onCompleteCalled.current && onComplete) {
            console.log('Calling onComplete for the first time');
            onCompleteCalled.current = true;
            onComplete(typedStatus.result);
          }
        } else if (statusType === 'failed') {
          setProgress(100);
          setIsPolling(false);
          if (!onCompleteCalled.current) {
            onCompleteCalled.current = true;
            // No llamamos a onComplete en caso de fallo, solo marcamos como llamada
          }
          const errorMsg = typedStatus.error || 'Unknown error';
          console.error('Processing failed:', errorMsg);
          toast.error('Processing failed: ' + errorMsg);
        } else if (statusType === 'running') {
          // If there is progress information in the metadata
          if (typedStatus.metadata?.progress) {
            setProgress(Number(typedStatus.metadata.progress));
          } else {
            // Indeterminate progress, show generic something
            setProgress((prev) => Math.min(prev + 5, 90));
          }
        } else if (statusType === 'pending') {
          // For pending
          setProgress(10);
        } else {
          // Unknown status
          setProgress(0);
          console.warn('Unknown execution status:', typedStatus.status);
        }
        
        // Reset retry counter if we had success
        setRetryCount(0);
      } else {
        console.error('Unexpected response format from hook:', status);
        // If the format fails, try with the direct method
        await fetchStatusDirectly();
      }
    } catch (error: any) {
      console.error('Error getting status with hook:', error);
      // If the hook fails, try with the direct method
      await fetchStatusDirectly();
    } finally {
      setIsLocalLoading(false);
    }
  };

  // Force a manual status check
  const manualRefresh = async () => {
    try {
      await fetchStatusDirectly();
      toast.success('Status updated');
    } catch (error) {
      console.error('Error updating status manually:', error);
      toast.error('Error updating status');
    }
  };

  // Effect to start the status check
  useEffect(() => {
    if (!executionId) {
      console.error('Execution ID not provided');
      setError('Invalid execution ID');
      return;
    }
    
    console.log(`Starting monitoring for execution ID: ${executionId}`);
    fetchStatus();
    
    let intervalId: NodeJS.Timeout;
    
    if (isPolling) {
      intervalId = setInterval(fetchStatus, refreshInterval);
    }
    
    // Reset onCompleteCalled if the executionId changes
    onCompleteCalled.current = false;

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [executionId, isPolling, refreshInterval]);

  // Render the component according to the status
  const getStatusBadge = () => {
    const statusType = getExecutionStatusType(execution?.status);
    
    switch (statusType) {
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800">Pending</Badge>;
      case 'running':
        return <Badge className="bg-blue-100 text-blue-800">Processing</Badge>;
      case 'completed':
        return <Badge className="bg-green-100 text-green-800">Completed</Badge>;
      case 'failed':
        return <Badge className="bg-red-100 text-red-800">Failed</Badge>;
      default:
        return <Badge className="bg-gray-100 text-gray-800">Unknown</Badge>;
    }
  };

  // Render the icon according to the status
  const getStatusIcon = () => {
    const statusType = getExecutionStatusType(execution?.status);
    
    switch (statusType) {
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'running':
        return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  if (!execution && isLocalLoading) {
    return (
      <div className="flex items-center justify-center p-6">
        <RefreshCw className="h-6 w-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  if (error && !execution) {
    return (
      <Card>
        <CardHeader className="bg-red-50 text-red-700">
          <CardTitle className="flex items-center">
            <AlertCircle className="h-5 w-5 mr-2" />
            Error checking status
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <p className="mb-4 text-sm">{error}</p>
          <div className="flex justify-end">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={manualRefresh}
              disabled={isLocalLoading}
            >
              {isLocalLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-1" />
              )}
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center text-base">
          {getStatusIcon()}
          <span className="ml-2">Status: {getStatusBadge()}</span>
          
          {isPolling && (execution?.status === 'processing' || execution?.status === 'running' || execution?.status === 'pending') && (
            <RefreshCw className="h-4 w-4 ml-2 animate-spin text-muted-foreground" />
          )}
          
          {!isPolling && (
            <Button 
              variant="ghost" 
              size="icon" 
              className="ml-auto h-6 w-6" 
              onClick={manualRefresh}
              disabled={isLocalLoading}
            >
              <RefreshCw className={`h-4 w-4 ${isLocalLoading ? 'animate-spin' : ''}`} />
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-4">
          <Progress value={progress} />
          
          {(() => {
            const statusType = getExecutionStatusType(execution?.status);

            switch (statusType) {
              case 'running':
                return (
                  <p className="text-sm text-muted-foreground">
                    Processing document... {progress > 0 ? `${progress}%` : ''}
                  </p>
                );
              case 'pending':
                return (
                  <p className="text-sm text-muted-foreground">
                    Waiting to start processing...
                  </p>
                );
              case 'completed':
                return (
                  <p className="text-sm text-green-600">
                    Processing completed successfully.
                  </p>
                );
              case 'failed':
                return (
                  <div>
                    <p className="text-sm text-red-600">
                      Processing failed: {execution?.error || 'Unknown error'}
                    </p>
                  </div>
                );
              default:
                return (
                  <p className="text-sm text-muted-foreground">
                    Status: {execution?.status || 'Unknown'}
                  </p>
                );
            }
          })()}
          
          {showDetails && execution && (
            <div className="text-xs text-muted-foreground border-t pt-2 mt-4">
              <p>ID: {execution.id}</p>
              <p>Pipeline: {execution.pipeline_name || 'Unknown'}</p>
              <p>Started: {new Date(execution.created_at).toLocaleString()}</p>
              {execution.updated_at && execution.updated_at !== execution.created_at && (
                <p>Last update: {new Date(execution.updated_at).toLocaleString()}</p>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
} 