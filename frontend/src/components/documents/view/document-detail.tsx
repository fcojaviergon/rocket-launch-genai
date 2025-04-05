'use client';

import { useState, useEffect, useCallback } from 'react';
import { useDocuments } from '@/lib/hooks/documents';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, FileText, Clock, CheckCircle, Search, Layers, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { PipelineSelector } from '@/components/pipelines/execution';
import { Document } from '@/lib/types/document-types';
import { useRouter } from 'next/navigation';
import { PipelineProcessDialog } from '@/components/pipelines/execution';
import { toast } from 'sonner';
import { DocumentEmbeddingTab } from './document-embedding-tab';

interface DocumentDetailProps {
  documentId: string;
  onBack?: () => void;
}

export function DocumentDetail({ documentId, onBack }: DocumentDetailProps) {
  const [document, setDocument] = useState<Document | null>(null);
  const [processingResults, setProcessingResults] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showProcessDialog, setShowProcessDialog] = useState(false);
  const { getDocument } = useDocuments();
  const router = useRouter();

  // Function to update the document and its results
  const refreshDocument = useCallback(async () => {
    if (!documentId) return;

    try {
      setIsLoading(true);
      const doc = await getDocument(documentId);
      console.log('Document received:', doc);
      console.log('Pipeline executions:', doc?.pipeline_executions);
      console.log('Processing results:', doc?.processing_results);
      
      setDocument(doc);
      
      // Load the processing results
      if (doc?.processing_results && doc.processing_results.length > 0) {
        console.log('Using processing_results');
        setProcessingResults(doc.processing_results);
      } else if (doc?.pipeline_executions && doc.pipeline_executions.length > 0) {
        console.log('Using pipeline_executions');
        const completedExecutions = doc.pipeline_executions.filter(
          exec => exec.status === 'completed'
        );
        console.log('Completed executions:', completedExecutions);
        setProcessingResults(completedExecutions.map(exec => ({
          id: exec.id,
          pipeline_name: exec.pipeline_name || 'Pipeline without name',
          created_at: exec.completed_at || exec.created_at,
          result: exec.results
        })));
      } else {
        setProcessingResults([]);
      }
    } catch (err) {
      console.error('Error refreshing document:', err);
      toast.error('Error refreshing document');
    } finally {
      setIsLoading(false);
    }
  }, [documentId, getDocument]);

  useEffect(() => {
    if (documentId) {
      refreshDocument();
    }
  }, [documentId, refreshDocument]);

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      router.push('/dashboard/documents');
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <p className="text-muted-foreground mb-4">{error || 'Could not load document'}</p>
          <Button onClick={handleBack}>Back</Button>
        </CardContent>
      </Card>
    );
  }

  // Format content to display
  const formatContent = (content: string) => {
    // If it is binary or too long, we show an appropriate message
    if (content.startsWith('[Archivo') || content.startsWith('[Contenido binario')) {
      return <p className="text-muted-foreground text-sm">The content is a binary file</p>;
    }
    
    if (content.length > 10000) {
      return (
        <>
          <p className="text-muted-foreground text-sm mb-4">The content is too long (showing first 10000 characters)</p>
          <p className="whitespace-pre-wrap font-mono text-xs bg-muted p-4 rounded-md max-h-96 overflow-y-auto">
            {content.substring(0, 10000)}...
          </p>
        </>
      );
    }
    
    return (
      <p className="whitespace-pre-wrap font-mono text-xs bg-muted p-4 rounded-md max-h-96 overflow-y-auto">
        {content}
      </p>
    );
  };

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <Button 
          variant="outline" 
          onClick={handleBack} 
          className="flex items-center text-primary"
        >
          <ArrowLeft className="h-4 w-4 mr-1" /> Back
        </Button>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        <div className="w-full md:w-2/3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <FileText className="h-5 w-5 mr-2" />
                {document.title}
              </CardTitle>
              <div className="text-sm text-muted-foreground">
                Created: {new Date(document.created_at).toLocaleString()}
              </div>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="content">
                <TabsList className="mb-4">
                  <TabsTrigger value="content">Content</TabsTrigger>
                  <TabsTrigger value="processing">Processing</TabsTrigger>
                  <TabsTrigger value="embeddings">Embeddings & RAG</TabsTrigger>
                  <TabsTrigger value="metadata">Metadata</TabsTrigger>
                </TabsList>
                <TabsContent value="content" className="space-y-4">
                  {formatContent(document.content)}
                </TabsContent>
                <TabsContent value="processing" className="space-y-4">
                  <div className="flex justify-end mb-4">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={refreshDocument} 
                      className="flex items-center gap-1"
                    >
                      <RefreshCw className="h-4 w-4" />
                      Refresh results
                    </Button>
                  </div>
                  {processingResults.length > 0 ? (
                    <div className="space-y-4">
                      {processingResults.map((result, index) => (
                        <Card key={index}>
                          <CardContent className="pt-6">
                            <div className="flex items-center justify-between mb-4">
                              <div className="flex items-center">
                                <CheckCircle className="h-5 w-5 mr-2 text-green-500" />
                                <span className="font-medium">{result.pipeline_name}</span>
                              </div>
                              <div className="text-sm text-muted-foreground">
                                {new Date(result.created_at).toLocaleString()}
                              </div>
                            </div>
                            <div className="bg-muted p-4 rounded-md">
                              <pre className="whitespace-pre-wrap text-xs font-mono overflow-auto max-h-60">
                                {JSON.stringify(result.result || result.results, null, 2)}
                              </pre>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-10">
                      <p className="text-muted-foreground mb-4">This document has not been processed yet</p>
                      <Button onClick={() => setShowProcessDialog(true)}>
                        Process now
                      </Button>
                    </div>
                  )}
                </TabsContent>
                <TabsContent value="embeddings" className="space-y-4">
                  <DocumentEmbeddingTab document={document} />
                </TabsContent>
                <TabsContent value="metadata" className="space-y-4">
                  <Card>
                    <CardContent className="pt-6">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <p className="text-sm font-medium">ID</p>
                          <p className="text-sm text-muted-foreground font-mono">{document.id}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-sm font-medium">Owner</p>
                          <p className="text-sm text-muted-foreground">{document.user_id}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-sm font-medium">Type</p>
                          <p className="text-sm text-muted-foreground">{document.file_type || "Unknown"}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-sm font-medium">Size</p>
                          <p className="text-sm text-muted-foreground">
                            {document.file_size 
                              ? `${Math.round(document.file_size / 1024)} KB` 
                              : "Unknown"}
                          </p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-sm font-medium">Created</p>
                          <p className="text-sm text-muted-foreground">{new Date(document.created_at).toLocaleString()}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-sm font-medium">Updated</p>
                          <p className="text-sm text-muted-foreground">{new Date(document.updated_at).toLocaleString()}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
        
        <div className="w-full md:w-1/3">
          <Card>
            <CardHeader>
              <CardTitle>Process document</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <PipelineSelector 
                onSelect={(pipeline) => {
                  // Here we could store the selected pipeline
                  console.log('Selected pipeline:', pipeline);
                }}
              />
              <Button className="w-full" onClick={() => setShowProcessDialog(true)}>
                Process document
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <PipelineProcessDialog
        isOpen={showProcessDialog}
        onClose={() => setShowProcessDialog(false)}
        documentId={document.id}
        documentName={document.title}
        onProcessed={() => {
          // Refrescar documento y resultados cuando se completa el procesamiento
          refreshDocument();
          toast.success('Documento procesado con éxito');
        }}
      />
    </div>
  );
} 