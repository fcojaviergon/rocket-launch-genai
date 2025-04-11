'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LucideIcon, Home, MessageSquare, Calendar, FileText, BarChart2, Settings, LogOut, Sparkles, MessagesSquare, Users, Zap, Bot } from 'lucide-react';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { signOut, useSession } from 'next-auth/react';

interface SidebarItemProps {
  icon: LucideIcon;
  label: string;
  href: string;
  badge?: number;
}

const SidebarItem = ({ icon: Icon, label, href, badge }: SidebarItemProps) => {
  const pathname = usePathname();
  const isActive = pathname === href;

  return (
    <Link 
      href={href} 
      className={cn(
        "dashboard-nav-item",
        isActive && "active"
      )}
    >
      <Icon className="h-5 w-5" />
      <span className="flex-1">{label}</span>
      {badge && (
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/20 text-xs font-medium text-blue-200">
          {badge}
        </span>
      )}
    </Link>
  );
};

export function Sidebar() {
  const { data: session } = useSession();
  const isAdmin = session?.user?.role === 'admin';

  return (
    <div className="flex h-screen flex-col bg-gray-900">
      <div className="p-6">
        <h2 className="text-xl font-bold text-white">Rocket Launch GenAI Platform</h2>
      </div>
      <div className="flex-1 overflow-auto py-2">
        <nav className="grid items-start gap-1">
          <SidebarItem icon={Home} label="Dashboard" href="/dashboard" />
          <SidebarItem icon={Bot} label="Agent" href="/dashboard/agent" />
          <SidebarItem icon={MessageSquare} label="RAG" href="/dashboard/messages" />
          <SidebarItem icon={Sparkles} label="Completions" href="/dashboard/completions" />
          <SidebarItem icon={MessagesSquare} label="Chat AI" href="/dashboard/chat" />
          <SidebarItem icon={FileText} label="Documentos" href="/dashboard/documents" />
          <SidebarItem icon={Zap} label="Pipelines" href="/dashboard/pipelines" />
          <SidebarItem icon={BarChart2} label="Analítica" href="/dashboard/analytics" />
          {isAdmin && (
            <SidebarItem icon={Users} label="Usuarios" href="/dashboard/users" />
          )}
          <SidebarItem icon={Settings} label="Configuración" href="/dashboard/settings" />
        </nav>
      </div>
      <div className="mt-auto p-4">
        <button 
          onClick={() => signOut()}
          className="dashboard-nav-item w-full"
        >
          <LogOut className="h-5 w-5" />
          <span>Cerrar sesión</span>
        </button>
      </div>
    </div>
  );
}