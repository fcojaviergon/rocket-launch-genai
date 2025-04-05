'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, AlertCircle, CheckCircle, Clock, XCircle, StopCircle } from 'lucide-react';
import { useBatchExecution } from '@/lib/hooks/pipelines';
import { BatchExecution } from '@/lib/types/pipeline-types';
import { toast } from 'sonner';

interface BatchStatusProps {
  batchId: string;
  onComplete?: (result: BatchExecution) => void;
  refreshInterval?: number;  // In milliseconds
  showDetails?: boolean;
}

export function BatchStatus({
  batchId,
  onComplete,
  refreshInterval = 5000,  // Default 5 seconds
  showDetails = true
}: BatchStatusProps) {
  const [batch, setBatch] = useState<BatchExecution | null>(null);
  const [isPolling, setIsPolling] = useState(true);
  const [isLocalLoading, setIsLocalLoading] = useState(false);
  const { getBatchStatus, cancelBatch } = useBatchExecution();

  // Function to get the batch status
  const fetchStatus = async () => {
    try {
      setIsLocalLoading(true);
      const status = await getBatchStatus(batchId);
      
      // Ensure the status is of the expected type
      if (status && typeof status === 'object' && 'status' in status) {
        setBatch(status as BatchExecution);
        
        // If it's finished, stop the polling
        const typedStatus = status as BatchExecution;
        if (typedStatus.status === 'completed' || typedStatus.status === 'failed') {
          setIsPolling(false);
          
          if (typedStatus.status === 'completed') {
            toast.success(`Batch processing completed: ${typedStatus.successful_items}/${typedStatus.total_items} documents processed correctly`);
            onComplete?.(typedStatus);
          } else if (typedStatus.status === 'failed') {
            toast.error(`Batch processing failed: ${typedStatus.failed_items}/${typedStatus.total_items} documents failed`);
          }
        }
      } else {
        console.error('Unexpected response format:', status);
        toast.error('Error in response format');
      }
    } catch (error) {
      console.error('Error getting batch status:', error);
      setIsPolling(false);
      toast.error('Error checking batch processing status');
    } finally {
      setIsLocalLoading(false);
    }
  };

  // Handle batch cancellation
  const handleCancelBatch = async () => {
    try {
      await cancelBatch(batchId);
      toast.success('Batch processing cancelled');
      fetchStatus(); // Update status
    } catch (error) {
      console.error('Error cancelling batch:', error);
      toast.error('Error cancelling batch processing');
    }
  };

  // Effect to start the status query
  useEffect(() => {
    fetchStatus();
    
    let intervalId: NodeJS.Timeout;
    
    if (isPolling) {
      intervalId = setInterval(fetchStatus, refreshInterval);
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [batchId, isPolling, refreshInterval]);

  // Calculate progress percentage
  const calculateProgress = () => {
    if (!batch) return 0;
    
    if (batch.total_items === 0) return 0;
    return Math.round((batch.processed_items / batch.total_items) * 100);
  };

  // Render the component according to the status
  const getStatusBadge = () => {
    const status = batch?.status || 'unknown';
    
    switch (status) {
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800">Pending</Badge>;
      case 'processing':
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
    const status = batch?.status || 'unknown';
    
    switch (status) {
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'processing':
        return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  if (!batch && isLocalLoading) {
    return (
      <div className="flex items-center justify-center p-6">
        <RefreshCw className="h-6 w-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle className="text-base flex items-center gap-2">
            {getStatusIcon()}
            Batch processing
          </CardTitle>
          {getStatusBadge()}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {batch && (
          <>
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Progress</span>
                <span>{calculateProgress()}%</span>
              </div>
              <Progress value={calculateProgress()} className="h-2" />
            </div>
            
            <div className="grid grid-cols-2 text-sm gap-x-4 gap-y-2">
              <div>Documents:</div>
              <div>{batch.total_items}</div>
              
              <div>Processed:</div>
              <div>{batch.processed_items}</div>
              
              <div>Success:</div>
              <div className="text-green-600">{batch.successful_items}</div>
              
              <div>Failed:</div>
              <div className="text-red-600">{batch.failed_items}</div>
            </div>
            
            {showDetails && (
              <div className="space-y-2 mt-4">
                <div className="text-xs text-muted-foreground">Details</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="font-medium">Pipeline:</div>
                  <div>{batch.pipeline_name}</div>
                  
                  <div className="font-medium">Started:</div>
                  <div>{new Date(batch.created_at).toLocaleString()}</div>
                  
                  {batch.updated_at && (
                    <>
                      <div className="font-medium">Updated:</div>
                      <div>{new Date(batch.updated_at).toLocaleString()}</div>
                    </>
                  )}
                </div>
              </div>
            )}
            
            <div className="flex flex-col gap-2 mt-2">
              {batch.status === 'processing' && (
                <Button 
                  variant="destructive" 
                  size="sm"
                  onClick={handleCancelBatch}
                >
                  <StopCircle className="h-4 w-4 mr-2" />
                  Cancel batch processing
                </Button>
              )}
              
              {!isPolling && batch.status !== 'completed' && (
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => {
                    fetchStatus();
                    // Only restart the polling if it's processing or pending
                    if (batch.status === 'processing' || batch.status === 'pending') {
                      setIsPolling(true);
                    }
                  }}
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Check status
                </Button>
              )}
              
              {batch.status === 'completed' && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => onComplete?.(batch)}
                >
                  View results
                </Button>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
} 