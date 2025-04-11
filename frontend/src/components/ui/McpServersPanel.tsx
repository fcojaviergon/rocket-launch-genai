'use client';

import React, { useState, useEffect } from 'react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
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
import { ChevronDown, Server, Code, Terminal } from 'lucide-react';
import { Badge } from "@/components/ui/badge";
import { getSession } from 'next-auth/react';
import { toast } from 'sonner';

interface McpCommand {
  name: string;
}

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

export function McpServersPanel() {
  const [servers, setServers] = useState<Record<string, McpServer>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  // Fetch MCP servers info
  useEffect(() => {
    const fetchServers = async () => {
      try {
        setLoading(true);
        const session = await getSession();
        
        if (!session?.accessToken) {
          throw new Error("No active session");
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
          setServers(data.servers);
        } else {
          setError('Failed to load MCP servers');
        }
      } catch (err) {
        console.error('Error fetching MCP servers:', err);
        setError('Error loading MCP servers');
        toast.error('Failed to load MCP servers');
      } finally {
        setLoading(false);
      }
    };

    fetchServers();
  }, []);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button 
          variant="outline" 
          className="flex items-center gap-2"
          onClick={() => setIsOpen(!isOpen)}
        >
          <Server className="h-4 w-4" />
          <span>MCP Servers</span>
          <Badge variant="outline" className="ml-2">
            {Object.keys(servers).length}
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
            {loading ? (
              <div className="flex justify-center py-4">
                <span className="animate-spin mr-2">⏳</span> Loading...
              </div>
            ) : error ? (
              <div className="text-red-500 py-4">{error}</div>
            ) : Object.keys(servers).length === 0 ? (
              <div className="text-muted-foreground py-4">No MCP servers available</div>
            ) : (
              <div className="space-y-2">
                {Object.entries(servers).map(([name, server]) => (
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
} 