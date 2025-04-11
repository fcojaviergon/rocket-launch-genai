'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { getSession } from 'next-auth/react';
import apiClient from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PlusIcon, Cross1Icon, CheckIcon, Pencil1Icon, TrashIcon } from '@radix-ui/react-icons';
import { RefreshCw, Loader, UserCircle, ArrowRight, Bot as BotIcon } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { MessageSquareIcon } from 'lucide-react';
import { McpServersPanel } from '@/components/ui/McpServersPanel';
import { ChatMessage } from '@/components/ChatMessage';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system' | 'tool' | 'thinking';
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
}

export default function ChatPage() {
  const router = useRouter();
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [editingConversation, setEditingConversation] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamedContent, setStreamedContent] = useState<string>("");
  const [useStreaming, setUseStreaming] = useState<boolean>(true);
  const inputRef = useRef<HTMLInputElement>(null);
  const [showThinking, setShowThinking] = useState<boolean>(false);
  const [showToolCalls, setShowToolCalls] = useState<boolean>(true);

  // Load token when starting with support for refresh token
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const session = await getSession();
        
        if (session?.accessToken) {
          // The token exists, try to load conversations
          loadConversations();
        } else {
          console.error('Could not get a valid token');
          setError('No active session');
          router.push('/login');
        }
      } catch (error) {
        console.error('Error initializing authentication:', error);
        setError('Authentication error');
        router.push('/login');
      }
    };
    
    initializeAuth();
  }, [router]);

  // Scroll to the last message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation?.messages]);

  // Verify the token before making API calls
  const verifyToken = async (): Promise<boolean> => {
    try {
      const session = await getSession();
      if (!session?.accessToken) {
        console.error('No token in the session');
        setError('No active session. Please login again.');
        return false;
      }
      
      // Validate the token in the backend
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/v1/auth/me`, {
        headers: {
          'Authorization': `Bearer ${session.accessToken}`
        }
      });
      
      if (!response.ok) {
        console.error('Invalid or expired token:', response.status);
        setError('Your session has expired. Please renew your session.');
        return false;
      }
      
      return true;
    } catch (error) {
      console.error('Error verifying token:', error);
      setError('Error validating the session. Please login again.');
      return false;
    }
  };

  // Load conversations
  const loadConversations = async (token?: string) => {
    // Verify token before making the call
    if (!await verifyToken()) {
      return; // No continue if the token is not valid
    }
    
    try {
      setIsLoading(true);
      
      let data;
      
      try {
        // Try with httpClient first
        if (apiClient && apiClient.get) {
          data = await apiClient.get<Conversation[]>('/api/v1/chat/conversations');
        } else {
          // Fallback to apiClient if httpClient is not available
          data = await apiClient.get<Conversation[]>('/api/v1/chat/conversations');
        }
      } catch (apiError: any) {
        console.error('Error con el cliente HTTP:', apiError);
        
        // Verify if it is an authentication error
        if (apiError.isAuthError || apiError.response?.status === 401) {
          setError('Your session has expired. Please reload the page to login again.');
          setIsLoading(false);
          // No redirect automatically
          return;
        }
        
        // For other errors, try with apiClient directly
        data = await apiClient.get<Conversation[]>('/api/v1/chat/conversations');
      }
      
      setConversations(data);
    } catch (error: any) {
      console.error('Error:', error);
      
      // Verify if it is an authentication error
      if (error.isAuthError || error.response?.status === 401) {
        setError('Your session has expired. Please reload the page to login again.');
        // No redirect automatically
      } else {
        setError('Could not load conversations: ' + error.message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Load a specific conversation
  const loadConversation = async (conversationId: string) => {
    // Verify token before making the call
    if (!await verifyToken()) {
      return null; // No continue if the token is not valid
    }
    
    try {
      setIsLoading(true);
      
      // Usar endpoint para mensajes detallados con opciones para thinking
      const endpoint = showThinking ? 
        `/api/v1/agent/conversations/${conversationId}/detailed-messages?include_thinking=true&include_tool_calls=${showToolCalls}` :
        `/api/v1/agent/conversations/${conversationId}/messages`;
      
      const messagesResponse = await apiClient.get<Message[]>(endpoint);
      
      // Obtener los detalles de la conversación
      const conversationResponse = await apiClient.get<Conversation>(`/api/v1/chat/conversations/${conversationId}`);
      
      // Combinamos la respuesta
      const conversation = {
        ...conversationResponse,
        messages: messagesResponse
      };
      
      // Asegurar que los mensajes tengan IDs únicos
      if (conversation.messages) {
        conversation.messages = conversation.messages.map(msg => ({
          ...msg,
          id: msg.id || `msg-${Math.random().toString(36).substring(2, 11)}`
        }));
      }
      
      setCurrentConversation(conversation);
      return conversation;
    } catch (error: any) {
      console.error('Error:', error);
      
      // Verificar si es un error de autenticación
      if (error.isAuthError || error.response?.status === 401) {
        setError('Your session has expired. Please reload the page to login again.');
      } else {
        setError(`Could not load conversation: ${error.message}`);
      }
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  // Update conversation title
  const handleUpdateTitle = async (conversationId: string) => {
    if (!newTitle.trim()) {
      setEditingConversation(null);
      return;
    }
    
    try {
      setIsLoading(true);
      
      let updatedConversation;
      
      try {
        if (apiClient && apiClient.put) {
          updatedConversation = await apiClient.put<Conversation>(
            `/api/v1/chat/conversations/${conversationId}`,
            { title: newTitle }
          );
        } else {
          updatedConversation = await apiClient.put<Conversation>(
            `/api/v1/chat/conversations/${conversationId}`,
            { title: newTitle }
          );
        }
      } catch (apiError) {
        console.error('Error con el cliente HTTP, usando API client directamente:', apiError);
        updatedConversation = await apiClient.put<Conversation>(
          `/api/v1/chat/conversations/${conversationId}`,
          { title: newTitle }
        );
      }
      
      // Update the list of conversations
      setConversations(prev => 
        prev.map(conv => 
          conv.id === conversationId 
            ? { ...conv, title: updatedConversation.title } 
            : conv
        )
      );
      
      // Update the current conversation if it is the same
      if (currentConversation && currentConversation.id === conversationId) {
        setCurrentConversation({
          ...currentConversation,
          title: updatedConversation.title
        });
      }
      
      toast.success('Title updated');
    } catch (error: any) {
      console.error('Error:', error);
      toast.error('Could not update the title: ' + error.message);
    } finally {
      setIsLoading(false);
      setEditingConversation(null);
    }
  };

  // Delete conversation
  const handleDeleteConversation = async (conversationId: string) => {
    try {
      setIsLoading(true);
      
      try {
        if (apiClient && apiClient.delete) {
          await apiClient.delete(`/api/v1/chat/conversations/${conversationId}`);
        } else {
          await apiClient.delete(`/api/v1/chat/conversations/${conversationId}`);
        }
      } catch (apiError) {
        console.error('Error con el cliente HTTP, usando API client directamente:', apiError);
        await apiClient.delete(`/api/v1/chat/conversations/${conversationId}`);
      }
      
      // Delete from the list of conversations
      setConversations(prev => prev.filter(conv => conv.id !== conversationId));
      
      // If it is the current conversation, reset it
      if (currentConversation && currentConversation.id === conversationId) {
        setCurrentConversation(null);
      }
      
      toast.success('Conversation deleted');
    } catch (error: any) {
      console.error('Error:', error);
      toast.error('Could not delete the conversation: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const resetError = () => setError('');

  const createNewConversation = async (initialMessage: string = '') => {
    try {
      const title = initialMessage.slice(0, 30) + (initialMessage.length > 30 ? '...' : '') || 'New conversation';
      
      let response;
      try {
        // Try with httpClient first
        if (apiClient && apiClient.post) {
          response = await apiClient.post('/api/v1/chat/conversations', { title });
        } else {
          // Fallback to apiClient
          response = await apiClient.post('/api/v1/chat/conversations', { title });
        }
      } catch (apiError) {
        console.error('Error con el cliente HTTP:', apiError);
        // Try directly with fetch
        const session = await getSession();
        if (!session?.accessToken) {
          throw new Error('No active session');
        }
        
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        const fetchResponse = await fetch(`${backendUrl}/api/v1/chat/conversations`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session.accessToken}`
          },
          body: JSON.stringify({ title })
        });
        
        if (!fetchResponse.ok) {
          throw new Error(`Error: ${fetchResponse.status} ${fetchResponse.statusText}`);
        }
        
        response = await fetchResponse.json();
      }
      
      if (response && response.id) {
        // Load the new conversation
        await loadConversation(response.id);
        // Update the list of conversations
        await loadConversations();
        return response;
      } else {
        throw new Error('Invalid response when creating conversation');
      }
    } catch (error) {
      console.error('Error creating conversation:', error);
      setError('Error creating conversation');
      return null;
    }
  };

  // Create new conversation
  const handleNewConversation = async () => {
    setIsLoading(true);
    try {
      const newConv = await createNewConversation();
      if (newConv) {
        // The conversation has been loaded in createNewConversation
        toast.success('Conversation created');
      }
    } catch (error) {
      console.error('Error creating new conversation:', error);
      setError('Could not create a new conversation');
    } finally {
      setIsLoading(false);
    }
  };

  const streamMessage = async (content: string) => {
    if (!content.trim()) return;
    
    // Verify token before making the call
    if (!await verifyToken()) {
      return; // No continue if the token is not valid
    }
    
    try {
      console.log("Iniciando streaming para:", content.slice(0, 20) + "...");
      setIsStreaming(true);
      setIsLoading(true);
      setError('');
      
      // Clean the previous streaming content
      setStreamedContent("");

      // If there is no current conversation, create one
      if (!currentConversation) {
        console.log("Creating a new conversation for the message");
        const newConv = await createNewConversation(content.slice(0, 30));
        if (!newConv) {
          throw new Error('Could not create a new conversation');
        }
        // Wait a moment to update correctly
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      // Create a unique ID for this user message to avoid duplicates
      const userMessageId = `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      // Add the user message to the UI immediately
      const tempMessage: Message = {
        id: userMessageId,
        content: content,
        role: 'user',
        timestamp: new Date().toISOString()
      };
      
      // Add assistant placeholder *before* starting the stream
      const placeholderMessage: Message = {
        id: 'streaming-placeholder', // Use a fixed ID for easy targeting
        role: 'assistant',
        content: '', // Start empty
        timestamp: new Date().toISOString()
      };
      
      // Verify if the message already exists to avoid duplicates
      let messageExists = false;
      
      setCurrentConversation((prevConv) => {
        if (!prevConv) return null;
        
        // Verify if the user message already exists to avoid duplicates
        messageExists = prevConv.messages.some(m => 
          m.role === 'user' && m.content === content && Date.now() - new Date(m.timestamp).getTime() < 5000
        );
        
        if (messageExists) {
          console.log("Duplicate user message detected, skipping addition and stream");
          return prevConv; 
        }
        
        // Add BOTH user message and placeholder
        return {
          ...prevConv,
          messages: [...prevConv.messages, tempMessage, placeholderMessage]
        };
      });
      
      // If the message already exists, do not continue with the streaming
      if (messageExists) {
        console.log("Duplicate message detected, canceling stream");
        setIsStreaming(false);
        setIsLoading(false);
        return;
      }
      
      // Reset any previous error
      resetError();
      
      // Get the session token and ensure it is valid
      const session = await getSession();
      if (!session?.accessToken) {
        throw new Error('No active session');
      }
      
      console.log("Sending stream request");
      
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content,
          conversation_id: currentConversation?.id,
          model: "gpt-3.5-turbo",
          temperature: 0.7,
          accessToken: session.accessToken
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error(`Error status ${response.status}: ${response.statusText}`, errorData);
        throw new Error(errorData.detail || `Error sending message: ${response.status}`);
      }

      // Process stream data
      const processStream = async () => {
        // Add null check for response.body
        if (!response.body) {
            console.error('Response body is null.');
            setError('Failed to get response stream.');
            setIsStreaming(false);
            // Remove placeholder on error
            setCurrentConversation(prev => {
                if (!prev) return null;
                const updatedMessages = prev.messages.filter(msg => msg.id !== 'streaming-placeholder');
                return { ...prev, messages: updatedMessages };
            });
            return;
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = ""; // Buffer for incomplete lines/JSON
        // Explicitly type receivedConversationId
        let receivedConversationId: string | null = null;
        const startTime = Date.now();

        console.log('Reading stream...');

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log('Stream finished reading');
                    break;
                }

                // Decode and add to buffer
                buffer += decoder.decode(value, { stream: true });

                // Process complete lines (JSON objects) in the buffer
                let newlineIndex;
                while ((newlineIndex = buffer.indexOf('\n')) >= 0) {
                    const line = buffer.substring(0, newlineIndex).trim();
                    buffer = buffer.substring(newlineIndex + 1);

                    if (line) {
                        try {
                            const chunkData = JSON.parse(line);
                            
                            // Update last message content IN PLACE using functional update
                            if (chunkData.content) {
                                setCurrentConversation(prev => {
                                    if (!prev || prev.messages.length === 0) return prev;
                                    const lastMessageIndex = prev.messages.length - 1;
                                    // Ensure the last message is the one we are streaming into (check role or id)
                                    if (prev.messages[lastMessageIndex].role === 'assistant' && prev.messages[lastMessageIndex].id === 'streaming-placeholder') {
                                        const updatedMessages = [...prev.messages];
                                        updatedMessages[lastMessageIndex] = {
                                            ...updatedMessages[lastMessageIndex],
                                            content: updatedMessages[lastMessageIndex].content + chunkData.content
                                        };
                                        return { ...prev, messages: updatedMessages };
                                    }
                                    return prev; // Return previous state if last message isn't the target
                                });
                            }
                            
                            // Handle Conversation ID (same as before)
                            if (chunkData.conversation_id && !receivedConversationId) {
                                receivedConversationId = chunkData.conversation_id;
                                console.log(`Received conversation ID: ${receivedConversationId}`);
                                // Explicitly check prev before updating ID
                                setCurrentConversation(prev => {
                                    if (!prev) return null; // Should not happen if ID is received, but safeguard
                                    const newId = receivedConversationId ?? prev.id;
                                    // Check if ID actually changed before creating new object
                                    if (newId !== prev.id) {
                                        return { ...prev, id: newId }; // Only update ID if it changed
                                    }
                                    return prev; // Otherwise, no change needed here (messages updated separately)
                                });
                            }
                        } catch (parseError) {
                            console.error('Error parsing stream chunk JSON:', parseError, 'Chunk:', line);
                        }
                    }
                }
            }

             // Process any remaining buffer content (optional, but good practice)
            if (buffer.trim()) {
                 console.warn("Stream ended with partial data in buffer:", buffer);
                 try {
                    const chunkData = JSON.parse(buffer.trim());
                    // Update last message content IN PLACE
                    if (chunkData.content) {
                         setCurrentConversation(prev => {
                            // Same update logic as inside the loop
                            if (!prev || prev.messages.length === 0) return prev;
                            const lastMessageIndex = prev.messages.length - 1;
                            if (prev.messages[lastMessageIndex].role === 'assistant' && prev.messages[lastMessageIndex].id === 'streaming-placeholder') {
                                const updatedMessages = [...prev.messages];
                                updatedMessages[lastMessageIndex] = {
                                    ...updatedMessages[lastMessageIndex],
                                    content: updatedMessages[lastMessageIndex].content + chunkData.content
                                };
                                return { ...prev, messages: updatedMessages };
                            }
                            return prev;
                        });
                    }
                     if (chunkData.conversation_id) {
                         const finalReceivedId = chunkData.conversation_id;
                         if (finalReceivedId && (!currentConversation?.id || currentConversation.id === 'temp-new')) { 
                             setCurrentConversation(prev => {
                                 if (!prev) {
                                     return { id: finalReceivedId, title: "New Chat", messages: [], created_at: "", updated_at: "" };
                                 }
                                 return { ...prev, id: finalReceivedId };
                             });
                         }
                     }
                 } catch (e) {
                     console.error("Error parsing final buffer content:", e);
                 }
            }

        } catch (error) {
            console.error('Error reading stream:', error);
            setError('Error processing the response.');
            // Remove placeholder on error
            setCurrentConversation(prev => {
                if (!prev) return null;
                const updatedMessages = prev.messages.filter(msg => msg.id !== 'streaming-placeholder');
                return { ...prev, messages: updatedMessages };
            });
        } finally {
            const duration = Date.now() - startTime;
            console.log(`Stream completed after ${duration} ms`);
            setIsStreaming(false);
            setIsLoading(false);

            // REMOVED block that added accumulatedContent separately

            console.log('Finalizing stream processing');
            // Ensure the conversation ID is set if this was a new chat (Keep this part)
             if (receivedConversationId && (!currentConversation?.id || currentConversation.id === 'temp-new')) { 
                  console.log('Setting final conversation ID:', receivedConversationId);
                 setCurrentConversation(prev => {
                     if (!prev) return null;
                     // Create a new messages array for the final state
                     const finalMessages = [...prev.messages]; 
                     const lastMessageIndex = finalMessages.length - 1;
                     if (lastMessageIndex >= 0 && finalMessages[lastMessageIndex].id === 'streaming-placeholder') {
                         const lastMessage = finalMessages[lastMessageIndex];
                         if (!lastMessage.content || lastMessage.content.trim() === "") {
                             finalMessages.pop(); 
                             console.warn("Removing empty streaming placeholder message.");
                         } else {
                             // Give placeholder a permanent ID
                             finalMessages[lastMessageIndex] = { ...lastMessage, id: `assistant-${Date.now()}` };
                         }
                     }
                      // Return the final state object
                     return { ...prev, messages: finalMessages }; 
                 });
             } else if (!receivedConversationId) {
                 console.warn('No conversation ID received in the stream');
             }
             
             // Update placeholder message ID or remove if empty after stream ends
             setCurrentConversation(prev => {
                 if (!prev) return null;
                 const messages = prev.messages;
                 if (messages.length === 0) return prev;
                 
                 const lastMessageIndex = messages.length - 1;
                 const lastMessage = messages[lastMessageIndex];

                 // Check if the last message is the placeholder we were streaming into
                 if (lastMessage && lastMessage.id === 'streaming-placeholder') {
                     const updatedMessages = [...messages];
                     // If placeholder ended up empty, remove it
                     if (!lastMessage.content || lastMessage.content.trim() === "") {
                         updatedMessages.pop(); 
                         console.warn("Removing empty streaming placeholder message.");
                     } else {
                         // Otherwise, give it a permanent ID
                         updatedMessages[lastMessageIndex] = { ...lastMessage, id: `assistant-${Date.now()}` };
                     }
                     // Update state: Ensure the updated state conforms to Conversation | null
                     setCurrentConversation(prev => prev ? { ...prev, id: prev.id, messages: updatedMessages } : null);
                 }
                 return prev; // No change if last message wasn't the placeholder
             });
        }
      };

      processStream();
    } catch (error) {
      console.error('Error processing the message', error);
      setError('Error processing the message');
      setIsStreaming(false);
      setIsLoading(false);
      setStreamedContent("");
    }
  };

  const submitMessage = async () => {
    if (!message.trim()) return;
    
    try {
      setIsLoading(true);
      setError('');
      
      // Guardar el mensaje para restaurarlo en caso de error
      const currentMessage = message;
      
      // If there is no conversation, create a new one with this message as title
      if (!currentConversation) {
        const newConv = await createNewConversation(currentMessage);
        if (!newConv) {
          throw new Error("Error creating a new conversation");
        }
      }

      // Create a unique ID for this message
      const userMessageId = `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      // Add the user message to the UI immediately
      const tempUserMessage: Message = {
        id: userMessageId,
        content: currentMessage,
        role: 'user',
        timestamp: new Date().toISOString()
      };
      
      if (currentConversation) {
        // Verify if the message already exists to avoid duplicates
        const messageExists = currentConversation.messages.some(m => 
          m.role === 'user' && m.content === currentMessage && Date.now() - new Date(m.timestamp).getTime() < 5000
        );
        
        if (!messageExists) {
          // Update the UI immediately with the user message
          setCurrentConversation({
            ...currentConversation,
            messages: [...currentConversation.messages, tempUserMessage]
          });
        }
      }
      
      // Send message to the backend
      let data: any = null;
      try {
        // Verify token before making the call
        const isTokenValid = await verifyToken();
        if (!isTokenValid) {
          throw new Error("Invalid token or session expired");
        }
        
        // Get session to access the token
        const session = await getSession();
        if (!session?.accessToken) {
          throw new Error("No access token available");
        }
        
        // Use fetch directly for greater control
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        const response = await fetch(`${backendUrl}/api/v1/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session.accessToken}`
          },
          body: JSON.stringify({
            content: currentMessage,
            conversation_id: currentConversation?.id
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          console.error(`Error status ${response.status}: ${response.statusText}`, errorData);
          throw new Error(errorData.detail || `Error sending message: ${response.status}`);
        }
        
        data = await response.json();
      } catch (error: any) {
        console.error('Error al enviar mensaje:', error);
        setError(error.message || 'Error sending message');
        // Restaurar el mensaje en caso de error
        setMessage(currentMessage);
        return;
      }
      
      // Procesar la respuesta del backend
      if (data?.conversation_id) {
        if (!currentConversation || currentConversation.id !== data.conversation_id) {
          // If a new conversation was created or the ID changed, load the complete conversation
          await loadConversation(data.conversation_id);
          await loadConversations();
        } else if (data.message) {
          // If it is the same conversation, update only the messages
          const assistantMessage: Message = {
            id: data.message.id || Date.now().toString() + '_assistant',
            content: data.message.content,
            role: 'assistant',
            timestamp: data.message.timestamp || new Date().toISOString()
          };
          
          // Update the current conversation with the assistant message
          setCurrentConversation(prevConv => {
            if (!prevConv) return null;
            return {
              ...prevConv,
              messages: [...prevConv.messages, assistantMessage]
            };
          });
        }
      }
    } catch (error: any) {
      console.error('Error:', error);
      setError(error.message || 'Error sending message');
      // Do not restore the message here, it is handled in the try block
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!message.trim()) return;
    
    const messageCopy = message; // Save a copy of the message
    setMessage(''); // Clean the input immediately for a better user experience
    
    // Use streaming or normal response depending on the configuration
    try {
      if (useStreaming) {
        await streamMessage(messageCopy);
      } else {
        await submitMessage();
      }
    } catch (error) {
      console.error("Error sending message:", error);
      // Do not restore the message because it would confuse the user
    }
  };

  return (
    <div className="flex h-screen flex-col">
      <div className="border-b px-4 py-2 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <MessageSquareIcon className="h-5 w-5" />
          <h1 className="text-lg font-semibold">Chat</h1>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center space-x-2">
            <Switch 
              id="show-thinking" 
              checked={showThinking}
              onCheckedChange={value => {
                setShowThinking(value);
                if (currentConversation) {
                  loadConversation(currentConversation.id);
                }
              }}
            />
            <Label htmlFor="show-thinking">Show thinking process</Label>
          </div>
          
          <div className="flex items-center space-x-2">
            <Switch 
              id="show-tools" 
              checked={showToolCalls}
              onCheckedChange={value => {
                setShowToolCalls(value);
                if (currentConversation) {
                  loadConversation(currentConversation.id);
                }
              }}
            />
            <Label htmlFor="show-tools">Show tool calls</Label>
          </div>
          
          <McpServersPanel />
        </div>
      </div>
      
      <div className="flex flex-1 overflow-hidden">
        <div className="w-64 border-r flex flex-col overflow-hidden">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Conversations</h2>
            <div className="flex space-x-1">
              <Button 
                variant="ghost"
                size="sm"
                onClick={() => loadConversations()}
                title="Refresh list"
                className="h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button 
                size="sm" 
                onClick={handleNewConversation}
                className="btn-primary h-8"
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                New
              </Button>
            </div>
          </div>
          
          <div className="overflow-y-auto flex-grow">
            {conversations.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm italic">
                No conversations yet
              </div>
            ) : (
              conversations.map((conversation: Conversation) => (
                <div 
                  key={conversation.id}
                  className={`chat-conversation-item ${currentConversation?.id === conversation.id ? 'active' : ''}`}
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
                            handleUpdateTitle(conversation.id);
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
                          handleUpdateTitle(conversation.id);
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
                        <div className="chat-conversation-title">
                          {conversation.title || 'New conversation'}
                        </div>
                        <div className="flex">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                            onClick={(e) => {
                              e.stopPropagation();
                              setNewTitle(conversation.title);
                              setEditingConversation(conversation.id);
                            }}
                          >
                            <Pencil1Icon className="h-3 w-3 text-gray-500 dark:text-gray-400" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (window.confirm('Are you sure you want to delete this conversation?')) {
                                handleDeleteConversation(conversation.id);
                              }
                            }}
                          >
                            <TrashIcon className="h-3 w-3 text-red-500" />
                          </Button>
                        </div>
                      </div>
                      <div className="chat-conversation-date">
                        {new Date(conversation.updated_at).toLocaleDateString()}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
          
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <Label htmlFor="streamingToggle" className="text-sm text-gray-700 dark:text-gray-300">
                Streaming
              </Label>
              <Switch 
                id="streamingToggle" 
                checked={useStreaming} 
                onCheckedChange={setUseStreaming}
              />
            </div>
          </div>
        </div>
        
        <div className="flex-1 flex flex-col overflow-hidden">
          {error && (
            <div className="p-4 bg-red-100 dark:bg-red-900/30 border-l-4 border-red-500 text-red-700 dark:text-red-300">
              <div className="flex">
                <div className="py-1">
                  <svg className="h-6 w-6 text-red-500 mr-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold">{error}</p>
                  <Button variant="ghost" size="sm" onClick={resetError} className="mt-2 text-red-700 dark:text-red-300">
                    Close
                  </Button>
                </div>
              </div>
            </div>
          )}

          {!currentConversation ? (
            <div className="flex-1 flex flex-col justify-center items-center p-8 text-center">
              <div className="mb-4 rounded-full bg-primary/10 p-3">
                <MessageSquareIcon className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-1">Start a new conversation</h3>
              <p className="text-muted-foreground mb-6 max-w-md">
                Write a message to start the conversation
              </p>
              <Button onClick={handleNewConversation} className="mt-2">
                New conversation
              </Button>
            </div>
          ) : (
            <>
              <div className="chat-header">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                  {currentConversation.title || 'New conversation'}
                </h2>
                <div className="flex items-center">
                  {isStreaming && (
                    <div className="flex items-center mr-4 text-blue-600 dark:text-blue-400">
                      <Loader className="animate-spin h-4 w-4 mr-2" />
                      <span className="text-sm">Processing...</span>
                    </div>
                  )}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm" className="btn-icon">
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
                        onClick={() => {
                          if (window.confirm('Are you sure you want to delete this conversation?')) {
                            handleDeleteConversation(currentConversation.id);
                          }
                        }}
                        className="text-red-600 focus:text-red-600"
                      >
                        <TrashIcon className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>

              <div className="chat-messages-container">
                {currentConversation.messages.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    Write a message to start the conversation
                  </div>
                ) : (
                  // Filter duplicate messages using a Set for IDs
                  [...new Map(currentConversation.messages.map(msg => [msg.id, msg])).values()].map((msg) => (
                    <ChatMessage 
                      key={`${msg.id}-${msg.role}`} 
                      message={msg} 
                      isLast={msg.role === 'user'}
                    />
                  ))
                )}
                
                {isStreaming && streamedContent && (
                  <div className="chat-message chat-message-assistant">
                    <div className="flex items-start">
                      <div className="flex-shrink-0 mr-2">
                        <BotIcon className="h-6 w-6 text-gray-600 dark:text-gray-400" />
                      </div>
                      <div className="chat-message-content">
                        {streamedContent}
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>

              <div className="chat-input-container">
                <form onSubmit={handleSubmit} className="flex">
                  <Input
                    ref={inputRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 min-w-0 bg-background ring-offset-background border-input"
                    disabled={isLoading || (currentConversation && currentConversation.messages.length > 1 && currentConversation.messages[currentConversation.messages.length - 1].role === 'user')}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleSubmit(e);
                      }
                    }}
                  />
                  <Button 
                    type="submit" 
                    className="ml-2 btn-primary px-4 flex items-center"
                    disabled={isLoading || !message.trim()}
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
    </div>
  );
}
