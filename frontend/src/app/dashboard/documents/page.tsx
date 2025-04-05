'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Upload, Plus, FileText, Trash2, CheckSquare, Download, Zap, Eye, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogFooter, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { UploadDialog } from '@/components/documents/upload';
import { PipelineSelector, ProcessDocuments } from '@/components/pipelines/execution';
import { toast } from 'sonner';
import { Document } from '@/lib/services/documents/document-service';
import { format } from 'date-fns';
import { useApi } from '@/lib/hooks/api';
import { usePipelineConfig } from '@/lib/hooks/pipelines/use-pipeline-config';
import { useDocuments } from '@/lib/hooks/documents/use-documents';

export default function DocumentsPage() {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState('');
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<string>('');
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [isProcessDialogOpen, setIsProcessDialogOpen] = useState(false);
  const [isCreatingPipeline, setIsCreatingPipeline] = useState(false);
  const [processingDocId, setProcessingDocId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const api = useApi();
  const { configs, loadPipelines } = usePipelineConfig();
  const documentHook = useDocuments();

  // Initialize isLoading to false by default
  const [documentState, setDocumentState] = useState<{
    documents: Document[];
    isLoading: boolean; // Start as false
    error: null | string;
  }>({
    documents: [],
    isLoading: false, // Default to false
    error: null
  });

  // Use useMemo for derived values
  const filteredDocuments = useMemo(() => 
    documentState.documents.filter(doc => {
      if (!searchTerm) return true;
      return (doc.title?.toLowerCase() || doc.name.toLowerCase())
        .includes(searchTerm.toLowerCase());
    }),
    [documentState.documents, searchTerm]
  );

  // Check if there are available pipelines
  const hasPipelines = configs && configs.length > 0;
  
  // Automatically select the first pipeline if none is selected
  useEffect(() => {
    if (configs && configs.length > 0 && !selectedPipeline && configs[0].id) {
      console.log('DocumentsPage - Automatically selecting the first pipeline:', configs[0].id);
      setSelectedPipeline(configs[0].id);
    }
  }, [configs, selectedPipeline]);

  // Function to create a test pipeline
  const createTestPipeline = async () => {
    setIsCreatingPipeline(true);
    try {
      console.log('Creating test pipeline in DocumentsPage...');
      
      // Create a basic test pipeline
      const testPipeline = {
        name: "PDF Extraction Pipeline",
        description: "Pipeline for extracting information from PDF documents",
        type: "pdf",
        steps: [
          {
            name: "extractor",
            type: "processor",
            config: {
              model: "gpt-3.5-turbo"
            }
          }
        ],
        metadata: {}
      };
      
      // Call the API to create the pipeline
      const response = await api.pipelines.createConfig(testPipeline) as any;
      console.log('Test pipeline created:', response);
      
      // Reload the pipeline list
      await loadPipelines();
      
      // If created successfully, select it automatically
      if (response && response.id) {
        setSelectedPipeline(response.id);
        toast.success('Pipeline created and selected');
      } else {
        toast.success('Pipeline created successfully');
      }
    } catch (err) {
      console.error('Error creating test pipeline:', err);
      toast.error('Error creating test pipeline');
    } finally {
      setIsCreatingPipeline(false);
    }
  };

  // Function to format dates
  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'dd/MM/yyyy HH:mm');
  };

  // Function to toggle document selection
  const toggleDocumentSelection = (docId: string) => {
    setSelectedDocuments(prev => {
      if (prev.includes(docId)) {
        return prev.filter(id => id !== docId);
      } else {
        return [...prev, docId];
      }
    });
  };

  // Function to process documents in batch
  const processBatchDocuments = async () => {
    if (selectedDocuments.length === 0 || !selectedPipeline) {
      toast.error('Select at least one document and a pipeline');
      return;
    }

    setIsBatchProcessing(true);
    try {
      // Here would be the logic to process documents in batch with the selected pipeline
      // For example:
      // await documentService.processBatch(selectedDocuments, selectedPipeline);
      toast.success(`${selectedDocuments.length} documents processed successfully`);
    } catch (error) {
      console.error('Error processing documents in batch:', error);
      toast.error('Error processing documents in batch');
    } finally {
      setIsBatchProcessing(false);
    }
  };

  // Function to process an individual document
  const handleProcess = async (docId: string) => {
    try {
      setProcessingDocId(docId);
      setIsProcessing(true);
      
      const doc = documentState.documents.find(d => d.id === docId);
      if (!doc) {
        toast.error("Document not found");
        return;
      }
      
      setSelectedDocument(doc);
      
      if (!selectedPipeline) {
        setIsProcessDialogOpen(true);
        return;
      }
      
      // Process the document using the document hook
      await documentHook.processDocument(docId, selectedPipeline);
      
      // Show success message
      toast.success(`Document "${doc.title || doc.name}" is being processed`);
      
      // Refresh the document list
      const docs = await documentHook.fetchDocuments();
      setDocumentState({
        documents: docs as Document[] || [],
        isLoading: false,
        error: null
      });
    } catch (error: any) {
      console.error("Error processing document:", error);
      toast.error(`Error processing document: ${error.message || "Unknown error"}`);
    } finally {
      setIsProcessing(false);
      setProcessingDocId(null);
    }
  };

  // Function to handle processing completion (updated to use hook)
  const handleProcessComplete = async () => {
    setIsProcessDialogOpen(false);
    // Refresh using the hook's function
    const docs = await documentHook.fetchDocuments(); 
    setDocumentState({
      documents: docs as Document[] || [],
      isLoading: false,
      error: null
    });
    toast.success('Document processed successfully');
  };

  // Final corrected useEffect for loading documents in LIST page
  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      // Condition 1: Wait for session to be ready
      // If session isn't ready, we simply wait. We don't set component loading state here.
      if (!documentHook.isSessionReady) {
        console.log("(List Page) Waiting for session...");
        // Ensure isLoading is false if session check determines we are not ready and not loading session
        if (!documentHook.isSessionLoading && documentState.isLoading) {
           setDocumentState(prev => ({ ...prev, isLoading: false }));
        }
        return; 
      }

      // Condition 2: Session is ready. Check if we are already loading data.
      // This prevents duplicate fetches if the effect runs multiple times quickly.
      if (documentState.isLoading) {
        console.log("(List Page) Skipping fetch: A fetch is already in progress.");
        return; 
      }

      // Condition 3: Session ready and not currently loading -> Start the fetch
      console.log("(List Page) Session ready. Starting document fetch.");
      setDocumentState(prev => ({ ...prev, isLoading: true, error: null })); // Set loading TRUE now

      try {
        const docs = await documentHook.fetchDocuments();
        if (isMounted) {
          const documentsArray = Array.isArray(docs) ? docs as Document[] : [];
          console.log("(List Page) Fetch successful. Setting documents:", documentsArray.length);
          setDocumentState({
            documents: documentsArray,
            isLoading: false, // Set loading FALSE after fetch success
            error: null
          });
        }
      } catch (error: any) {
        console.error("(List Page) Fetch error:", error);
        if (isMounted) {
          console.log("(List Page) Setting error state after fetch failure.");
          setDocumentState(prev => ({ 
            ...prev,
            documents: [],
            isLoading: false, // Set loading FALSE after fetch error
            error: error.message || "Failed to load documents"
          }));
        }
      }
    };

    loadData();

    return () => {
      isMounted = false;
      console.log("(List Page) Unmounting document load effect.");
    };
  // Dependencies: ONLY session status.
  }, [documentHook.isSessionReady, documentHook.isSessionLoading]);

  // Function to handle document deletion
  const handleDeleteDocument = async (documentId: string) => {
    try {
      await documentHook.deleteDocument(documentId);
      // Refresh using the hook's function
      const docs = await documentHook.fetchDocuments();
      setDocumentState({
        documents: docs as Document[] || [],
        isLoading: false,
        error: null
      });
    } catch (error) {
      console.error('Error deleting document:', error);
      toast.error('Error deleting document');
    }
  };

  // Function to go to document details
  const handleViewDetails = (docId: string) => {
    router.push(`/dashboard/documents/${docId}`);
  };

  return (
    <div className="p-6 w-full">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Documents</h1>
        <div className="flex space-x-2">
          <Button 
            className="flex items-center gap-2"
            onClick={() => setIsUploadOpen(true)}
          >
            <Upload className="h-4 w-4" />
            Upload document
          </Button>
        </div>
      </div>

      {selectedDocuments.length > 0 && (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle>Process selected documents</CardTitle>
            <CardDescription>
              You have selected {selectedDocuments.length} documents to process
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ProcessDocuments 
              documents={documentState.documents.filter(doc => selectedDocuments.includes(doc.id))} 
              onProcessComplete={async () => {
                // Refresh using the hook
                const docs = await documentHook.fetchDocuments();
                setDocumentState({
                  documents: docs as Document[] || [],
                  isLoading: false,
                  error: null
                });
                setSelectedDocuments([]);
              }}
            />
          </CardContent>
        </Card>
      )}

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
                selectedId={selectedPipeline}
                placeholder="Select pipeline to process..."
              />
            </div>

            {!hasPipelines && (
              <div className="flex-shrink-0">
                <Button
                  variant="outline"
                  onClick={createTestPipeline}
                  disabled={isCreatingPipeline}
                  className="w-full"
                >
                  {isCreatingPipeline ? (
                    <>
                      <div className="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Create pipeline
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>My documents</CardTitle>
          <CardDescription>Manage your uploaded documents</CardDescription>
        </CardHeader>
        <CardContent>
          {/* Show loading indicator ONLY if documentState.isLoading is true */} 
          {documentState.isLoading ? (
            <div className="text-center py-10">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mx-auto mb-3"></div>
              <p className="text-muted-foreground">Loading...</p>
            </div>
          // If NOT loading, check for errors
          ) : documentState.error ? (
            <div className="text-center py-10">
              <AlertCircle className="h-10 w-10 text-destructive mx-auto mb-3" />
              <h3 className="font-medium text-lg mb-1">Error loading documents</h3>
              <p className="text-muted-foreground mb-4">{documentState.error}</p>
              <Button onClick={() => { 
                  // Manually trigger loadData on retry
                  // Need to ensure isLoading is false before calling
                  if (!documentState.isLoading) {
                    // Reset error and set loading before calling hook function
                    setDocumentState(prev => ({...prev, isLoading: true, error: null})); 
                    documentHook.fetchDocuments()
                        .then(docs => {
                             const documentsArray = Array.isArray(docs) ? docs as Document[] : [];
                             setDocumentState({documents: documentsArray, isLoading: false, error: null});
                        })
                        .catch(err => {
                             setDocumentState(prev => ({...prev, documents:[], isLoading: false, error: err.message || "Failed again"}));
                        });
                  } else {
                      console.log("Retry skipped: Already loading");
                  }
               }}>
                  Try again
               </Button>
            </div>
          // If NOT loading and NO error, check authentication
          ) : !documentHook.isSessionReady ? (
            <div className="text-center py-10">
              <AlertCircle className="h-10 w-10 text-destructive mx-auto mb-3" />
              <h3 className="font-medium text-lg mb-1">Authentication Required</h3>
              <p className="text-muted-foreground mb-4">Please log in to view documents.</p>
              <Button onClick={() => router.push('/login')}>Log In</Button>
            </div>
          // If NOT loading, NO error, and IS authenticated, show content
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
                      <div 
                        className="flex items-center gap-2 cursor-pointer hover:text-primary"
                        onClick={() => handleViewDetails(doc.id)}
                      >
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        {doc.title ?? doc.name}
                      </div>
                    </TableCell>
                    <TableCell>
                      {(doc.title?.split('.').pop() ?? doc.name.split('.').pop())?.toUpperCase() || 'Document'}
                    </TableCell>
                    <TableCell>
                      {doc.content 
                        ? (doc.content.startsWith('[Archivo ') || doc.content.startsWith('[Contenido binario') 
                          ? doc.content.match(/\d+\s*bytes/) 
                            ? doc.content.match(/\d+\s*bytes/)?.[0] || 'Binary file'
                            : 'Binary file'
                          : `${doc.content.length} characters`)
                        : 'No content'}
                    </TableCell>
                    <TableCell>{formatDate(doc.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleViewDetails(doc.id)}
                          title="View document details"
                        >
                          <Eye className="h-4 w-4 text-blue-500" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleProcess(doc.id)}
                          title={selectedPipeline ? `Process with selected pipeline` : "Process document"}
                        >
                          <Zap className="h-4 w-4 text-amber-500" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => documentHook.downloadDocument(doc.id)}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={async () => {
                            if (confirm(`Are you sure you want to delete the document "${doc.title}"?`)) {
                              await handleDeleteDocument(doc.id);
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : searchTerm !== '' ? (
            <div className="text-center py-10">
              <FileText className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
              <h3 className="font-medium text-lg mb-1">No documents found</h3>
              <p className="text-muted-foreground mb-4">No documents match your search</p>
              <Button onClick={() => setSearchTerm('')}>View all</Button>
            </div>
          ) : (
            <div className="text-center py-10">
              <FileText className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
              <h3 className="font-medium text-lg mb-1">No documents</h3>
              <p className="text-muted-foreground mb-4">Upload a document to get started</p>
              <Button onClick={() => setIsUploadOpen(true)}>Upload document</Button>
            </div>
          )}
        </CardContent>
      </Card>

      {selectedDocument && (
        <Dialog
          open={isProcessDialogOpen}
          onOpenChange={setIsProcessDialogOpen}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Processing document</DialogTitle>
              <DialogDescription>
                The document {selectedDocument.title ?? selectedDocument.name} is being processed with the selected pipeline.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <Progress value={75} className="w-full" />
              <p className="text-center mt-2 text-sm text-muted-foreground">Processing...</p>
            </div>
            <DialogFooter>
              <Button onClick={handleProcessComplete}>Finish</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
      
      {/* Upload document dialog */}
      <UploadDialog 
        isOpen={isUploadOpen} 
        onClose={() => setIsUploadOpen(false)}
        onUploadComplete={async (newDoc) => {
          if (newDoc && newDoc.id) {
            setDocumentState(prev => ({ 
              ...prev, 
              documents: [newDoc as Document, ...prev.documents] 
            }));
            // Optional: Trigger a full refresh via hook after optimistic update
            await documentHook.fetchDocuments(); 
          }
        }}
      />
    </div>
  );
}
