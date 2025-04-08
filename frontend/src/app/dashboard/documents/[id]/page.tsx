"use client";

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, FileText, Clock, CheckCircle, Layers, Search, XCircle, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { DocumentEmbeddingTab } from '@/components/documents/view/document-embedding-tab';
import { DocumentProcessPanel } from '@/components/documents/view/document-process-panel';
import { ExecutionStatus } from '@/components/pipelines/monitoring/execution-status';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { PipelineExecution } from '@/lib/types/pipeline-types';
import { Document as DocumentType } from '@/lib/types/document-types';
import { useApi } from '@/lib/hooks/api';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { DocumentService } from '@/lib/services/documents/document-service';

interface DocumentDetails {
  id: string;
  title?: string;
  content?: string;
  file_path?: string;
  created_at: string;
  updated_at?: string;
  processing_results?: Array<{
    id: string;
    pipeline_name: string;
    summary?: string;
    keywords?: string[];
    token_count?: number;
    created_at: string;
  }>;
  pipeline_executions?: Array<{
    id: string;
    pipeline_name: string;
    status: string;
    created_at: string;
    updated_at?: string;
    completed_at?: string;
    error?: string;
  }>;
  name?: string;
  file_type?: string;
  file_size?: number;
  user_id?: string;
}

// Function to determine the type of status
const getExecutionStatusType = (status: string): 'completed' | 'failed' | 'running' | 'pending' => {
  const statusLower = status.toLowerCase();
  
  if (statusLower.includes('complet') || statusLower === 'completed' || statusLower === 'success') {
    return 'completed';
  } else if (statusLower.includes('fail') || statusLower === 'failed' || statusLower === 'error') {
    return 'failed';
  } else if (statusLower.includes('process') || statusLower.includes('run') || statusLower === 'running' || statusLower === 'processing') {
    return 'running';
  } else {
    return 'pending';
  }
};

// Define the type for an item within processing_results
// type ProcessingResultItem = NonNullable<Document['processing_results']>[number];

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const { data: session, status: sessionStatus } = useSession();
  const executionId = searchParams.get('execution_id');
  const [document, setDocument] = useState<DocumentType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('content');
  const [hasRunningExecutions, setHasRunningExecutions] = useState(false);
  const [executions, setExecutions] = useState<PipelineExecution[]>([]);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const apiClient = useApi();
  const router = useRouter();

  // Función simplificada que NO hace llamadas API
  const refreshExecutions = useCallback(() => {
    console.log("Actualizando ejecuciones desde datos del documento");
    
    // Si el documento tiene ejecuciones, usamos esas
    if (document && document.pipeline_executions && document.pipeline_executions.length > 0) {
      const documentExecutions = document.pipeline_executions as PipelineExecution[];
      setExecutions(documentExecutions);
      
      const hasRunning = documentExecutions.some(exec => 
        ['running', 'pending', 'processing'].includes(exec.status?.toLowerCase())
      );
      setHasRunningExecutions(hasRunning);
      
      toast.success("Lista de ejecuciones actualizada");
    } else {
      // Si no hay ejecuciones en el documento, dejamos la lista vacía
      setExecutions([]);
      setHasRunningExecutions(false);
    }
    
    return [];
  }, [document]);

  useEffect(() => {
    if (executionId) {
      setActiveTab('executions');
    }
    
    const tabParam = searchParams.get('tab');
    if (tabParam && ['content', 'processing', 'embeddings', 'executions'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
    
    // Check if there is a new execution in localStorage
    try {
      const newExecutionStr = localStorage.getItem('new_execution');
      if (newExecutionStr) {
        localStorage.removeItem('new_execution');
        
        const newExecution = JSON.parse(newExecutionStr);
        console.log('New execution detected:', newExecution);
        
        // Update the document only if it already exists
        setExecutions(prev => {
          const existingIndex = prev.findIndex(exec => exec.id === newExecution.id);
          
          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = { ...updated[existingIndex], ...newExecution } as PipelineExecution;
            return updated;
          } else {
            return [newExecution as PipelineExecution, ...prev];
          }
        });
      }
    } catch (error) {
      console.error('Error processing execution from localStorage:', error);
    }
  }, [executionId, searchParams]);

  // useEffect to fetch the main document details
  useEffect(() => {
    let isMounted = true;
    const fetchDocument = async () => {
      console.log(`(Effect Run - Detail Page) ID=${id}, Status=${sessionStatus}, Client=${!!apiClient?.documents?.get}`);
      
      if (sessionStatus !== 'authenticated' || !id || !apiClient?.documents?.get) {
        console.log("(Effect Run - Detail Page) Waiting for Auth/ID/Client...");
        if (sessionStatus === 'loading' && !loading) setLoading(true);
        if (sessionStatus === 'unauthenticated' && !loading) {
             setError('Authentication required.');
             setLoading(false);
        }
        return;
      }

      console.log(`(Effect Run - Detail Page) Fetching document ID: ${id}`);
      if (!loading) setLoading(true);
      setError(null);

      try {
        const data = await apiClient.documents.get(id as string) as DocumentType;
        if (isMounted) {
          console.log('(Effect Run - Detail Page) Fetch successful:', data?.id);
          setDocument(data);
          
          const initialExecutions = (data.pipeline_executions || []) as PipelineExecution[];
          setExecutions(initialExecutions);
          const hasRunning = initialExecutions.some(exec => 
            ['running', 'pending', 'processing'].includes(exec.status?.toLowerCase())
          );
          setHasRunningExecutions(hasRunning);
          console.log('(Effect Run - Detail Page) Initial executions set:', initialExecutions.length, 'Has running:', hasRunning);
        }
      } catch (err: any) {
        if (isMounted) {
          console.error('(Effect Run - Detail Page) Fetch error:', err);
          if (!String(err.message).includes('Authentication is still loading')) {
             setError(err.message || 'Could not load document');
          }
          setDocument(null);
          setExecutions([]);
          setHasRunningExecutions(false);
        }
      } finally {
        if (isMounted) {
          console.log("(Effect Run - Detail Page) Setting loading false.");
          setLoading(false);
        }
      }
    };

    fetchDocument();

    return () => {
      isMounted = false;
      console.log("(Effect Cleanup - Detail Page) Unmounting.");
    };
  }, [id, apiClient, sessionStatus]);

  // Función de callback ultra simplificada
  const handleProcessingComplete = useCallback((result?: any) => {
    console.log('Procesamiento completado', result);
    
    // Si recibimos un resultado con ID, lo agregamos/actualizamos en la lista
    if (result && result.id) {
      setExecutions(prev => {
        const existingIndex = prev.findIndex(exec => exec.id === result.id);
        
        if (existingIndex >= 0) {
          // Actualizar existente
          const updated = [...prev];
          updated[existingIndex] = { ...updated[existingIndex], ...result };
          return updated;
        } else {
          // Agregar como nuevo
          return [result as PipelineExecution, ...prev];
        }
      });
    } else {
      // Si no hay resultado, solo usamos los datos del documento
      refreshExecutions();
    }
  }, [refreshExecutions]);

  // --- Handler for Reprocessing ---
  const handleReprocessEmbeddings = async () => {
    if (!document?.id) {
      toast.error("Document ID is missing.");
      return;
    }

    setIsReprocessing(true);
    try {
      // Using defaults for model, chunk size, overlap for now
      // Optionally, add UI elements to set these
      const result = await DocumentService.reprocessEmbeddings(document.id);
      toast.success(result.message || "Reprocessing task scheduled successfully.");
      // Optionally, update document status locally or refetch document
      // For simplicity, we just show the toast here
    } catch (error: any) { // Catch specific error
      const errorMessage = error?.response?.data?.detail || error.message || "Failed to schedule reprocessing.";
      toast.error(`Error: ${errorMessage}`);
    } finally {
      setIsReprocessing(false);
    }
  };
  // --- End Reprocessing Handler ---

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="text-gray-500">Loading document...</div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="text-red-500">{error || 'Document not found'}</div>
      </div>
    );
  }

  const documentTitle = document.title || "Untitled document";

  // --- Revised Result Extraction ---
  const latestCompletedExecution = executions
    ?.filter(exec => getExecutionStatusType(exec.status) === 'completed')
    .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())[0];

   // --- Add these logs before the return statement ---
   /*
   console.log("--- Debugging Results Display ---");
   console.log("Document Fetched:", !!document);
   console.log("Raw Executions State (first 2):", JSON.stringify(executions?.slice(0, 2), null, 2));
   console.log("Latest Completed Execution (found):", !!latestCompletedExecution);
  
   if (latestCompletedExecution) {
       console.log("Latest Completed Execution Object:", JSON.stringify(latestCompletedExecution, null, 2));
   }
   */
   const executionOutput = latestCompletedExecution?.results;
   
   // Access summary and extracted_info directly from executionOutput
   const summaryData = executionOutput?.summary; 
   const displayResults = summaryData?.extracted_info;
   /*
   console.log("Extracted executionOutput:", executionOutput ? typeof executionOutput : 'undefined');
   console.log("Extracted summaryData:", summaryData ? typeof summaryData : 'undefined');
   console.log("Extracted displayResults (extracted_info):", displayResults ? JSON.stringify(displayResults) : displayResults);
   console.log("Is displayResults truthy?", !!displayResults);
   console.log("--- End Debugging ---");
   */
   // --- End logs ---
  // Get the pipeline name from the inner results
  const pipelineNameForResult = executionOutput?.pipeline_name;
  // Execution date remains the same
  const executionDate = latestCompletedExecution?.completed_at || latestCompletedExecution?.updated_at || latestCompletedExecution?.created_at;
  // --- End Revised Result Extraction ---

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <Link href="/dashboard/documents" className="flex items-center text-primary hover:underline">
          <ArrowLeft className="h-4 w-4 mr-1" /> Back to documents
        </Link>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        <div className="w-full md:w-2/3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <FileText className="h-5 w-5 mr-2" />
                {documentTitle}
              </CardTitle>
              <div className="text-sm text-muted-foreground">
                Created: {new Date(document.created_at).toLocaleString()}
              </div>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue={activeTab} value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                  <TabsTrigger value="content">Content</TabsTrigger>
                  <TabsTrigger value="processing">Results</TabsTrigger>
                  <TabsTrigger value="embeddings">
                    <Layers className="h-4 w-4 mr-2" /> Embeddings & RAG
                  </TabsTrigger>
                  <TabsTrigger value="executions">Executions</TabsTrigger>
                </TabsList>
                
                <TabsContent value="content" className="mt-4">
                  <div className="whitespace-pre-wrap bg-muted/30 p-4 rounded-md max-h-[500px] overflow-y-auto">
                    {document.content || 'No content available'}
                  </div>
                </TabsContent>
                
                <TabsContent value="processing" className="mt-4">
                  {displayResults ? (
                    <div className="space-y-4">
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">
                            {pipelineNameForResult || "Resultados del último procesamiento"}
                          </CardTitle>
                          {executionDate && (
                             <CardDescription>
                                Ejecutado: {new Date(executionDate).toLocaleString()}
                             </CardDescription>
                          )}
                        </CardHeader>
                        <CardContent>
                          {displayResults.summary ? (
                            <div className="mb-4">
                              <h4 className="font-medium mb-1">Summary:</h4>
                              <p className="text-sm">{displayResults.summary}</p>
                            </div>
                          ) : null}
                          
                          {displayResults.keywords && displayResults.keywords.length > 0 ? (
                            <div className="mb-4">
                              <h4 className="font-medium mb-1">Keywords:</h4>
                              <div className="flex flex-wrap gap-1">
                                {displayResults.keywords.map((keyword: string, i: number) => (
                                  <span 
                                    key={i} 
                                    className="px-2 py-1 bg-primary/10 text-primary text-xs rounded-full"
                                  >
                                    {keyword.replace(/^\d+\.\s*/, '').trim()}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ) : null}
                          
                          {displayResults.text_stats?.word_count ? (
                            <div className="text-xs text-muted-foreground">
                              Palabras: {displayResults.text_stats.word_count}
                            </div>
                          ) : null}
                        </CardContent>
                      </Card>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground border rounded-md p-4">
                    <p>No results of processing available or the last execution failed.</p>
                      <p className="mt-2 text-sm">
                        Use the right panel to process this document.
                      </p>
                    </div>
                  )}
                </TabsContent>
                
                <TabsContent value="embeddings" className="mt-4">
                  <DocumentEmbeddingTab document={document as any} />
                  
                  {/* --- Reprocess Button --- */}
                  {(document.processing_status === 'completed' || document.processing_status === 'failed') && (
                    <div className="mt-6 border-t pt-4">
                      <h4 className="text-sm font-medium mb-2">Actions</h4>
                      <Button 
                        onClick={handleReprocessEmbeddings}
                        disabled={isReprocessing}
                        variant="outline"
                      >
                        {isReprocessing ? (
                          <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4 mr-2" />
                        )}
                        Reprocess Embeddings
                      </Button>
                      <p className="text-xs text-muted-foreground mt-2">
                        Current Status: {document.processing_status}
                        {document.processing_status === 'failed' && document.error_message && (
                          <span className="block text-red-600">Error: {document.error_message}</span>
                        )}
                      </p>
                    </div>
                  )}
                  {/* --- End Reprocess Button --- */}
                  
                </TabsContent>
                
                <TabsContent value="executions" className="mt-4">
                  {executionId && (
                    <div className="mb-6">
                      <div className="text-sm font-medium mb-2">Ejecución actual:</div>
                      <ExecutionStatus 
                        executionId={executionId} 
                        showDetails={true}
                        refreshInterval={10000}
                        onComplete={(result) => {
                          if (result && result.id) {
                            handleProcessingComplete(result);
                            if (result.status?.toLowerCase().includes('complet')) {
                              setActiveTab('processing');
                            }
                          }
                        }}
                      />
                    </div>
                  )}
                  
                  <div className="mt-6">
                    <div className="text-sm font-medium mb-2 flex justify-between items-center">
                      <span>Execution history:</span>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-8 w-8 p-0"
                        onClick={refreshExecutions}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                    </div>
                    {executions && executions.length > 0 ? (
                      <div className="space-y-4">
                        {executions.map((execution, index) => (
                          <div 
                            key={execution.id || index} 
                            className="flex items-center p-3 border rounded-md"
                          >
                            {(() => {
                              const statusType = getExecutionStatusType(execution.status);
                              switch (statusType) {
                                case 'completed':
                                  return <CheckCircle className="h-5 w-5 text-green-500 mr-3" />;
                                case 'failed':
                                  return <XCircle className="h-5 w-5 text-red-500 mr-3" />;
                                case 'running':
                                  return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin mr-3" />;
                                default:
                                  return <Clock className="h-5 w-5 text-yellow-500 mr-3" />;
                              }
                            })()}
                            
                            <div className="flex-grow">
                              <div className="font-medium">{execution.pipeline_name || 'Pipeline'}</div>
                              <div className="text-sm text-muted-foreground">
                                Estado: {(() => {
                                  const statusType = getExecutionStatusType(execution.status);
                                  switch (statusType) {
                                    case 'completed':
                                      return 'COMPLETADO';
                                    case 'failed':
                                      return 'FALLIDO';
                                    case 'running':
                                      return 'EN PROCESO';
                                    default:
                                      return 'PENDIENTE';
                                  }
                                })()}
                                {execution.completed_at && (
                                  <> • Completado: {new Date(execution.completed_at).toLocaleString()}</>
                                )}
                              </div>
                            </div>
                            
                            {(() => {
                              const statusType = getExecutionStatusType(execution.status);
                              if (statusType === 'completed') {
                                return (
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={() => {
                                      setActiveTab('processing');
                                    }}
                                  >
                                    Ver resultados
                                  </Button>
                                );
                              } else if (statusType === 'running' || statusType === 'pending') {
                                return (
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={() => {
                                      if(document?.id) {
                                        router.push(`/dashboard/documents/${document.id}?execution_id=${execution.id}`);
                                      }
                                    }}
                                  >
                                    Monitorear
                                  </Button>
                                );
                              }
                              return null;
                            })()}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-muted-foreground border rounded-md p-4">
                        <p>No pipeline executions found for this document.</p>
                        <p className="mt-2 text-sm">Use the panel on the right or click Refresh.</p>
                      </div>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
        
        <div className="w-full md:w-1/3">
          <Card>
            <CardHeader>
              <CardTitle>Process document</CardTitle>
              <CardDescription>
                Select a pipeline to process this document
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DocumentProcessPanel 
                documentId={document.id}
                documentName={documentTitle}
                onProcessed={handleProcessingComplete}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
