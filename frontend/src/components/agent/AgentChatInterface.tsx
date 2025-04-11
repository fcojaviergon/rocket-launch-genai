'use client';

import React, { useState, FormEvent, useRef, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getSession } from "next-auth/react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PlusIcon, Cross1Icon, CheckIcon, Pencil1Icon, TrashIcon } from '@radix-ui/react-icons';
import { RefreshCw, Loader, UserCircle, ArrowRight, Bot as BotIcon, MessageSquareIcon, Code, Eye, EyeOff, Terminal, Server } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Terminal as TerminalIcon } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { ChevronDown } from 'lucide-react';

// --- Types ---
interface Message {
  id: string | number;
  role: 'user' | 'agent' | 'assistant' | 'error' | 'tool' | 'thinking' | 'observation';
  text: string;
  timestamp?: string;
  isVisible?: boolean;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at: string;
  updated_at?: string;
}

// MCP Server types
interface McpServer {
  name: string;
  description: string;
  commands: string[];
  hasCommands: boolean;
}

interface McpServersResponse {
  status: string;
  servers: Record<string, McpServer>;
}

// --- Component ---
export default function AgentChatInterface() {
  const [input, setInput] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [editingConversation, setEditingConversation] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState<string>('');
  const [showThinking, setShowThinking] = useState<boolean>(true);
  const inputRef = useRef<HTMLInputElement>(null);
  const [mcpServers, setMcpServers] = useState<Record<string, McpServer>>({});
  const [loadingMcpServers, setLoadingMcpServers] = useState<boolean>(false);
  const [mcpServersError, setMcpServersError] = useState<string | null>(null);
  const [mcpPopoverOpen, setMcpPopoverOpen] = useState<boolean>(false);

  // Enhanced date formatting function with better error handling
  const formatDate = (dateString?: string): string => {
    if (!dateString) return "Recent";
    
    try {
      // Make sure the date string is properly formatted
      const normalizedDateStr = dateString.replace(/(\d{4}-\d{2}-\d{2})(T)(\d{2}:\d{2}:\d{2})(\.\d+)?([Z+-].*)/, '$1T$3Z');
      const date = new Date(normalizedDateStr);
      
      // Check if date is valid
      if (isNaN(date.getTime())) {
        console.warn(`Invalid date string: ${dateString}`);
        return "Recent";
      }
      
      // Format the date based on how recent it is
      const now = new Date();
      const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
      
      if (diffDays === 0) {
        return "Today";
      } else if (diffDays === 1) {
        return "Yesterday";
      } else if (diffDays < 7) {
        return `${diffDays} days ago`;
      } else {
        return date.toLocaleDateString();
      }
    } catch (error) {
      console.warn(`Error formatting date: ${dateString}`, error);
      return "Recent"; 
    }
  };

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const session = await getSession();
        setIsAuthenticated(!!session?.accessToken);
        if (session?.accessToken) {
          // Load conversations if authenticated
          loadConversations();
        }
      } catch (error) {
        console.error("Error checking session:", error);
        setIsAuthenticated(false);
      }
    };
    checkAuth();
  }, []);

  // Auto-scroll effect
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentConversation?.messages, messages]);

  // Focus input when conversation changes
  useEffect(() => {
    if (currentConversation && !isLoading) {
      inputRef.current?.focus();
    }
  }, [currentConversation, isLoading]);

  // Load all conversations
  const loadConversations = async () => {
    try {
      setIsLoading(true);
      // Estandarizar formato del API
      const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/v1/agent/conversations`;
        
      const session = await getSession();
      if (!session?.accessToken) {
        throw new Error("No active session");
      }
      
      const response = await fetch(apiUrl, {
        headers: {
          'Authorization': `Bearer ${session.accessToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error loading conversations: ${response.status}`);
      }
      
      const data = await response.json();
      setConversations(data);
    } catch (error) {
      console.error("Error loading conversations:", error);
      toast.error("Failed to load conversations");
      // For development, create some fake conversations
      if (process.env.NODE_ENV === 'development') {
        const fakeConversations: Conversation[] = [
          {
            id: "fake-1",
            title: "Testing the agent",
            messages: [],
            created_at: new Date().toISOString()
          },
          {
            id: "fake-2",
            title: "Math questions",
            messages: [],
            created_at: new Date().toISOString()
          }
        ];
        setConversations(fakeConversations);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Load a specific conversation
  const loadConversation = async (id: string) => {
    try {
      setIsLoading(true);
      // Estandarizar formato del API
      const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/v1/agent/conversations/${id}`;
        
      const session = await getSession();
      if (!session?.accessToken) {
        throw new Error("No active session");
      }
      
      const response = await fetch(apiUrl, {
        headers: {
          'Authorization': `Bearer ${session.accessToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error loading conversation: ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Loaded conversation data:", data);
      
      // Convert messages to our format
      const formattedMessages = data.messages.map((msg: any) => ({
        id: msg.id,
        // Corregir el mapeo de roles para mostrar correctamente
        role: msg.role === 'assistant' ? 'agent' : 
              ['tool', 'thinking', 'observation', 'user', 'error'].includes(msg.role) ? msg.role : 'agent',
        text: msg.content,
        timestamp: msg.created_at,
        isVisible: msg.role !== 'thinking' || showThinking
      }));
      

      const conversation: Conversation = {
        id: data.id,
        title: data.title,
        messages: formattedMessages,
        created_at: data.created_at,
        updated_at: data.updated_at
      };
      
      console.log("Setting current conversation:", conversation);
      setCurrentConversation(conversation);
      setMessages(formattedMessages);
      setConversationId(data.id);
      
      return conversation;
    } catch (error) {
      console.error("Error loading conversation:", error);
      toast.error("Failed to load conversation");
      
      // For development, create a fake conversation
      if (process.env.NODE_ENV === 'development') {
        const fakeConversation: Conversation = {
          id,
          title: "Fake conversation",
          messages: [
            { id: "1", role: 'user', text: "Hello", timestamp: new Date().toISOString() },
            { id: "2", role: 'agent', text: "Hi there! How can I help you today?", timestamp: new Date().toISOString() }
          ],
          created_at: new Date().toISOString()
        };
        setCurrentConversation(fakeConversation);
        setMessages(fakeConversation.messages);
        setConversationId(id);
        return fakeConversation;
      }
      
      return null;
    } finally {
      setIsLoading(false);
    }
  };


  // Create a new conversation
  const createNewConversation = async () => {
    try {
      setIsLoading(true);
      // Estandarizar formato del API
      const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/v1/agent/conversations`;
        
      const session = await getSession();
      if (!session?.accessToken) {
        throw new Error("No active session");
      }
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.accessToken}`
        },
        body: JSON.stringify({ title: "New conversation" })
      });
      
      if (!response.ok) {
        throw new Error(`Error creating conversation: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Update state
      const newConversation: Conversation = {
        id: data.id,
        title: data.title,
        messages: [],
        created_at: data.created_at
      };
      
      setConversations(prev => [newConversation, ...prev]);
      setCurrentConversation(newConversation);
      setMessages([]);
      setConversationId(data.id);
      
      toast.success("New conversation created");
      return newConversation;
    } catch (error) {
      console.error("Error creating conversation:", error);
      toast.error("Failed to create new conversation");
      
      // For development, create a fake conversation
      if (process.env.NODE_ENV === 'development') {
        const fakeId = `fake-${Date.now()}`;
        const fakeConversation: Conversation = {
          id: fakeId,
          title: "New conversation",
          messages: [],
          created_at: new Date().toISOString()
        };
        setConversations(prev => [fakeConversation, ...prev]);
        setCurrentConversation(fakeConversation);
        setMessages([]);
        setConversationId(fakeId);
        return fakeConversation;
      }
      
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  // Update conversation title
  const updateConversationTitle = async (id: string, title: string) => {
    if (!title.trim()) {
      setEditingConversation(null);
      return;
    }
    
    try {
      setIsLoading(true);
      // Estandarizar formato del API
      const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/v1/agent/conversations/${id}/title`;
        
      const session = await getSession();
      if (!session?.accessToken) {
        console.error("No active session when updating title");
        toast.error("Authentication error - please refresh the page");
        throw new Error("No active session");
      }
      
      console.log(`Updating conversation title for ID: ${id} to "${title}"`);
      
      const response = await fetch(apiUrl, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.accessToken}`
        },
        body: JSON.stringify({ title })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error(`Error updating conversation: ${response.status}`, errorData);
        throw new Error(`Error updating conversation: ${response.status}`);
      }
      
      // Update state
      setConversations(prev => 
        prev.map(conv => 
          conv.id === id ? { ...conv, title } : conv
        )
      );
      
      if (currentConversation?.id === id) {
        setCurrentConversation(prev => 
          prev ? { ...prev, title } : null
        );
      }
      
      toast.success("Title updated");
    } catch (error) {
      console.error("Error updating conversation title:", error);
      toast.error("Failed to update title");
      
      // For development, update state anyway
      if (process.env.NODE_ENV === 'development') {
        console.log("Development mode: Updating title in state despite API error");
        setConversations(prev => 
          prev.map(conv => 
            conv.id === id ? { ...conv, title } : conv
          )
        );
        
        if (currentConversation?.id === id) {
          setCurrentConversation(prev => 
            prev ? { ...prev, title } : null
          );
        }
      }
    } finally {
      setIsLoading(false);
      setEditingConversation(null);
    }
  };

  // Delete conversation
  const deleteConversation = async (id: string) => {
    try {
      setIsLoading(true);
      // Estandarizar formato del API
      const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/v1/agent/conversations/${id}`;
        
      const session = await getSession();
      if (!session?.accessToken) {
        throw new Error("No active session");
      }
      
      const response = await fetch(apiUrl, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.accessToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error deleting conversation: ${response.status}`);
      }
      
      // Update state
      setConversations(prev => prev.filter(conv => conv.id !== id));
      
      if (currentConversation?.id === id) {
        setCurrentConversation(null);
        setMessages([]);
        setConversationId(null);
      }
      
      toast.success("Conversation deleted");
    } catch (error) {
      console.error("Error deleting conversation:", error);
      toast.error("Failed to delete conversation");
      
      // For development, update state anyway
      if (process.env.NODE_ENV === 'development') {
        setConversations(prev => prev.filter(conv => conv.id !== id));
        
        if (currentConversation?.id === id) {
          setCurrentConversation(null);
          setMessages([]);
          setConversationId(null);
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle thinking visualization
  const toggleThinkingVisibility = () => {
    console.log("Toggle thinking visibility. Current state:", showThinking);
    
    // Toggle the visibility state
    const newShowThinking = !showThinking;
    setShowThinking(newShowThinking);
    
    // Apply visibility changes to messages
    if (currentConversation) {
      console.log(`Updating ${currentConversation.messages.length} messages, showing thinking: ${newShowThinking}`);
      
      const updatedMessages = currentConversation.messages.map(msg => {
        // Only modify thinking messages, leave others unchanged
        if (msg.role === 'thinking') {
          return {
            ...msg,
            isVisible: newShowThinking // thinking messages follow the toggle
          };
        }
        return msg;
      });
      
      // Update conversation and message state
      setCurrentConversation({
        ...currentConversation,
        messages: updatedMessages
      });
      
      setMessages(updatedMessages);
      console.log("Messages updated, thinking messages are now:", newShowThinking ? "visible" : "hidden");
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    // Create a new conversation if needed
    if (!currentConversation) {
      const newConv = await createNewConversation();
      if (!newConv) return;
    }

    setIsLoading(true);
    const userQuery = input.trim();
    const userMessageId = `user-${Date.now()}`;
    const newUserMessage: Message = {
      id: userMessageId,
      role: 'user',
      text: userQuery,
      timestamp: new Date().toISOString(),
      isVisible: true
    };
    
    // Add user message and placeholder for agent
    const agentMessageId = `agent-${Date.now()}`;
    const agentPlaceholder: Message = {
      id: agentMessageId,
      role: 'agent',
      text: '...',
      timestamp: new Date().toISOString(),
      isVisible: true
    };
    
    // Update local state immediately
    let updatedMessages: Message[] = [];
    
    if (currentConversation) {
      updatedMessages = [...currentConversation.messages, newUserMessage, agentPlaceholder];
      
      setCurrentConversation({
        ...currentConversation,
        messages: updatedMessages
      });
    } else {
      updatedMessages = [...messages, newUserMessage, agentPlaceholder];
    }
    
    setMessages(updatedMessages);
    setInput(''); // Clear input after adding messages

    let session;
    try {
      // Get Session and Token
      session = await getSession();
      if (!session?.accessToken) {
        setIsAuthenticated(false);
        throw new Error("Authentication token not found or session expired. Please log in again.");
      }
      setIsAuthenticated(true);
      const token = session.accessToken;
      
      // Prepare request
      const requestBody = { 
        query: userQuery, 
        conversation_id: conversationId
      };
      
      // Estandarizar formato del API
      const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/v1/agent/invoke`;

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`, 
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        let errorDetail = 'Request failed';
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const errorData = await response.json();
            errorDetail = errorData.detail || JSON.stringify(errorData);
          } else {
            const errorText = await response.text();
            errorDetail = errorText || `HTTP error! status: ${response.status}`;
          }
        } catch (parseError) {
          errorDetail = `Error processing response (${response.status})`;
        }
        
        if (response.status === 401 || response.status === 403) {
          setIsAuthenticated(false); 
          errorDetail = `Authentication Error: ${errorDetail}. Please try logging in again.`;
        }
        throw new Error(errorDetail);
      }

      if (!response.body) {
        throw new Error("Response body is missing");
      }

      // Process the stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          console.log("Stream chunk received:", chunk);
          
          // Process SSE format - split by lines and extract data
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.substring(6); // Remove 'data: ' prefix
              
              // Check if it's an error message
              try {
                const jsonData = JSON.parse(data);
                if (jsonData.error) {
                  console.error("Error from server:", jsonData.error);
                  accumulatedResponse += `\n\nError: ${jsonData.error}`;
                  continue;
                }
              } catch (e) {
                // Not JSON, treat as text content
                accumulatedResponse += data;
              }
            }
          }

          // Actualizamos los mensajes directamente - solo actualizar el placeholder, no añadir nuevos mensajes
          const latestMessages = updatedMessages.map(msg =>
            msg.id === agentMessageId
              ? { ...msg, text: accumulatedResponse }
              : msg
          );

          console.log("Updating messages with agent response:", accumulatedResponse);
          
          // Actualizar ambos estados para mantener consistencia
          if (currentConversation) {
            setCurrentConversation(prev => ({
              ...prev!,
              messages: latestMessages
            }));
          }
          
          setMessages(latestMessages);
          
          // Force scroll to bottom with each update
          if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
          }
        }
      } catch (error) {
        console.error("Error processing stream:", error);
      }
      
      console.log("Stream complete, final response:", accumulatedResponse);

      // Si la respuesta está vacía, mostrar un mensaje de error
      if (!accumulatedResponse.trim()) {
        const errorMessages = updatedMessages.map(msg =>
          msg.id === agentMessageId
            ? { ...msg, text: "[Agent did not provide a response]" }
            : msg
        );
        
        if (currentConversation) {
          setCurrentConversation(prev => ({
            ...prev!,
            messages: errorMessages
          }));
        }
        
        setMessages(errorMessages);
        setIsLoading(false);
        return;
      }

      // If response came back, extract the conversation_id if available
      // The backend may create a new conversation or use an existing one
      const convMatchResult = /conversation ID: ([0-9a-f-]+)/i.exec(accumulatedResponse);
      if (convMatchResult && convMatchResult[1] && !conversationId) {
        const extractedConvId = convMatchResult[1];
        setConversationId(extractedConvId);
        
        // Refresh conversations list
        loadConversations();
      }

      // Actualizar el estado final con la respuesta completa
      const finalMessages = updatedMessages.map(msg =>
        msg.id === agentMessageId
          ? { ...msg, text: accumulatedResponse }
          : msg
      );

      if (currentConversation) {
        setCurrentConversation(prev => ({
          ...prev!,
          messages: finalMessages
        }));
      }
      
      setMessages(finalMessages);

      // Después de completar el streaming, esperar un momento antes de recargar
      // para dar tiempo a que el backend finalice la persistencia
      if (conversationId) {
        console.log("Waiting for backend to finalize persistence...");
        
        // Esperar antes de recargar
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Cargar la conversación solo una vez
        console.log("Loading conversation with final response");
        try {
          // Realizar una única carga con toda la verificación hecha en el backend
          const conversation = await loadConversation(conversationId);
          
          if (conversation) {
            // Replace local state with server state to ensure consistency
            setCurrentConversation(conversation);
            setMessages(conversation.messages);
            console.log("✅ Updated chat with database state");
            
            // Force scroll to bottom with each update
            if (messagesEndRef.current) {
              messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
            }
          } else {
            console.warn("⚠️ Failed to load conversation from server, keeping client-side state");
          }
        } catch (error) {
          console.error("Error loading conversation with final response:", error);
          // Keep the client-side state if server load fails
        }
      }

    } catch (error) {
      console.error("Error invoking agent:", error);
      const errorText = error instanceof Error ? error.message : 'Unknown error';
      
      // Update the placeholder message with error info
      if (currentConversation) {
        const updatedMessages = currentConversation.messages.map(msg =>
          msg.id === agentMessageId
            ? { ...msg, role: 'error', text: `Error: ${errorText}` }
            : msg
        );
        
        setCurrentConversation({
          ...currentConversation,
          messages: updatedMessages as Message[]
        });
      } else {
        setMessages(prevMessages =>
          prevMessages.map(msg =>
            msg.id === agentMessageId
              ? { ...msg, role: 'error', text: `Error: ${errorText}` }
              : msg
          )
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Add effect to load MCP servers
  useEffect(() => {
    const fetchMcpServers = async () => {
      try {
        setLoadingMcpServers(true);
        const session = await getSession();
        
        if (!session?.accessToken) {
          // Don't show error, just don't load
          return;
        }
        
        // Usar el formato estándar de API
        const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/v1/agent/mcp/servers`;
        
        const response = await fetch(apiUrl, {
          headers: {
            'Authorization': `Bearer ${session.accessToken}`
          }
        });
        
        if (!response.ok) {
          throw new Error(`Error loading MCP servers: ${response.status}`);
        }
        
        const data: McpServersResponse = await response.json();
        
        if (data.status === 'success') {
          setMcpServers(data.servers);
        } else {
          setMcpServersError('Failed to load MCP servers');
        }
      } catch (err) {
        console.error('Error fetching MCP servers:', err);
        setMcpServersError('Error loading MCP servers');
      } finally {
        setLoadingMcpServers(false);
      }
    };

    if (isAuthenticated) {
      fetchMcpServers();
    }
  }, [isAuthenticated]);

  // MCP Servers Panel component embedded
  const McpServersPanel = () => (
    <Popover open={mcpPopoverOpen} onOpenChange={setMcpPopoverOpen}>
      <PopoverTrigger asChild>
        <Button 
          variant="outline" 
          className="flex items-center gap-2"
          onClick={() => setMcpPopoverOpen(!mcpPopoverOpen)}
        >
          <Server className="h-4 w-4" />
          <span>MCP Servers</span>
          <Badge variant="outline" className="ml-2">
            {Object.keys(mcpServers).length}
          </Badge>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Available MCP Servers</CardTitle>
            <CardDescription>
              Tools and commands you can use in your queries
            </CardDescription>
          </CardHeader>
          <CardContent className="max-h-[60vh] overflow-auto">
            {loadingMcpServers ? (
              <div className="flex justify-center py-4">
                <span className="animate-spin mr-2">⏳</span> Loading...
              </div>
            ) : mcpServersError ? (
              <div className="text-red-500 py-4">{mcpServersError}</div>
            ) : Object.keys(mcpServers).length === 0 ? (
              <div className="text-muted-foreground py-4">No MCP servers available</div>
            ) : (
              <div className="space-y-2">
                {Object.entries(mcpServers).map(([name, server]) => (
                  <Collapsible key={name} className="border rounded-md p-2">
                    <CollapsibleTrigger className="flex items-center justify-between w-full">
                      <div className="flex items-center gap-2">
                        <Server className="h-4 w-4" />
                        <span className="font-medium">{name}</span>
                      </div>
                      <ChevronDown className="h-4 w-4" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="pt-2">
                      <p className="text-sm text-muted-foreground mb-2">{server.description}</p>
                      {server.commands.length > 0 ? (
                        <div className="space-y-1">
                          <h4 className="text-xs font-semibold">Available Commands:</h4>
                          <ul className="space-y-1">
                            {server.commands.map(cmd => (
                              <li key={cmd} className="text-xs flex items-center">
                                <Terminal className="h-3 w-3 mr-1" />
                                <code className="bg-muted p-1 rounded">{cmd}</code>
                              </li>
                            ))}
                          </ul>
                          <div className="mt-2 text-xs">
                            <h4 className="font-semibold">Example:</h4>
                            <code className="bg-muted p-1 rounded block mt-1">
                              server={name} {server.commands[0]} param="value"
                            </code>
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground">No commands available</p>
                      )}
                    </CollapsibleContent>
                  </Collapsible>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </PopoverContent>
    </Popover>
  );

  // Show loading indicator while checking auth state
  if (isAuthenticated === null) {
    return <p className="text-center text-muted-foreground p-4">Initializing...</p>;
  }

  // Render chat interface
  return (
    <div className="flex h-[calc(100vh-5rem)]">
      {/* Sidebar with conversations */}
      <div className="w-72 border-r p-4 flex flex-col bg-card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Conversations</h2>
          <div className="flex space-x-1">
            <Button 
              variant="ghost"
              size="sm"
              onClick={() => loadConversations()}
              title="Refresh list"
              className="h-8 w-8 p-0"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button 
              size="sm" 
              onClick={createNewConversation}
              className="h-8"
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              New
            </Button>
          </div>
        </div>
        
        <div className="overflow-y-auto flex-grow">
          {conversations.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm italic">
              No conversations yet
            </div>
          ) : (
            conversations.map((conversation) => (
              <div 
                key={conversation.id}
                className={`p-2 rounded-md mb-1 hover:bg-accent/50 cursor-pointer group ${
                  currentConversation?.id === conversation.id ? 'bg-accent' : ''
                }`}
                onClick={() => loadConversation(conversation.id)}
              >
                {editingConversation === conversation.id ? (
                  <div className="flex items-center w-full">
                    <Input
                      className="h-8 text-sm mr-1 w-full"
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          updateConversationTitle(conversation.id, newTitle);
                        } else if (e.key === 'Escape') {
                          setEditingConversation(null);
                        }
                      }}
                      autoFocus
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 text-blue-600 dark:text-blue-400"
                      onClick={(e) => {
                        e.stopPropagation();
                        updateConversationTitle(conversation.id, newTitle);
                      }}
                    >
                      <CheckIcon className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 text-gray-500 dark:text-gray-400"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingConversation(null);
                      }}
                    >
                      <Cross1Icon className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex flex-col">
                    <div className="flex justify-between items-start">
                      <div className="truncate text-sm font-medium">
                        {conversation.title || 'New conversation'}
                      </div>
                      <div className="flex opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={(e) => {
                            e.stopPropagation();
                            setNewTitle(conversation.title);
                            setEditingConversation(conversation.id);
                          }}
                        >
                          <Pencil1Icon className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm('Are you sure you want to delete this conversation?')) {
                              deleteConversation(conversation.id);
                            }
                          }}
                        >
                          <TrashIcon className="h-3 w-3 text-destructive" />
                        </Button>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {conversation.updated_at 
                        ? formatDate(conversation.updated_at) 
                        : formatDate(conversation.created_at)}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
        
        <div className="mt-4 pt-4 border-t">
          <div className="flex items-center justify-between mb-2">
            <Label htmlFor="thinkingToggle" className="text-sm">
              Show Reasoning
            </Label>
            <Switch 
              id="thinkingToggle" 
              checked={showThinking} 
              onCheckedChange={toggleThinkingVisibility}
            />
          </div>
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {!isAuthenticated ? (
          <Alert variant="destructive" className="m-4">
            <TerminalIcon className="h-4 w-4" />
            <AlertTitle>Authentication Required</AlertTitle>
            <AlertDescription>
              You must be logged in to use the agent. Please sign in.
            </AlertDescription>
          </Alert>
        ) : !currentConversation ? (
          <div className="flex-1 flex flex-col justify-center items-center p-8 text-center">
            <div className="mb-4 rounded-full bg-primary/10 p-3">
              <MessageSquareIcon className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-1">Start a new conversation</h3>
            <p className="text-muted-foreground mb-6 max-w-md">
              Write a message to start chatting with the AI Agent
            </p>
            <Button onClick={createNewConversation} className="mt-2">
              New conversation
            </Button>
          </div>
        ) : (
          <>
            {/* Chat header */}
            <div className="border-b p-4 flex justify-between items-center bg-card">
              <h2 className="text-lg font-semibold">
                {currentConversation.title || 'New conversation'}
              </h2>
              <div className="flex items-center gap-4">
                {/* Add MCP Server Panel here */}
                <McpServersPanel />
                
                {isLoading && (
                  <div className="flex items-center mr-4 text-blue-600">
                    <Loader className="animate-spin h-4 w-4 mr-2" />
                    <span className="text-sm">Processing...</span>
                  </div>
                )}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm">
                      <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                      </svg>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem 
                      onClick={() => {
                        setNewTitle(currentConversation.title);
                        setEditingConversation(currentConversation.id);
                      }}
                    >
                      <Pencil1Icon className="mr-2 h-4 w-4" />
                      Rename
                    </DropdownMenuItem>
                    <DropdownMenuItem 
                      onClick={toggleThinkingVisibility}
                    >
                      {showThinking ? (
                        <>
                          <EyeOff className="mr-2 h-4 w-4" />
                          Hide Reasoning
                        </>
                      ) : (
                        <>
                          <Eye className="mr-2 h-4 w-4" />
                          Show Reasoning
                        </>
                      )}
                    </DropdownMenuItem>
                    <DropdownMenuItem 
                      onClick={() => {
                        if (window.confirm('Are you sure you want to delete this conversation?')) {
                          deleteConversation(currentConversation.id);
                        }
                      }}
                      className="text-destructive"
                    >
                      <TrashIcon className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
            
            {/* Chat messages */}
            <div className="flex-grow overflow-y-auto p-4 bg-background">
              <div className="space-y-4 max-w-3xl mx-auto">
                {currentConversation.messages.length === 0 ? (
                  <p className="text-center text-muted-foreground">
                    Start the conversation by typing below.
                  </p>
                ) : (
                  currentConversation.messages
                    .filter(msg => msg.isVisible !== false)
                    .map((message) => {
                      // Define message display based on role
                      let icon = null;
                      let bgColorClass = '';
                      let borderClass = '';
                      let textColorClass = '';
                      
                      switch (message.role) {
                        case 'user':
                          icon = <UserCircle className="h-6 w-6 text-primary" />;
                          bgColorClass = 'bg-primary/10';
                          textColorClass = 'text-foreground text-base';
                          break;
                        case 'agent':
                        case 'assistant':
                          icon = <BotIcon className="h-6 w-6 text-blue-500" />;
                          bgColorClass = 'bg-card';
                          borderClass = 'border';
                          textColorClass = 'text-foreground text-base';
                          break;
                        case 'thinking':
                          icon = <Code className="h-6 w-6 text-orange-500" />;
                          bgColorClass = 'bg-orange-50 dark:bg-orange-950/30';
                          borderClass = 'border-orange-200 dark:border-orange-800 border';
                          textColorClass = 'text-orange-800 dark:text-orange-200 text-base';
                          break;
                        case 'tool':
                          icon = <Code className="h-6 w-6 text-green-500" />;
                          bgColorClass = 'bg-green-50 dark:bg-green-950/30';
                          borderClass = 'border-green-200 dark:border-green-800 border';
                          textColorClass = 'text-green-800 dark:text-green-200 text-base';
                          break;
                        case 'observation':
                          icon = <Code className="h-6 w-6 text-blue-500" />;
                          bgColorClass = 'bg-blue-50 dark:bg-blue-950/30';
                          borderClass = 'border-blue-200 dark:border-blue-800 border';
                          textColorClass = 'text-blue-800 dark:text-blue-200 text-base';
                          break;
                        case 'error':
                          icon = <Terminal className="h-6 w-6 text-destructive" />;
                          bgColorClass = 'bg-destructive/10';
                          textColorClass = 'text-destructive text-base';
                          break;
                        default:
                          icon = <MessageSquareIcon className="h-6 w-6 text-muted-foreground" />;
                          bgColorClass = 'bg-card';
                          borderClass = 'border';
                          textColorClass = 'text-foreground text-base';
                      }
                      
                      return (
                        <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                          {message.role !== 'user' && (
                            <div className="mr-2 flex-shrink-0 mt-1">
                              {icon}
                            </div>
                          )}
                          <div className={`${bgColorClass} ${borderClass} ${textColorClass} p-4 rounded-lg max-w-[80%] shadow-sm whitespace-pre-wrap`}>
                            {message.text}
                          </div>
                          {message.role === 'user' && (
                            <div className="ml-2 flex-shrink-0 mt-1">
                              {icon}
                            </div>
                          )}
                        </div>
                      );
                    })
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>
            
            {/* Input area */}
            <div className="p-4 border-t bg-card">
              <form onSubmit={handleSubmit} className="flex max-w-3xl mx-auto">
                <Input
                  ref={inputRef}
                  type="text"
                  placeholder="Type your message to the agent..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={isLoading}
                  className="flex-1 min-w-0 text-base"
                />
                <Button 
                  type="submit" 
                  className="ml-2 px-4 flex items-center"
                  disabled={isLoading || !input.trim()}
                >
                  {isLoading ? (
                    <Loader className="h-5 w-5 animate-spin" />
                  ) : (
                    <ArrowRight className="h-5 w-5" />
                  )}
                </Button>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  );
} 