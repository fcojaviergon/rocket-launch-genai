'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { PipelineConfig, PipelineInfo } from '@/lib/types/pipeline-types';
import { CheckCircle, PackageCheck, Clock3, ListTree } from 'lucide-react';

interface PipelineDetailsProps {
  pipeline: PipelineConfig | PipelineInfo;
}

export function PipelineDetails({ pipeline }: PipelineDetailsProps) {
  // Determine the badge color for the pipeline type
  const getTypeColor = (type: string | undefined) => {
    switch (type) {
      case 'document':
        return 'bg-blue-100 text-blue-800 hover:bg-blue-100';
      case 'image':
        return 'bg-purple-100 text-purple-800 hover:bg-purple-100';
      case 'data':
        return 'bg-green-100 text-green-800 hover:bg-green-100';
      default:
        return 'bg-gray-100 text-gray-800 hover:bg-gray-100';
    }
  };

  // Return the appropriate icon for each pipeline step
  const getStepIcon = (step: any) => {
    const stepType = typeof step === 'string' 
      ? step
      : step.type?.toLowerCase() || '';

    if (typeof stepType === 'string') {
      if (stepType.includes('check') || stepType.includes('validate')) {
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      } else if (stepType.includes('extract') || stepType.includes('parse')) {
        return <PackageCheck className="h-4 w-4 text-blue-500" />;
      } else if (stepType.includes('process') || stepType.includes('transform')) {
        return <Clock3 className="h-4 w-4 text-orange-500" />;
      } else {
        return <ListTree className="h-4 w-4 text-gray-500" />;
      }
    }
    
    return <ListTree className="h-4 w-4 text-gray-500" />;
  };

  // Check if the steps are strings or objects
  const renderSteps = () => {
    const steps = pipeline.steps;
    return steps.map((step, idx) => {
      const isStringStep = typeof step === 'string';
      
      return (
        <div key={idx} className="border rounded-md p-3">
          <div className="flex items-center gap-2 mb-1">
            {getStepIcon(step)}
            <span className="font-medium">
              {isStringStep ? step : (step.name || step.id)}
            </span>
          </div>
          {!isStringStep && step.type && (
            <div className="text-xs text-gray-500 ml-6">Type: {step.type}</div>
          )}
          {!isStringStep && step.parameters && Object.keys(step.parameters).length > 0 && (
            <div className="mt-2 ml-6">
              <div className="text-xs text-gray-500 mb-1">Parameters:</div>
              <div className="text-xs grid grid-cols-2 gap-x-2 gap-y-1">
                {Object.entries(step.parameters).map(([key, value]) => (
                  <div key={key} className="col-span-2 grid grid-cols-2">
                    <div className="text-gray-600">{key}:</div>
                    <div className="truncate">
                      {typeof value === 'object' 
                        ? JSON.stringify(value) 
                        : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl">{pipeline.name}</CardTitle>
            <CardDescription>{pipeline.description || 'No description'}</CardDescription>
          </div>
          {pipeline.type && (
            <Badge className={getTypeColor(pipeline.type)}>
              {pipeline.type}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-medium mb-2">Pipeline steps</h3>
            <div className="space-y-2">
              {renderSteps()}
            </div>
          </div>

          {pipeline.parameters && Object.keys(pipeline.parameters).length > 0 && (
            <>
              <Separator />
              <div>
                <h3 className="text-sm font-medium mb-2">Global parameters</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(pipeline.parameters).map(([key, value]) => (
                    <div key={key} className="col-span-2 grid grid-cols-2">
                      <div className="font-medium">{key}:</div>
                      <div className="truncate">
                        {typeof value === 'object' 
                          ? JSON.stringify(value) 
                          : String(value)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {pipeline.metadata && Object.keys(pipeline.metadata).length > 0 && (
            <>
              <Separator />
              <div>
                <h3 className="text-sm font-medium mb-2">Metadata</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(pipeline.metadata).map(([key, value]) => (
                    <div key={key} className="col-span-2 grid grid-cols-2">
                      <div className="font-medium">{key}:</div>
                      <div className="truncate">
                        {typeof value === 'object' 
                          ? JSON.stringify(value) 
                          : String(value)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
} 