'use client';

import { DashboardShell, DashboardHeader } from '@/components/ui';
import { PipelineConfigList } from '@/components/pipelines/config';

export default function PipelineConfigsPage() {
  return (
    <DashboardShell>
      <DashboardHeader
        heading="Pipeline configurations"
        text="Manage the pipeline configurations for document processing"
      />
      <div className="grid gap-8">
        <PipelineConfigList />
      </div>
    </DashboardShell>
  );
}
