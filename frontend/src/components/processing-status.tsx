import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardFooter, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Check, X, RotateCw, Clock, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import axios from 'axios';

interface ProcessingStatusProps {
  executionId?: string;
  batchId?: string;
  onComplete?: (result: any) => void;
  refreshInterval?: number;
}

type StatusType = 'pending' | 'running' | 'processing' | 'completed' | 'failed' | 'canceled';

const statusColors: Record<StatusType, string> = {
  pending: 'bg-blue-100 text-blue-800 border-blue-200',
  running: 'bg-blue-100 text-blue-800 border-blue-200',
  processing: 'bg-blue-100 text-blue-800 border-blue-200',
  completed: 'bg-green-100 text-green-800 border-green-200',
  failed: 'bg-red-100 text-red-800 border-red-200',
  canceled: 'bg-orange-100 text-orange-800 border-orange-200'
};

const statusIcons: Record<StatusType, React.ReactNode> = {
  pending: <Clock className="h-4 w-4" />,
  running: <Clock className="h-4 w-4" />,
  processing: <Clock className="h-4 w-4 animate-spin" />,
  completed: <Check className="h-4 w-4" />,
  failed: <X className="h-4 w-4" />,
  canceled: <X className="h-4 w-4" />
};

const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ 
  executionId, 
  batchId, 
  onComplete, 
  refreshInterval = 3000 
}) => {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      let response;
      
      if (executionId) {
        response = await axios.get(`/api/v1/pipeline/execution/${executionId}`);
      } else if (batchId) {
        response = await axios.get(`/api/v1/pipeline/batch/${batchId}`);
      } else {
        setError('ExecutionId or batchId is required');
        setLoading(false);
        return;
      }
      
      setStatus(response.data);
      
      // If processing has finished (completed, failed, or canceled), notify the callback
      if (
        onComplete && 
        ['completed', 'failed', 'canceled'].includes(response.data.status)
      ) {
        onComplete(response.data);
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error getting status:', err);
      setError('Error getting processing status');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    
    // Set up update interval only if status is not final
    const intervalId = setInterval(() => {
      if (
        !status || 
        !['completed', 'failed', 'canceled'].includes(status.status)
      ) {
        fetchStatus();
      }
    }, refreshInterval);
    
    return () => clearInterval(intervalId);
  }, [executionId, batchId, refreshInterval]);

  const handleRetry = async () => {
    try {
      if (!executionId) {
        toast.error("Cannot retry without an execution ID");
        return;
      }
      
      await axios.post(`/api/v1/pipeline/execution/${executionId}/retry`);
      toast.success("Processing has been successfully restarted");
      
      // Update status immediately
      fetchStatus();
    } catch (err) {
      console.error('Error retrying:', err);
      toast.error("Could not retry processing");
    }
  };

  const handleCancel = async () => {
    try {
      if (!executionId) {
        toast.error("Cannot cancel without an execution ID");
        return;
      }
      
      await axios.post(`/api/v1/pipeline/execution/${executionId}/cancel`);
      toast.success("Processing has been successfully canceled");
      
      // Update status immediately
      fetchStatus();
    } catch (err) {
      console.error('Error canceling:', err);
      toast.error("Could not cancel processing");
    }
  };

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="animate-spin mr-2">
          <RotateCw className="h-5 w-5" />
        </div>
        <p>Loading processing status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-4 bg-red-50 text-red-800 rounded-md border border-red-200">
        <AlertCircle className="h-5 w-5 mr-2" />
        <p>{error}</p>
        <Button 
          variant="outline" 
          size="sm" 
          className="ml-4"
          onClick={fetchStatus}
        >
          Retry
        </Button>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="flex items-center justify-center p-4 bg-yellow-50 text-yellow-800 rounded-md border border-yellow-200">
        <AlertCircle className="h-5 w-5 mr-2" />
        <p>No status information found</p>
      </div>
    );
  }

  const { 
    status: currentStatus, 
    progress = 0, 
    pipeline_name, 
    started_at, 
    completed_at, 
    error_message 
  } = status;

  const formattedStartDate = started_at ? new Date(started_at).toLocaleString() : 'N/A';
  const formattedEndDate = completed_at ? new Date(completed_at).toLocaleString() : 'N/A';
  const duration = started_at && completed_at 
    ? Math.round((new Date(completed_at).getTime() - new Date(started_at).getTime()) / 1000)
    : null;
  
  // Make sure currentStatus is a valid key
  const statusKey = (currentStatus as StatusType) || 'pending';

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">
            {batchId ? 'Batch Processing' : 'Processing Status'}
          </CardTitle>
          <Badge className={statusColors[statusKey] || 'bg-gray-100'}>
            <div className="flex items-center space-x-1">
              {statusIcons[statusKey] || <Clock className="h-4 w-4" />}
              <span>
                {statusKey === 'pending' && 'Pending'}
                {statusKey === 'running' && 'Running'}
                {statusKey === 'processing' && 'Processing'}
                {statusKey === 'completed' && 'Completed'}
                {statusKey === 'failed' && 'Failed'}
                {statusKey === 'canceled' && 'Canceled'}
              </span>
            </div>
          </Badge>
        </div>
        <CardDescription>
          {pipeline_name ? `Pipeline: ${pipeline_name}` : 'Processing tracking'}
        </CardDescription>
      </CardHeader>
      
      <CardContent className="pb-2">
        <div className="space-y-4">
          {/* Progress bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
          
          {/* Time information */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Start</p>
              <p>{formattedStartDate}</p>
            </div>
            <div>
              <p className="text-muted-foreground">End</p>
              <p>{formattedEndDate}</p>
            </div>
          </div>
          
          {/* Duration */}
          {duration && (
            <div className="text-sm">
              <p className="text-muted-foreground">Duration</p>
              <p>{duration} seconds</p>
            </div>
          )}
          
          {/* Error message */}
          {error_message && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
              <p className="font-medium mb-1">Error</p>
              <p className="break-words">{error_message}</p>
            </div>
          )}
        </div>
      </CardContent>
      
      <CardFooter className="flex justify-end space-x-2 pt-2">
        {statusKey === 'failed' && (
          <Button 
            variant="secondary" 
            size="sm" 
            onClick={handleRetry}
            className="gap-1"
          >
            <RotateCw className="h-4 w-4" />
            Retry
          </Button>
        )}
        
        {['running', 'processing'].includes(statusKey) && (
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleCancel}
            className="gap-1 text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            <X className="h-4 w-4" />
            Cancel
          </Button>
        )}
      </CardFooter>
    </Card>
  );
};

export default ProcessingStatus; 