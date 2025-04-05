'use client';

import { Sidebar } from '@/components/ui/sidebar';
import { UpgradeNotice } from '@/components/ui/upgrade-notice';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen">
      <div className="w-64 flex-shrink-0">
        <Sidebar />
      </div>
      <div className="flex-1 overflow-auto">
        <div className="container mx-auto p-6">
          <UpgradeNotice />
          {children}
        </div>
      </div>
    </div>
  );
}
