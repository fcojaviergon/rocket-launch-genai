'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search, Layers } from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { api } from '@/lib/api';

interface DocumentEmbeddingTabProps {
  document: any; // We use 'any' to avoid type problems between different interfaces
}

interface EmbeddingResponse {
  status: string;
  message?: string;
  detail?: string;
  document_id?: string;
  model?: string;
  chunk_count?: number;
}

interface SearchResponse {
  status: string;
  query?: string;
  results?: SearchResultItem[];
  count?: number;
  message?: string;
  detail?: string;
}

interface SearchResultItem {
  document_id: string;
  document_title: string;
  chunk_text: string;
  chunk_index: number;
  similarity: number;
  metadata?: Record<string, any>;
}

export function DocumentEmbeddingTab({ document }: DocumentEmbeddingTabProps) {
  // States for the generation of embeddings
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [processingSuccess, setProcessingSuccess] = useState<string | null>(null);
  const [embeddingModel, setEmbeddingModel] = useState<string>('text-embedding-3-small');
  const [chunkSize, setChunkSize] = useState<number>(1000);
  const [chunkOverlap, setChunkOverlap] = useState<number>(200);

  // States for the RAG search
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [minSimilarity, setMinSimilarity] = useState<number>(0.7);
  const [resultLimit, setResultLimit] = useState<number>(5);

  // Function to process embeddings
  const processEmbeddings = async () => {
    if (!document?.id) {
      toast.error('No document selected');
      return;
    }

    setIsProcessing(true);
    setProcessingError(null);
    setProcessingSuccess(null);

    try {
      const response = await api.documents.processEmbeddings(document.id, {
        model: embeddingModel,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      }) as EmbeddingResponse;

      if (response.status === 'success') {
        setProcessingSuccess(response.message || 'Embeddings processed successfully');
        toast.success(response.message || 'Embeddings processed successfully');
      } else {
        setProcessingError('Error processing embeddings: ' + (response.detail || 'Invalid response'));
        toast.error('Error processing embeddings');
      }
    } catch (error: any) {
      console.error('Error processing embeddings:', error);
      setProcessingError('Error processing embeddings: ' + (error.message || 'Unknown error'));
      toast.error('Error processing embeddings');
    } finally {
      setIsProcessing(false);
    }
  };

  // Function to perform RAG search
  const performSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a query to search');
      return;
    }

    setIsSearching(true);
    setSearchError(null);
    setSearchResults([]);

    try {
      const searchParams = {
        query: searchQuery,
        model: embeddingModel,
        limit: resultLimit,
        min_similarity: minSimilarity,
        document_id: document.id,
      };
      
      console.log('Sending search with parameters:', searchParams);
      
      const response = await api.documents.search(searchParams);
      console.log('Search response:', response);
      
      // Verify the format of the response and adapt it if necessary
      if (Array.isArray(response)) {
        // The response is directly an array of results
        setSearchResults(response);
        
        if (response.length === 0) {
          toast.info('No results found');
        } else {
          toast.success(`Found ${response.length} results`);
        }
        
      } else if (response && typeof response === 'object') {
        // The response is an object with the expected structure
        const responseObj = response as SearchResponse;
        
        if (responseObj.status === 'success') {
          setSearchResults(responseObj.results || []);
          
          if ((responseObj.results || []).length === 0) {
            toast.info('No results found');
          } else {
            const resultCount = responseObj.count || (responseObj.results ? responseObj.results.length : 0);
            toast.success(`Found ${resultCount} results`);
          }
        } else {
          setSearchError('Error in search: ' + (responseObj.detail || 'Invalid response'));
          toast.error('Error in search');
        }
      } else {
        // Unknown response format
        setSearchError('Error in search: Unexpected response format');
        toast.error('Error in response format');
      }
    } catch (error: any) {
      console.error('Error in RAG search:', error);
      setSearchError('Error in search: ' + (error.message || 'Unknown error'));
      toast.error('Error in search');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <Tabs defaultValue="process">
      <TabsList>
        <TabsTrigger value="process">
          <Layers className="h-4 w-4 mr-2" /> Process Embeddings
        </TabsTrigger>
        <TabsTrigger value="search">
          <Search className="h-4 w-4 mr-2" /> RAG Search
        </TabsTrigger>
      </TabsList>
      
      <TabsContent value="process" className="space-y-4 py-4">
        <Card>
          <CardHeader>
            <CardTitle>Generate Embeddings for Document</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Embedding Model</Label>
              <Select 
                value={embeddingModel} 
                onValueChange={setEmbeddingModel}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="text-embedding-3-small">text-embedding-3-small (OpenAI)</SelectItem>
                  <SelectItem value="text-embedding-3-large">text-embedding-3-large (OpenAI)</SelectItem>
                  <SelectItem value="text-embedding-ada-002">text-embedding-ada-002 (OpenAI - Legacy)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <Label>Chunk Size</Label>
                <span className="text-sm">{chunkSize} characters</span>
              </div>
              <Slider
                value={[chunkSize]}
                min={100}
                max={5000}
                step={100}
                onValueChange={(value) => setChunkSize(value[0])}
              />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <Label>Chunk Overlap</Label>
                <span className="text-sm">{chunkOverlap} characters</span>
              </div>
              <Slider
                value={[chunkOverlap]}
                min={0}
                max={1000}
                step={50}
                onValueChange={(value) => setChunkOverlap(value[0])}
              />
            </div>
            
            <Button 
              onClick={processEmbeddings} 
              disabled={isProcessing}
              className="w-full"
            >
              {isProcessing ? 'Processing...' : 'Process Embeddings'}
            </Button>
            
            {processingError && (
              <Alert variant="destructive">
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{processingError}</AlertDescription>
              </Alert>
            )}
            
            {processingSuccess && (
              <Alert>
                <AlertTitle>Success</AlertTitle>
                <AlertDescription>{processingSuccess}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabsContent>
      
      <TabsContent value="search" className="space-y-4 py-4">
        <Card>
          <CardHeader>
            <CardTitle>Semantic Search (RAG)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Query</Label>
              <Textarea
                placeholder="Write your query here..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                rows={3}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Embedding Model</Label>
              <Select 
                value={embeddingModel} 
                onValueChange={setEmbeddingModel}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="text-embedding-3-small">text-embedding-3-small (OpenAI)</SelectItem>
                  <SelectItem value="text-embedding-3-large">text-embedding-3-large (OpenAI)</SelectItem>
                  <SelectItem value="text-embedding-ada-002">text-embedding-ada-002 (OpenAI - Legacy)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <Label>Minimum Similarity</Label>
                <span className="text-sm">{(minSimilarity * 100).toFixed(0)}%</span>
              </div>
              <Slider
                value={[minSimilarity]}
                min={0}
                max={1}
                step={0.05}
                onValueChange={(value) => setMinSimilarity(value[0])}
              />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <Label>Result Limit</Label>
                <span className="text-sm">{resultLimit}</span>
              </div>
              <Slider
                value={[resultLimit]}
                min={1}
                max={20}
                step={1}
                onValueChange={(value) => setResultLimit(value[0])}
              />
            </div>
            
            <Button 
              onClick={performSearch} 
              disabled={isSearching}
              className="w-full"
            >
              {isSearching ? 'Searching...' : 'Search'}
            </Button>
            
            {searchError && (
              <Alert variant="destructive">
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{searchError}</AlertDescription>
              </Alert>
            )}
            
            {searchResults.length > 0 && (
              <div className="space-y-4 mt-6">
                <h3 className="text-lg font-medium">Results ({searchResults.length})</h3>
                <ul className="divide-y divide-gray-200 rounded-md border border-gray-200">
                  {searchResults.map((result, index) => (
                    <li key={`${result.document_id}-${result.chunk_index}-${index}`} className="p-4 hover:bg-gray-50">
                      <p className="text-sm font-medium text-indigo-600">
                        Document: {result.document_title} (ID: {result.document_id})
                      </p>
                      <p className="mt-1 text-xs text-gray-500">
                        Chunk Index: {result.chunk_index} | Similarity: {(result.similarity * 100).toFixed(2)}%
                      </p>
                      <blockquote className="mt-2 border-l-4 border-gray-300 pl-4 italic text-sm text-gray-700">
                        {result.chunk_text}
                      </blockquote>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
} 