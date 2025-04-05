'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send, Search, X, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import { api } from '@/lib/api'; // Import the centralized API

interface Source {
  document_name: string;
  document_type: string;
  relevance: number;
}

interface RagResponse {
  answer: string;
  sources: Source[];
  conversation_id?: string;
  created_at: string | Date;
}

interface ChatResponse {
  conversation_id: string;
  message: {
    id: string;
    content: string;
    role: string;
    timestamp: string | Date;
  };
}

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'system';
  timestamp: Date;
  sources?: Source[];
}

export default function MessagesPage() {
  const [isRagMode, setIsRagMode] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: 'Welcome to Rocket Launch GenAI Platform. This section works to search documents processed by the AI',
      sender: 'system',
      timestamp: new Date(Date.now() - 3600000)
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      if (isRagMode) {
        // Use the centralized API for RAG
        const data = await api.chat.ragQuery({
          query: inputValue
        }) as RagResponse;
        
        const systemMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: data.answer,
          sender: 'system',
          timestamp: new Date(data.created_at),
          sources: data.sources
        };
        setMessages(prev => [...prev, systemMessage]);
      } else {
          // Normal chat using the centralized API
        const data = await api.chat.sendMessage({
          content: inputValue
        }) as ChatResponse;
        
        const systemMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: data.message.content,
          sender: 'system',
          timestamp: new Date(data.message.timestamp)
        };
        setMessages(prev => [...prev, systemMessage]);
      }
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, there was an error processing your message.',
        sender: 'system',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      setInputValue('');
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="p-6 w-full h-full flex flex-col">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">RAG</h1>
          <p className="text-muted-foreground">Communicate with the AI RAG assistant</p>
        </div>
        <Button
          variant={isRagMode ? "destructive" : "secondary"}
          size="sm"
          onClick={() => setIsRagMode(!isRagMode)}
        >
          {isRagMode ? (
            <>
              <X className="w-4 h-4 mr-2" />
              Disable search
            </>
          ) : (
            <>
              <Search className="w-4 h-4 mr-2" />
              Search in documents
            </>
          )}
        </Button>
      </div>

      <Card className="flex-1 flex flex-col">
        <CardHeader>
          <CardTitle>Chat with AI assistant for RAG</CardTitle>
          <CardDescription>
            {isRagMode 
              ? "Perform queries on your documents"
              : "Perform queries and get intelligent answers"}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto mb-4 space-y-4">
            {messages.map(message => (
              <div 
                key={message.id} 
                className={cn("flex", message.sender === 'user' ? 'justify-end' : 'justify-start')}
              >
                <div 
                  className={cn(
                    "max-w-[80%] rounded-lg p-3",
                    message.sender === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'
                  )}
                >
                  <p>{message.content}</p>
                  {message.sources && (
                    <div className="mt-2 space-y-1">
                      <p className="text-xs font-medium">Sources:</p>
                      {message.sources.map((source, idx) => (
                        <div key={idx} className="flex items-center gap-1">
                          <FileText className="h-3 w-3" />
                          <span className="text-xs">{source.document_name}</span>
                          <Badge variant="secondary" className="text-xs">
                            {Math.round(source.relevance * 100)}% relevant
                          </Badge>
                        </div>
                      ))}
                    </div>
                  )}
                  <p className="text-xs mt-1 opacity-70">{formatTime(message.timestamp)}</p>
                </div>
              </div>
            ))}
            
            {loading && (
              <div className="flex justify-start">
                <div className="bg-muted max-w-[80%] rounded-lg p-3">
                  <div className="flex items-center space-x-2">
                    <div className="h-2 w-2 bg-blue-600 dark:bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="h-2 w-2 bg-blue-600 dark:bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    <div className="h-2 w-2 bg-blue-600 dark:bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '600ms' }}></div>
                    <span className="ml-1 text-sm text-gray-500 dark:text-gray-400">Processing message...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
          
          <div className="flex gap-2">
            <Input
              placeholder={isRagMode ? "Ask about your documents..." : "Write your message..."}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !loading && handleSendMessage()}
              className="flex-1"
              disabled={loading}
            />
            <Button onClick={handleSendMessage} size="default" disabled={loading}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
