'use client'; // Indicate this is a Client Component if it needs interactivity

import AgentChatInterface from '@/components/agent/AgentChatInterface'; // Import the component

export default function AgentPage() {
  return (
    <div className="flex-1 flex flex-col">
      <AgentChatInterface />
    </div>
  );
} 