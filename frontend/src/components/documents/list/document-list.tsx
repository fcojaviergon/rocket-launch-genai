'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Search, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { PipelineSelector } from '@/components/pipelines/execution';
import { useDocuments } from '@/lib/hooks/documents';
import { Document } from '@/lib/types/document-types';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';

interface DocumentListProps {
  onSelectDocuments?: (documentIds: string[]) => void;
  onProcess?: (documentId: string, pipelineName: string) => void;
  onDelete?: (documentId: string) => void;
  onRefresh?: () => void;
}

export function DocumentList({ 
  onSelectDocuments, 
  onProcess, 
  onDelete,
  onRefresh
}: DocumentListProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPipeline, setSelectedPipeline] = useState('');
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const { documents, isLoading, error, fetchDocuments, deleteDocument } = useDocuments();
  
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);
  
  // Notify changes in selection
  useEffect(() => {
    if (onSelectDocuments) {
      onSelectDocuments(selectedDocuments);
    }
  }, [selectedDocuments, onSelectDocuments]);

  // Filter documents based on search
  const filteredDocuments = documents.filter(doc => 
    doc.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Handle document selection
  const toggleDocumentSelection = (id: string) => {
    setSelectedDocuments(prev => 
      prev.includes(id) 
        ? prev.filter(docId => docId !== id) 
        : [...prev, id]
    );
  };

  // Format file size
  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
    else return (bytes / 1073741824).toFixed(1) + ' GB';
  };

  // Handle document deletion
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) {
      return;
    }
    
    try {
      await deleteDocument(id);
      // Remove from selected documents if it was selected
      setSelectedDocuments(prev => prev.filter(docId => docId !== id));
      
      if (onDelete) onDelete(id);
      if (onRefresh) onRefresh();
    } catch (error) {
      console.error('Error deleting document:', error);
    }
  };

  return (
    <div className="space-y-4">
      <Card className="mb-6">
        <CardHeader className="pb-3">
          <CardTitle>Search documents</CardTitle>
          <CardDescription>Find your documents quickly</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by file name..."
                className="pl-8"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="w-full md:w-1/3">
              <PipelineSelector 
                onSelect={setSelectedPipeline}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>My documents</CardTitle>
          <CardDescription>Manage your uploaded documents</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-10">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mx-auto mb-3"></div>
              <p className="text-muted-foreground"></p>
            </div>
          ) : filteredDocuments.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]">
                    <input 
                      type="checkbox" 
                      checked={selectedDocuments.length === filteredDocuments.length && filteredDocuments.length > 0}
                      onChange={() => {
                        if (selectedDocuments.length === filteredDocuments.length) {
                          setSelectedDocuments([]);
                        } else {
                          setSelectedDocuments(filteredDocuments.map(d => d.id));
                        }
                      }}
                      className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  </TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDocuments.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="w-[40px]">
                      <input 
                        type="checkbox" 
                        checked={selectedDocuments.includes(doc.id)}
                        onChange={() => toggleDocumentSelection(doc.id)}
                        className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                    </TableCell>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <Link href={`/dashboard/documents/${doc.id}`} className="hover:underline">
                          {doc.title}
                        </Link>
                      </div>
                    </TableCell>
                    <TableCell>
                      {doc.file_type?.toUpperCase() || 'DOC'}
                    </TableCell>
                    <TableCell>
                      {formatFileSize(doc.file_size)}
                    </TableCell>
                    <TableCell>
                      {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true, locale: es })}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => onProcess && onProcess(doc.id, selectedPipeline)}
                          disabled={!selectedPipeline}
                        >
                          Process
                        </Button>
                        <Button 
                          variant="destructive" 
                          size="sm"
                          onClick={() => handleDelete(doc.id)}
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-10">
              <p className="text-muted-foreground">No documents found</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
} 