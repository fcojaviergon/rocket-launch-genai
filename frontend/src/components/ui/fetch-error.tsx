import React from 'react';
import { Alert, AlertTitle, AlertDescription } from './alert';
import { Button } from './button';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface FetchErrorProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

/**
 * A standardized component for displaying data fetching errors
 */
export function FetchError({
  title = 'Failed to load data',
  message = 'There was an error loading the data. Please try again.',
  onRetry,
  className
}: FetchErrorProps) {
  return (
    <Alert variant="destructive" className={className}>
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        {message}
      </AlertDescription>
      {onRetry && (
        <div className="mt-4">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={onRetry}
            className="gap-1"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        </div>
      )}
    </Alert>
  );
} 