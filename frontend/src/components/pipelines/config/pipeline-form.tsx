import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PipelineConfig, PipelineStep } from '@/lib/types/pipeline-types';
import { X, Plus, ArrowUp, ArrowDown } from 'lucide-react';
import { toast } from 'sonner';

interface PipelineFormProps {
  initialData?: PipelineConfig;
  onSubmit: (config: PipelineConfig) => void;
  onCancel: () => void;
}

// Predefined steps available
const AVAILABLE_STEPS = [
  { id: 'text_extraction', name: 'Text extraction', category: 'document' },
  { id: 'summarization', name: 'Text summarization', category: 'document' },
  { id: 'keyword_extraction', name: 'Keyword extraction', category: 'document' },
  { id: 'sentiment_analysis', name: 'Sentiment analysis', category: 'document' },
  { id: 'ner', name: 'NER', category: 'document' },
  { id: 'classification', name: 'Text classification', category: 'document' },
  { id: 'embedding', name: 'Embedding generation', category: 'document' },
  { id: 'vector_index', name: 'Vector indexing', category: 'document' },
  
  { id: 'image_classification', name: 'Image classification', category: 'image' },
  { id: 'object_detection', name: 'Object detection', category: 'image' },
  { id: 'image_captioning', name: 'Image captioning', category: 'image' },
  
  { id: 'data_cleaning', name: 'Data cleaning', category: 'data' },
  { id: 'data_normalization', name: 'Data normalization', category: 'data' },
  { id: 'feature_extraction', name: 'Feature extraction', category: 'data' }
];

export function PipelineForm({ initialData, onSubmit, onCancel }: PipelineFormProps) {
  const [name, setName] = useState(initialData?.name || '');
  const [description, setDescription] = useState(initialData?.description || '');
  const [type, setType] = useState(initialData?.type || 'document');
  const [steps, setSteps] = useState<PipelineStep[]>(initialData?.steps || []);
  const [availableSteps, setAvailableSteps] = useState(AVAILABLE_STEPS);
  const [selectedStepId, setSelectedStepId] = useState('');

  // Filter steps available according to the selected type
  useEffect(() => {
    if (type) {
      setAvailableSteps(AVAILABLE_STEPS.filter(step => step.category === type));
      setSelectedStepId('');
    }
  }, [type]);

  const handleAddStep = () => {
    if (!selectedStepId) {
      toast.error('Select a step to add');
      return;
    }

    const stepToAdd = availableSteps.find(s => s.id === selectedStepId);
    if (!stepToAdd) return;

    const newStep: PipelineStep = {
      id: stepToAdd.id,
      name: stepToAdd.name,
      type: 'processor',
      parameters: {}
    };

    setSteps([...steps, newStep]);
    setSelectedStepId('');
  };

  const handleRemoveStep = (index: number) => {
    const newSteps = [...steps];
    newSteps.splice(index, 1);
    setSteps(newSteps);
  };

  const handleMoveStep = (index: number, direction: 'up' | 'down') => {
    if (
      (direction === 'up' && index === 0) || 
      (direction === 'down' && index === steps.length - 1)
    ) {
      return;
    }

    const newSteps = [...steps];
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    
    [newSteps[index], newSteps[newIndex]] = [newSteps[newIndex], newSteps[index]];
    setSteps(newSteps);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name) {
      toast.error('The name is required');
      return;
    }

    if (steps.length === 0) {
      toast.error('Add at least one step to the pipeline');
      return;
    }

    const config: PipelineConfig = {
      name,
      description,
      type,
      steps,
      id: initialData?.id
    };

    onSubmit(config);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        <div>
          <Label htmlFor="name">Name</Label>
          <Input 
            id="name" 
            value={name} 
            onChange={(e) => setName(e.target.value)} 
            placeholder="Name of the pipeline"
            required
          />
        </div>

        <div>
          <Label htmlFor="description">Description</Label>
          <Textarea 
            id="description" 
            value={description} 
            onChange={(e) => setDescription(e.target.value)} 
            placeholder="Describe the purpose of this pipeline"
            rows={3}
          />
        </div>

        <div>
          <Label htmlFor="type">Type</Label>
          <Select value={type} onValueChange={setType}>
            <SelectTrigger>
              <SelectValue placeholder="Select the type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="document">Documents</SelectItem>
              <SelectItem value="image">Images</SelectItem>
              <SelectItem value="data">Data</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Pipeline steps</Label>
          
          <div className="flex gap-2">
            <Select value={selectedStepId} onValueChange={setSelectedStepId}>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="Select a step to add" />
              </SelectTrigger>
              <SelectContent>
                {availableSteps.map((step) => (
                  <SelectItem key={step.id} value={step.id}>
                    {step.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button type="button" onClick={handleAddStep}>
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          </div>

          <div className="border rounded-md p-4 mt-2">
            {steps.length > 0 ? (
              <ul className="space-y-2">
                {steps.map((step, index) => (
                  <li key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <span className="font-medium">{index + 1}. {step.name}</span>
                    <div className="flex items-center gap-1">
                      <Button 
                        type="button" 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleMoveStep(index, 'up')}
                        disabled={index === 0}
                      >
                        <ArrowUp className="h-4 w-4" />
                      </Button>
                      <Button 
                        type="button" 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleMoveStep(index, 'down')}
                        disabled={index === steps.length - 1}
                      >
                        <ArrowDown className="h-4 w-4" />
                      </Button>
                      <Button 
                        type="button" 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleRemoveStep(index)}
                      >
                        <X className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-center py-4 text-gray-500">
                No steps configured. Add at least one step to the pipeline.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">
          {initialData ? 'Update Pipeline' : 'Create Pipeline'}
        </Button>
      </div>
    </form>
  );
} 