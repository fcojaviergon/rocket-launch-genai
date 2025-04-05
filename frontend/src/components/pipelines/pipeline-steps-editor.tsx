'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Plus, Trash, MoveUp, MoveDown, Settings } from 'lucide-react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface PipelineStep {
  name: string
  type: string
  config: Record<string, any>
  description?: string
  id?: string
}

interface PipelineStepsEditorProps {
  value: PipelineStep[]
  onChange: (value: PipelineStep[]) => void
}

// Available processor types
const PROCESSOR_TYPES = [
  {
    value: 'text_extraction',
    label: 'Text extraction',
    description: 'Extracts text from documents',
    configFields: [
      { name: 'language', label: 'Language', type: 'text', default: 'es' },
      { name: 'min_length', label: 'Minimum length', type: 'number', default: 100 },
    ],
  },
  {
    value: 'summarizer',
    label: 'Summarizer',
    description: 'Generates a summary of the text',
    configFields: [
      { name: 'max_length', label: 'Longitud máxima', type: 'number', default: 200 },
      { 
        name: 'style', 
        label: 'Estilo', 
        type: 'select', 
        options: [
          { value: 'concise', label: 'Concise' },
          { value: 'detailed', label: 'Detailed' },
          { value: 'bullet_points', label: 'Bullet points' },
        ],
        default: 'concise'
      },
    ],
  },
  {
    value: 'keyword_extraction',
    label: 'Keyword extraction',
    description: 'Identifies keywords in the text',
    configFields: [
      { name: 'max_keywords', label: 'Maximum number of keywords', type: 'number', default: 10 },
      { name: 'min_relevance', label: 'Minimum relevance', type: 'number', default: 0.5 },
    ],
  },
  {
    value: 'sentiment_analysis',
    label: 'Sentiment analysis',
    description: 'Analyzes the sentiment of the text',
    configFields: [
      { name: 'detailed', label: 'Detailed', type: 'checkbox', default: false },
    ],
  },
  // Add support for backend-defined processor types
  {
    value: 'extract_text',
    label: 'Extract Text',
    description: 'Extract text from documents',
    configFields: [
      { name: 'format', label: 'Format', type: 'text', default: 'plain' },
    ],
  },
  {
    value: 'summarize',
    label: 'Summarize',
    description: 'Summarize document content',
    configFields: [
      { name: 'max_tokens', label: 'Max Tokens', type: 'number', default: 200 },
    ],
  },
  {
    value: 'extract_keywords',
    label: 'Extract Keywords',
    description: 'Extract keywords from text',
    configFields: [
      { name: 'max_keywords', label: 'Max Keywords', type: 'number', default: 10 },
    ],
  },
]

// Check PROCESSOR_TYPES to ensure it is properly defined
if (!PROCESSOR_TYPES || !Array.isArray(PROCESSOR_TYPES)) {
  console.error("PROCESSOR_TYPES is not defined correctly");
}

type ConfigField = {
  name: string;
  label: string;
  type: string;
  default: string | number | boolean;
  options?: Array<{ value: string; label: string }>;
};

export function PipelineStepsEditor({ value = [], onChange }: PipelineStepsEditorProps) {
  // Create a safe version of the value array to avoid undefined issues
  const safeValue = Array.isArray(value) ? value : [];
  
  // Log incoming value for debugging
  console.log('PipelineStepsEditor value:', safeValue);

  const addStep = () => {
    const newStep = {
      name: '',
      type: 'processor',
      config: {},
      description: '',
    };
    onChange([...safeValue, newStep]);
  }

  const updateStep = (index: number, stepData: Partial<PipelineStep>) => {
    // Validate index
    if (index < 0 || index >= safeValue.length) {
      console.error(`Invalid step index: ${index}`);
      return;
    }
    
    const newSteps = [...safeValue];
    
    // Ensure the step at this index exists
    if (!newSteps[index]) {
      console.error(`Step at index ${index} does not exist`);
      return;
    }
    
    // Create a safe config object
    const currentConfig = newSteps[index].config || {};
    const newConfig = stepData.config || {};
    
    // Update the step with merged data
    newSteps[index] = { 
      ...newSteps[index], 
      ...stepData,
      config: { ...currentConfig, ...newConfig }
    };
    
    onChange(newSteps);
  }

  const removeStep = (index: number) => {
    // Make sure we're working with a valid index
    if (index < 0 || index >= safeValue.length) {
      return;
    }
    onChange(safeValue.filter((_, i) => i !== index));
  }

  const moveStep = (index: number, direction: 'up' | 'down') => {
    // Validate index and direction
    if (
      (direction === 'up' && index === 0) ||
      (direction === 'down' && index === safeValue.length - 1) ||
      index < 0 ||
      index >= safeValue.length
    ) {
      return;
    }

    const newSteps = [...safeValue];
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    
    // Swap the steps
    const temp = newSteps[index];
    newSteps[index] = newSteps[newIndex];
    newSteps[newIndex] = temp;
    
    onChange(newSteps);
  }

  // Function to get the processor display info
  const getProcessorInfo = (step: PipelineStep) => {
    // Handle processor types that match directly
    let processorType = PROCESSOR_TYPES.find(p => p.value === step.type);
    
    // If not found and type is "processor", check the id instead
    if (!processorType && step.type === "processor" && step.id) {
      processorType = PROCESSOR_TYPES.find(p => p.value === step.id);
    }
    
    // If still not found, create a generic entry
    if (!processorType) {
      return {
        label: step.name || step.type || "Unknown",
        description: "Custom processor",
        configFields: []
      };
    }
    
    return processorType;
  }

  // When a processor type is selected, configure with default values
  const handleTypeChange = (index: number, newType: string) => {
    const processorType = PROCESSOR_TYPES.find(p => p.value === newType);
    if (!processorType) {
      console.warn(`Processor type not found: ${newType}`);
      return;
    }

    // Create default config
    const defaultConfig: Record<string, any> = {};
    processorType.configFields.forEach(field => {
      defaultConfig[field.name] = field.default;
    });

    // Update the step - preserve compatibility with backend format
    updateStep(index, {
      type: newType.includes('extract') || newType.includes('summarize') ? newType : "processor",
      id: newType,
      name: safeValue[index]?.name || processorType.label,
      config: defaultConfig,
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium" id="steps-heading">Pipeline steps</span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addStep}
          aria-describedby="steps-heading"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add step
        </Button>
      </div>

      {safeValue.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No steps configured in this pipeline.
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={addStep}
          >
            <Plus className="h-4 w-4 mr-2" />
            Add first step
          </Button>
        </div>
      ) : (
        <div className="space-y-4" role="list">
          {safeValue.map((step, index) => {
            // Get the effective processor type info
            const processorInfo = getProcessorInfo(step);
            
            return (
              <Card key={index} role="listitem">
                <CardHeader className="py-4 px-5">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-base font-medium">
                      {step.name || `Step ${index + 1}`}
                    </CardTitle>
                    <div className="flex space-x-1">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => moveStep(index, 'up')}
                              disabled={index === 0}
                            >
                              <MoveUp className="h-4 w-4" />
                              <span className="sr-only">Move up</span>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Move up</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>

                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => moveStep(index, 'down')}
                              disabled={index === safeValue.length - 1}
                            >
                              <MoveDown className="h-4 w-4" />
                              <span className="sr-only">Move down</span>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Move down</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>

                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => removeStep(index)}
                            >
                              <Trash className="h-4 w-4" />
                              <span className="sr-only">Remove</span>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Remove</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="py-2 px-5 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor={`step-${index}-name`}>Name</Label>
                      <Input
                        id={`step-${index}-name`}
                        value={step.name || ''}
                        onChange={(e) => updateStep(index, { name: e.target.value })}
                        placeholder="Enter a name for this step"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`step-${index}-type`}>Type</Label>
                      <Select
                        value={step.id || step.type || ''}
                        onValueChange={(value) => handleTypeChange(index, value)}
                      >
                        <SelectTrigger id={`step-${index}-type`}>
                          <SelectValue placeholder="Select a type" />
                        </SelectTrigger>
                        <SelectContent>
                          {PROCESSOR_TYPES.map((type) => (
                            <SelectItem key={type.value} value={type.value}>
                              {type.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`step-${index}-description`}>Description (optional)</Label>
                    <Textarea
                      id={`step-${index}-description`}
                      value={step.description || ''}
                      onChange={(e) => updateStep(index, { description: e.target.value })}
                      placeholder="Describe what this step does"
                    />
                  </div>

                  {/* Configuration section */}
                  <Accordion type="single" collapsible defaultValue="configuration">
                    <AccordionItem value="configuration">
                      <AccordionTrigger className="py-2">
                        <div className="flex items-center">
                          <Settings className="h-4 w-4 mr-2" />
                          Configuration
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-4 pt-2">
                          {processorInfo?.configFields?.length > 0 ? (
                            processorInfo.configFields.map((field: ConfigField) => {
                              const config = step.config || {};
                              const fieldValue = config[field.name] !== undefined 
                                ? config[field.name] 
                                : field.default;
                              
                              return (
                                <div key={field.name} className="space-y-2">
                                  <Label htmlFor={`step-${index}-config-${field.name}`}>
                                    {field.label}
                                  </Label>
                                  
                                  {field.type === 'text' && (
                                    <Input
                                      id={`step-${index}-config-${field.name}`}
                                      value={fieldValue || ''}
                                      onChange={(e) => {
                                        const newConfig = { ...config };
                                        newConfig[field.name] = e.target.value;
                                        updateStep(index, { config: newConfig });
                                      }}
                                    />
                                  )}
                                  
                                  {field.type === 'number' && (
                                    <Input
                                      id={`step-${index}-config-${field.name}`}
                                      type="number"
                                      value={fieldValue || 0}
                                      onChange={(e) => {
                                        const newConfig = { ...config };
                                        newConfig[field.name] = parseInt(e.target.value);
                                        updateStep(index, { config: newConfig });
                                      }}
                                    />
                                  )}
                                  
                                  {field.type === 'checkbox' && (
                                    <div className="flex items-center space-x-2">
                                      <input
                                        id={`step-${index}-config-${field.name}`}
                                        type="checkbox"
                                        checked={!!fieldValue}
                                        onChange={(e) => {
                                          const newConfig = { ...config };
                                          newConfig[field.name] = e.target.checked;
                                          updateStep(index, { config: newConfig });
                                        }}
                                        className="form-checkbox h-5 w-5"
                                      />
                                    </div>
                                  )}
                                  
                                  {field.type === 'select' && field.options && (
                                    <Select
                                      value={fieldValue || field.default.toString()}
                                      onValueChange={(value) => {
                                        const newConfig = { ...config };
                                        newConfig[field.name] = value;
                                        updateStep(index, { config: newConfig });
                                      }}
                                    >
                                      <SelectTrigger id={`step-${index}-config-${field.name}`}>
                                        <SelectValue placeholder="Select..." />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {field.options.map((option) => (
                                          <SelectItem key={option.value} value={option.value}>
                                            {option.label}
                                          </SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  )}
                                </div>
                              );
                            })
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              No configuration options available for this step type.
                            </p>
                          )}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  )
} 