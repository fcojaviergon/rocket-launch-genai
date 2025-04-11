'use client';

import React from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Bot, User, Wrench, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import ReactMarkdown from 'react-markdown';

interface ChatMessageProps {
  message: {
    id: string;
    content: string;
    role: 'user' | 'assistant' | 'system' | 'tool' | 'thinking';
    timestamp?: string;
  };
  isLast?: boolean;
}

export function ChatMessage({ message, isLast = false }: ChatMessageProps) {
  // Parse tool messages to extract action and result
  let toolAction = '';
  let toolResult = '';
  
  if (message.role === 'tool' && message.content.includes('\nResult: ')) {
    const parts = message.content.split('\nResult: ');
    toolAction = parts[0].replace('Tool Call: ', '');
    toolResult = parts[1];
  }
  
  return (
    <div 
      className={cn(
        'flex w-full items-start gap-4 py-4',
        message.role === 'thinking' && 'bg-blue-50/30 border-l-4 border-blue-200',
        message.role === 'tool' && 'bg-gray-50/30 border-l-4 border-gray-200'
      )}
      id={message.id}
    >
      {message.role === 'user' && (
        <Avatar className="h-8 w-8">
          <AvatarFallback className="bg-primary text-primary-foreground">
            <User className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}
      
      {message.role === 'assistant' && (
        <Avatar className="h-8 w-8">
          <AvatarFallback className="bg-blue-500 text-white">
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}
      
      {message.role === 'thinking' && (
        <Avatar className="h-8 w-8">
          <AvatarFallback className="bg-blue-300 text-white">
            <Brain className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}
      
      {message.role === 'tool' && (
        <Avatar className="h-8 w-8">
          <AvatarFallback className="bg-gray-500 text-white">
            <Wrench className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}

      <div className="flex flex-col gap-2 w-full max-w-[calc(100%-64px)]">
        {message.role === 'thinking' ? (
          <div className="flex flex-col">
            <div className="text-xs font-medium text-blue-600 mb-1">Thinking Process</div>
            <Card className="p-3 bg-blue-50/50 border-blue-100 prose prose-sm">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </Card>
          </div>
        ) : message.role === 'tool' ? (
          <div className="flex flex-col">
            <div className="text-xs font-medium text-gray-600 mb-1">Tool Execution</div>
            <Card className="p-3 bg-gray-50/50 border-gray-100">
              <div className="text-xs text-gray-500 font-mono mb-2 bg-gray-100 p-2 rounded">
                {toolAction}
              </div>
              <div className="text-sm border-t pt-2">
                <div className="text-xs uppercase font-semibold text-gray-500 mb-1">Result:</div>
                <ReactMarkdown>
                  {toolResult}
                </ReactMarkdown>
              </div>
            </Card>
          </div>
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
} 