'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Plus, X, Save } from 'lucide-react';
import { PipelineInfo, PipelineConfig, PipelineStep } from '@/lib/types/pipeline-types';
import { usePipelineConfig } from '@/lib/hooks/pipelines';
import { toast } from 'sonner';

interface PipelineFormProps {
  pipeline?: PipelineInfo;
  onSave: () => void;
  onCancel: () => void;
}

export function PipelineForm({ pipeline, onSave, onCancel }: PipelineFormProps) {
  const isEditing = !!pipeline;
  const { createPipeline, updatePipeline } = usePipelineConfig();
  const [isLoading, setIsLoading] = useState(false);
  
  const [formData, setFormData] = useState<{
    name: string;
    description: string;
    steps: string[];
  }>({
    name: '',
    description: '',
    steps: [''],
  });

  useEffect(() => {
    if (pipeline) {
      setFormData({
        name: pipeline.name || '',
        description: pipeline.description || '',
        steps: pipeline.steps.length ? pipeline.steps : [''],
      });
    }
  }, [pipeline]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleStepChange = (index: number, value: string) => {
    const newSteps = [...formData.steps];
    newSteps[index] = value;
    setFormData(prev => ({ ...prev, steps: newSteps }));
  };

  const addStep = () => {
    setFormData(prev => ({ ...prev, steps: [...prev.steps, ''] }));
  };

  const removeStep = (index: number) => {
    if (formData.steps.length === 1) return;
    const newSteps = formData.steps.filter((_, i) => i !== index);
    setFormData(prev => ({ ...prev, steps: newSteps }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!formData.name.trim()) {
      toast.error('The pipeline name is required');
      return;
    }
    
    // Filter empty steps
    const filteredSteps = formData.steps.filter(step => step.trim());
    if (filteredSteps.length === 0) {
      toast.error('At least one step must be defined');
      return;
    }

    try {
      setIsLoading(true);
      
      // Convert steps from strings to PipelineStep objects
      const pipelineSteps: PipelineStep[] = filteredSteps.map((step, index) => ({
        id: `step-${index + 1}`,
        name: step,
        type: 'processor',
      }));
      
      const pipelineData: PipelineConfig = {
        name: formData.name,
        description: formData.description || '',
        steps: pipelineSteps,
      };
      
      if (isEditing && pipeline?.id) {
        await updatePipeline(pipeline.id, pipelineData);
        toast.success('Pipeline updated correctly');
      } else {
        await createPipeline(pipelineData);
        toast.success('Pipeline created correctly');
      }
      
      onSave();
    } catch (error) {
      console.error('Error saving pipeline:', error);
      toast.error('Error saving pipeline');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-4">
          <div className="space-y-2">
            <Label htmlFor="name">Pipeline name</Label>
            <Input
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              placeholder="Descriptive name of the pipeline"
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              placeholder="Detailed description of the pipeline and its function"
              rows={3}
            />
          </div>
        </div>
        
        <div className="space-y-2">
          <Label>Pipeline steps</Label>
          <p className="text-sm text-muted-foreground mb-2">
            Define the sequential steps that this pipeline will execute
          </p>
          
          <div className="space-y-2">
            {formData.steps.map((step, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  value={step}
                  onChange={(e) => handleStepChange(index, e.target.value)}
                  placeholder={`Step ${index + 1}`}
                  className="flex-1"
                />
                <Button 
                  type="button" 
                  variant="outline" 
                  size="sm"
                  onClick={() => removeStep(index)}
                  disabled={formData.steps.length === 1}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            
            <Button
              type="button"
              variant="outline"
              onClick={addStep}
              className="w-full mt-2"
            >
              <Plus className="h-4 w-4 mr-2" /> Add step
            </Button>
          </div>
        </div>
      </div>
      
      <div className="flex justify-end gap-2">
        <Button 
          type="button" 
          variant="outline"
          onClick={onCancel}
          disabled={isLoading}
        >
          Cancel
        </Button>
        <Button 
          type="submit"
          disabled={isLoading}
        >
          {isLoading ? (
            <>Saving...</>
          ) : (
            <>
              <Save className="h-4 w-4 mr-2" />
              {isEditing ? 'Update' : 'Save'}
            </>
          )}
        </Button>
      </div>
    </form>
  );
} 