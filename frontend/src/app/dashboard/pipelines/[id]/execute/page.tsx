'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { DashboardHeader } from '@/components'
import { DashboardShell } from '@/components'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { useSession } from 'next-auth/react'
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { usePipelineExecution } from '@/lib/hooks/pipelines'
import apiClient from '@/lib/api/client'

interface Pipeline {
  id: string
  name: string
  description: string
  type: string
  steps: {
    name: string
    type: string
    config: Record<string, any>
  }[]
}

interface Document {
  id: string
  title: string
  content: string
  created_at: string
}

interface PipelineExecution {
  id: string
  pipeline_id: string
  document_id: string
  status: string
  created_at: string
  updated_at: string
}

export default function ExecutePipelinePage() {
  const params = useParams()
  const router = useRouter()
  const { data: session, status } = useSession()
  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDocument, setSelectedDocument] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(true)
  const [executing, setExecuting] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const { getExecutionStatus } = usePipelineExecution()

  // Load the data when the pipeline ID changes
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        if (status !== 'authenticated') {
          setError('You have not logged in. Please log in to continue.');
          setLoading(false);
          return;
        }
        
        try {
          // Load pipeline using apiClient
          const pipelineData = await apiClient.get<Pipeline>(`/api/v1/pipelines/configs/${params.id}`);
          setPipeline(pipelineData);
          
          // Load documents using apiClient
          const documentsData = await apiClient.get<Document[]>('/api/v1/documents');
          setDocuments(documentsData);
          
          if (documentsData.length > 0) {
            setSelectedDocument(documentsData[0].id);
          }
        } catch (apiError: any) {
          console.error('Error API:', apiError);
          
          // And it is an authentication error
          if (apiError.status === 401) {
            setError('The session has expired. Please log in again.');
            toast.error('Session expired', {
              description: 'Please reload the page or log in again.'
            });
          } else {
            setError(apiError.message || 'Error loading the data');
          }
        }
      } catch (err: any) {
        console.error('General error:', err);
        setError('Error loading the data. Try again.');
      } finally {
        setLoading(false);
      }
    };

    // Only execute if we have an active session
    if (status === 'authenticated') {
      fetchData();
    }
  }, [params.id, status]);

  const handleExecute = async () => {
    if (!selectedDocument) {
      toast.error('Select a document to process');
      return;
    }

    try {
      setExecuting(true);
      setError(null);
      
      console.log(`Executing pipeline: ${params.id} with document: ${selectedDocument}`);
      
      // Execute pipeline using apiClient
      const response = await apiClient.post<PipelineExecution>('/api/v1/pipelines/executions', {
        pipeline_id: params.id,
        document_id: selectedDocument,
        async_processing: true,
      });
      
      console.log('Execution response:', response);
      
      if (!response || !response.id) {
        throw new Error('No execution ID received');
      }
      
      // Verify the initial execution status
      try {
        const executionStatus = await getExecutionStatus(response.id);
        console.log('Initial execution status:', executionStatus);
        
        toast.success('Processing started', {
          description: `Execution ID: ${response.id}. You will be redirected to the results page.`
        });
        
        // Redirect the user to the results page after a brief delay
        setTimeout(() => {
          const url = `/dashboard/documents/${selectedDocument}?execution_id=${response.id}`;
          console.log('Redirecting to:', url);
          router.push(url);
        }, 1500);
        
      } catch (statusError) {
        console.error('Error getting initial status:', statusError);
        
        // If the status verification fails, we still redirect
        toast.success('Processing started', {
          description: 'The document is being processed. You will be redirected to the results page.'
        });
        
        setTimeout(() => {
          router.push(`/dashboard/documents/${selectedDocument}?execution_id=${response.id}`);
        }, 1500);
      }
    } catch (error: any) {
      console.error('Error executing pipeline:', error);
      
      // Si es un error de autenticación
      if (error.status === 401) {
        toast.error('Session expired', {
          description: 'Your session has expired. Please reload the page.',
          action: {
            label: 'Reload',
            onClick: () => window.location.reload()
          }
        });
      } else {
        toast.error('Could not start processing', {
          description: error.message || 'Error processing the document'
        });
      }
    } finally {
      setExecuting(false);
    }
  };

  if (loading) {
    return (
      <DashboardShell>
        <DashboardHeader heading="Ejecutar Pipeline" text="Procesando datos...">
          <Link href="/dashboard/pipelines">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </Link>
        </DashboardHeader>
        <div className="flex justify-center items-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardShell>
    )
  }

  if (error || !pipeline) {
    return (
      <DashboardShell>
        <DashboardHeader heading="Execute Pipeline" text="There was an error loading the data">
          <Link href="/dashboard/pipelines">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </Link>
        </DashboardHeader>
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error || 'Pipeline not found'}</AlertDescription>
        </Alert>
      </DashboardShell>
    )
  }

  return (
    <DashboardShell>
      <DashboardHeader heading={`Execute: ${pipeline.name}`} text="Select a document to process with this pipeline.">
        <Link href="/dashboard/pipelines">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
      </DashboardHeader>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Pipeline details</CardTitle>
            <CardDescription>{pipeline.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableCaption>This pipeline contains {pipeline.steps.length} processors</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead>Order</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pipeline.steps.map((step, index) => (
                  <TableRow key={index}>
                    <TableCell>{index + 1}</TableCell>
                    <TableCell>{step.name}</TableCell>
                    <TableCell>{step.type}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Select document</CardTitle>
            <CardDescription>Choose the document you want to process</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              <div className="space-y-2">
                <Label htmlFor="document">Document</Label>
                <Select
                  value={selectedDocument}
                  onValueChange={setSelectedDocument}
                  disabled={documents.length === 0}
                >
                  <SelectTrigger id="document">
                    <SelectValue placeholder="Select document" />
                  </SelectTrigger>
                  <SelectContent>
                    {documents.map((doc) => (
                      <SelectItem key={doc.id} value={doc.id}>
                        {doc.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {documents.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    No documents available. Please <Link href="/dashboard/documents/upload" className="text-primary">upload a document</Link> first.
                  </p>
                )}
              </div>

              <Button
                onClick={handleExecute}
                disabled={executing || documents.length === 0 || !selectedDocument}
                className="w-full mt-4"
              >
                {executing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  'Execute Pipeline'
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  )
} 