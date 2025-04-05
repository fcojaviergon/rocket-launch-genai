'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Spinner } from '@/components/ui';
import ProcessingStatus from '@/components/processing-status';
import axios from 'axios';

interface Document {
  id: string;
  name: string;
  type: string;
  size: number;
  created_at: string;
  user_id: string;
}

interface BatchProcessResponse {
  batch_id: string;
  status: string;
}

const BatchProcessPage = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [processing, setProcessing] = useState<boolean>(false);
  const [batchId, setBatchId] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await axios.get<Document[]>('/api/v1/documents');
      setDocuments(response.data);
    } catch (error: any) {
      toast.error('Error loading documents', {
        description: error.response?.data?.detail || 'Could not load documents'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDocument = (documentId: string) => {
    setSelectedDocuments(prev => {
      if (prev.includes(documentId)) {
        return prev.filter(id => id !== documentId);
      } else {
        return [...prev, documentId];
      }
    });
  };

  const handleSelectAll = () => {
    if (selectedDocuments.length === documents.length) {
      setSelectedDocuments([]);
    } else {
      setSelectedDocuments(documents.map(doc => doc.id));
    }
  };

  const handleProcessDocuments = async () => {
    if (selectedDocuments.length === 0) {
      toast.warning('Select documents', {
        description: 'You must select at least one document to process'
      });
      return;
    }

    try {
      setProcessing(true);
      // Asumiendo que esta API existe en el backend
      const response = await axios.post<BatchProcessResponse>('/api/v1/pipeline/batch-process', {
        document_ids: selectedDocuments,
        async_processing: true
      });
      
      setBatchId(response.data.batch_id);
      
      toast.success('Processing started', {
        description: `Processing of ${selectedDocuments.length} documents has been started`
      });
    } catch (error: any) {
      toast.error('Error starting processing', {
        description: error.response?.data?.detail || 'Could not start processing'
      });
      setProcessing(false);
    }
  };

  const handleProcessingComplete = () => {
    setProcessing(false);
    fetchDocuments(); // Update the list of documents
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
    else return (bytes / 1073741824).toFixed(1) + ' GB';
  };

  return (
    <div className="container py-8">
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">Batch processing</h1>
          <Button 
            variant="default" 
            onClick={handleProcessDocuments} 
            disabled={selectedDocuments.length === 0 || processing}
          >
            {(processing && !batchId) ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                <span>Processing...</span>
              </>
            ) : (
              'Process selected documents'
            )}
          </Button>
        </div>

        {batchId && (
          <div className="mb-6">
            <ProcessingStatus 
              batchId={batchId} 
              onComplete={handleProcessingComplete}
              refreshInterval={3000}
            />
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Available documents</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center items-center py-10">
                <Spinner className="h-8 w-8" />
              </div>
            ) : documents.length === 0 ? (
              <p className="text-center py-10">
                No documents available. Upload some documents first.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">
                        <Checkbox 
                          checked={selectedDocuments.length === documents.length && documents.length > 0}
                          onCheckedChange={handleSelectAll}
                        />
                      </TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead>Creation date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {documents.map((doc) => (
                      <TableRow key={doc.id}>
                        <TableCell>
                          <Checkbox 
                            checked={selectedDocuments.includes(doc.id)}
                            onCheckedChange={() => handleSelectDocument(doc.id)}
                            disabled={processing}
                          />
                        </TableCell>
                        <TableCell>{doc.name}</TableCell>
                        <TableCell>{doc.type}</TableCell>
                        <TableCell>{formatFileSize(doc.size)}</TableCell>
                        <TableCell>{new Date(doc.created_at).toLocaleString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default BatchProcessPage;
