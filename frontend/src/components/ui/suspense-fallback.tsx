import React from 'react';
import { Spinner } from './spinner';

interface SuspenseFallbackProps {
  message?: string;
  className?: string;
  spinnerSize?: 'sm' | 'md' | 'lg';
}

/**
 * A standardized loading fallback component to use with React.Suspense
 */
export function SuspenseFallback({
  message = 'Loading...',
  className = 'flex items-center justify-center py-8',
  spinnerSize = 'md'
}: SuspenseFallbackProps) {
  return (
    <div className={className}>
      <div className="flex flex-col items-center">
        <Spinner size={spinnerSize} className="mb-2" />
        {message && <p className="text-sm text-muted-foreground">{message}</p>}
      </div>
    </div>
  );
}

/**
 * Layout-specific suspense fallback that expands to fill the available space
 */
export function FullPageSuspenseFallback({
  message = 'Loading...',
  spinnerSize = 'lg'
}: Omit<SuspenseFallbackProps, 'className'>) {
  return (
    <SuspenseFallback
      message={message}
      spinnerSize={spinnerSize}
      className="flex items-center justify-center min-h-[50vh] w-full"
    />
  );
} 