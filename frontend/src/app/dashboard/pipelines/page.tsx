'use client';

import React, { useEffect, useState } from 'react';
import { PipelineService } from '@/lib/services';
import { PipelineInfo, PipelineConfig } from '@/lib/types/pipeline-types';
import { PipelineDetails } from '@/components/pipelines/config';
import { PipelineForm } from '@/components/pipelines/config/forms';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Plus, Edit, Trash, FileText, Play } from 'lucide-react';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useSession } from 'next-auth/react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { DashboardHeader, DashboardShell } from '@/components';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import axios from 'axios';

interface Pipeline {
  id: string;
  name: string;
  description: string;
  type: string;
  steps: any[];
  created_at: string;
  updated_at: string;
}

export default function PipelinesPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);

  const fetchPipelines = async () => {
    try {
      setLoading(true);
      console.log('Fetching all pipelines configs');
      
      const response = await fetch('/api/pipelines/configs', {
        method: 'GET',
        credentials: 'include' // Ensure cookies are sent with the request
      });

      console.log('Pipelines fetch response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.text();
        console.error('Pipelines fetch error:', errorData);
        
        // Check if it's an authentication error
        if (response.status === 401) {
          console.log('Authentication error, redirecting to login');
          // Redirect to login
          router.push('/login');
          return;
        }
        
        throw new Error(`Failed to fetch pipelines: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Pipelines data loaded successfully, count:', Array.isArray(data) ? data.length : 'not an array');
      
      setPipelines(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error fetching pipelines:', err);
      setError('Could not load the pipelines. Try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipelines();
  }, []);

  const handleCreatePipeline = () => {
    setSelectedPipeline(null);
    setIsCreateDialogOpen(true);
  };

  const handleEditPipeline = (pipeline: Pipeline) => {
    setSelectedPipeline(pipeline);
    setIsEditDialogOpen(true);
  };

  const handleDeletePipeline = async (id: string) => {
    if (!confirm('Are you sure you want to delete this pipeline?')) {
      return;
    }

    try {
      await axios.delete(`/api/pipelines/configs/${id}`);
      toast.success('Pipeline deleted correctly');
      fetchPipelines();
    } catch (err) {
      console.error('Error deleting pipeline:', err);
      toast.error('Could not delete the pipeline');
    }
  };

  const handleSavePipeline = async () => {
    setIsCreateDialogOpen(false);
    setIsEditDialogOpen(false);
    await fetchPipelines();
  };

  const handleExecutePipeline = (id: string) => {
    router.push(`/dashboard/pipelines/${id}/execute`);
  };

  if (loading) {
    return (
      <DashboardShell>
        <DashboardHeader heading="Pipelines" text="Pipeline management and document processing configurations.">
          {/*
          <Button disabled>
            <Plus className="mr-2 h-4 w-4" />
            New Pipeline
          </Button>
          */}
        </DashboardHeader>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="overflow-hidden">
              <CardHeader className="pb-2">
                <Skeleton className="h-5 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-2/3" />
              </CardContent>
              <CardFooter>
                <div className="flex justify-end space-x-2 w-full">
                  <Skeleton className="h-9 w-20" />
                  <Skeleton className="h-9 w-20" />
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      </DashboardShell>
    );
  }

  if (error) {
    return (
      <DashboardShell>
        <DashboardHeader heading="Pipelines" text="Pipeline management and document processing configurations.">
          <Button onClick={() => fetchPipelines()}>
            Try again
          </Button>
        </DashboardHeader>
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </DashboardShell>
    );
  }
  
  return (
    <DashboardShell>
      <DashboardHeader heading="Pipelines" text="Pipeline management and document processing configurations.">
        {/*
        <Link href="/dashboard/pipelines/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Pipeline
          </Button>
        </Link>
        */}
      </DashboardHeader>

      {pipelines.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
          <h3 className="mb-2 mt-2 text-lg font-semibold">No pipelines found</h3>
          <p className="mb-4 text-sm text-muted-foreground">
            Create your first pipeline to start processing documents.
          </p>
          <Link href="/dashboard/pipelines/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create pipeline
            </Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {pipelines.map((pipeline) => (
            <Card key={pipeline.id} className="overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-medium">
                  {pipeline.name}
                </CardTitle>
                <div className="flex items-center">
                  <Badge variant="outline" className="mr-2">
                    {pipeline.type || 'Standard'}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {new Date(pipeline.created_at).toLocaleDateString()}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="pb-2">
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {pipeline.description || 'No description'}
                </p>
                <div className="mt-2">
                  <p className="text-xs font-medium">Processors: {pipeline.steps?.length || 0}</p>
                </div>
              </CardContent>
              {/*
              <CardFooter>
                <div className="flex justify-end space-x-2 w-full">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleExecutePipeline(pipeline.id)}
                  >
                    <Play className="h-4 w-4 mr-1" />
                    Execute
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push(`/dashboard/pipelines/${pipeline.id}/edit`)}
                  >
                    <Edit className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeletePipeline(pipeline.id)}
                  >
                    <Trash className="h-4 w-4 mr-1" />
                    Delete
                  </Button>
                </div>
              </CardFooter>
              */}
            </Card>
          ))}
        </div>
      )}
      
      {/* Dialog for creating pipeline */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-4xl">
          <PipelineForm 
            onSave={handleSavePipeline} 
            onCancel={() => setIsCreateDialogOpen(false)} 
          />
        </DialogContent>
      </Dialog>

      {/* Dialog for editing pipeline */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-4xl">
          {selectedPipeline && (
            <PipelineForm 
              pipeline={selectedPipeline} 
              onSave={handleSavePipeline} 
              onCancel={() => setIsEditDialogOpen(false)} 
            />
          )}
        </DialogContent>
      </Dialog>
    </DashboardShell>
  );
}
