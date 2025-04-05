'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Plus, RefreshCw, Trash2, Pencil, Eye, Code } from 'lucide-react';
import { PipelineConfig } from '@/lib/types/pipeline-types';
import { usePipelineConfig } from '@/lib/hooks/pipelines';
import { toast } from 'sonner';
import { PipelineForm } from './pipeline-form';

export function PipelineConfigList() {
  const [selectedPipeline, setSelectedPipeline] = useState<PipelineConfig | null>(null);
  const [configJson, setConfigJson] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [jsonMode, setJsonMode] = useState(false);
  const { 
    configs, 
    isLoading, 
    loadPipelines, 
    createPipeline, 
    updatePipeline, 
    deletePipeline 
  } = usePipelineConfig();

  const handleSavePipeline = async (config: PipelineConfig) => {
    try {
      if (editMode && selectedPipeline) {
        await updatePipeline(selectedPipeline.id!, config);
        toast.success('Pipeline updated correctly');
      } else {
        await createPipeline(config);
        toast.success('Pipeline created correctly');
      }
      
      loadPipelines();
      setConfigJson('');
      setEditMode(false);
      setJsonMode(false);
    } catch (error) {
      console.error('Error saving pipeline:', error);
      toast.error('Error saving pipeline');
    }
  };

  const handleCreatePipeline = async () => {
    try {
      if (!configJson.trim()) {
        toast.error('The configuration cannot be empty');
        return;
      }

      let config;
      try {
        config = JSON.parse(configJson);
      } catch (e) {
        toast.error('Invalid JSON');
        return;
      }

      if (!config.name) {
        toast.error('The configuration must have a name');
        return;
      }

      if (!config.steps || !Array.isArray(config.steps) || config.steps.length === 0) {
        toast.error('The configuration must have at least one step');
        return;
      }

      if (editMode && selectedPipeline) {
        await updatePipeline(selectedPipeline.id!, config);
        toast.success('Pipeline updated correctly');
      } else {
        await createPipeline(config);
        toast.success('Pipeline created correctly');
      }
      
      loadPipelines();
      setConfigJson('');
      setEditMode(false);
      setJsonMode(false);
    } catch (error) {
      console.error('Error saving pipeline:', error);
      toast.error('Error saving pipeline');
    }
  };

  const handleDeletePipeline = async (id: string) => {
    if (!confirm(`¿Estás seguro de eliminar esta configuración?`)) {
      return;
    }

    try {
      await deletePipeline(id);
      toast.success('Pipeline deleted correctly');
      loadPipelines();
    } catch (error) {
      console.error('Error deleting pipeline:', error);
      toast.error('Error deleting pipeline');
    }
  };

  const handleEditPipeline = (pipeline: PipelineConfig) => {
    setSelectedPipeline(pipeline);
    setConfigJson(JSON.stringify(pipeline, null, 2));
    setEditMode(true);
    setJsonMode(false);
  };

  const handleViewConfig = (pipeline: PipelineConfig) => {
    setSelectedPipeline(pipeline);
    setEditMode(false);
    setConfigJson(JSON.stringify(pipeline, null, 2));
    setJsonMode(true);
  };

  const getTypeColor = (type: string | undefined) => {
    switch (type) {
      case 'document':
        return 'bg-blue-100 text-blue-800 hover:bg-blue-100';
      case 'image':
        return 'bg-green-100 text-green-800 hover:bg-green-100';
      case 'data':
        return 'bg-orange-100 text-orange-800 hover:bg-orange-100';
      default:
        return 'bg-gray-100 text-gray-800 hover:bg-gray-100';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Pipeline Configurations</h2>
        <div className="flex gap-2">
          <Button onClick={loadPipelines} variant="outline" disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
            {isLoading ? 'Loading...' : 'Update'}
          </Button>
          <Dialog>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-1" />
                New Pipeline
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-[800px]">
              <DialogHeader>
                <DialogTitle>
                  {editMode ? 'Edit Pipeline Configuration' : 'Create New Pipeline Configuration'}
                </DialogTitle>
                <DialogDescription>
                  {jsonMode 
                    ? "Enter the configuration in JSON format" 
                    : "Define the pipeline steps and their configuration"}
                </DialogDescription>
              </DialogHeader>

              {jsonMode ? (
                <div className="space-y-4">
                  <div className="flex justify-end">
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => setJsonMode(false)}
                    >
                      <Code className="h-4 w-4 mr-1" />
                      Use Form
                    </Button>
                  </div>
                  <Textarea
                    placeholder="Pipeline JSON"
                    value={configJson}
                    onChange={(e) => setConfigJson(e.target.value)}
                    className="font-mono min-h-[300px]"
                  />

                  <DialogFooter>
                    <Button 
                      variant="outline" 
                      onClick={() => {
                        setConfigJson('');
                        setEditMode(false);
                        setJsonMode(false);
                        setSelectedPipeline(null);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button onClick={handleCreatePipeline}>
                      {editMode ? 'Update' : 'Create'}
                    </Button>
                  </DialogFooter>
                </div>
              ) : (
                <>
                  {editMode && selectedPipeline && (
                    <div className="flex justify-end mb-4">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => {
                          setJsonMode(true);
                          setConfigJson(JSON.stringify(selectedPipeline, null, 2));
                        }}
                      >
                        <Code className="h-4 w-4 mr-1" />
                        View/Edit JSON
                      </Button>
                    </div>
                  )}
                  
                  <PipelineForm 
                    initialData={editMode && selectedPipeline ? selectedPipeline : undefined}
                    onSubmit={handleSavePipeline}
                    onCancel={() => {
                      setEditMode(false);
                      setSelectedPipeline(null);
                    }}
                  />
                </>
              )}
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center p-10">
          <RefreshCw className="h-10 w-10 animate-spin text-gray-400" />
        </div>
      ) : configs && configs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {configs.map((pipeline) => (
            <Card key={pipeline.id}>
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <CardTitle className="text-lg">{pipeline.name}</CardTitle>
                  <Badge className={getTypeColor(pipeline.type)}>
                    {pipeline.type || 'general'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {pipeline.description || 'No description'}
                  </p>
                  
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Pipeline steps:</p>
                    <div className="space-y-1">
                      {pipeline.steps.map((step, idx) => (
                        <div key={idx} className="text-xs bg-gray-50 p-1 rounded">
                          {idx + 1}. {step.name || step.id}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex gap-2 pt-3">
                    <Button variant="outline" size="sm" onClick={() => handleViewConfig(pipeline)}>
                      <Eye className="h-3.5 w-3.5 mr-1" />
                      View
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleEditPipeline(pipeline)}>
                      <Pencil className="h-3.5 w-3.5 mr-1" />
                      Edit
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleDeletePipeline(pipeline.id!)}>
                      <Trash2 className="h-3.5 w-3.5 mr-1" />
                      Delete
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center p-10">
            <p className="text-gray-500 mb-4">No pipelines available</p>
            <Dialog>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-1" />
                  Create Pipeline
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-[800px]">
                <DialogHeader>
                  <DialogTitle>Create New Pipeline Configuration</DialogTitle>
                  <DialogDescription>
                    Enter the configuration in JSON format
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                  <Textarea
                    placeholder="Pipeline JSON"
                    value={configJson}
                    onChange={(e) => setConfigJson(e.target.value)}
                    className="font-mono min-h-[300px]"
                  />

                  <DialogFooter>
                    <Button variant="outline" onClick={() => setConfigJson('')}>
                      Cancel
                    </Button>
                    <Button onClick={handleCreatePipeline}>
                      Create
                    </Button>
                  </DialogFooter>
                </div>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      )}
    </div>
  );
} 