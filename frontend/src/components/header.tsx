import React from 'react';

interface DashboardHeaderProps {
  heading: string;
  text?: string;
  children?: React.ReactNode;
}

export function DashboardHeader({ heading, text, children }: DashboardHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold">{heading}</h1>
        {text && <p className="text-muted-foreground mt-1">{text}</p>}
      </div>
      {children}
    </div>
  );
}
