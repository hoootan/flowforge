"use client";

import { use, useCallback, useEffect, useState } from "react";
import { api, type Function as FunctionType, type Run, type Tool } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { NotFoundState } from "@/components/empty-state";
import { FunctionHeader } from "@/components/functions/detail/function-header";
import { FunctionKPIs } from "@/components/functions/detail/function-kpis";
import { RecentRuns } from "@/components/functions/detail/recent-runs";
import {
  AgentConfigCard,
  AttachedToolsCard,
  TriggerCard,
  SystemPromptCard,
} from "@/components/functions/detail/sidebar-cards";

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-6 w-40" />
      <div className="flex items-center gap-4">
        <Skeleton className="h-12 w-12 rounded-xl" />
        <div className="space-y-2"><Skeleton className="h-8 w-64" /><Skeleton className="h-4 w-80" /></div>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6"><Skeleton className="h-64" /><Skeleton className="h-48" /></div>
        <div className="space-y-6"><Skeleton className="h-48" /><Skeleton className="h-48" /><Skeleton className="h-32" /></div>
      </div>
    </div>
  );
}

export default function FunctionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [func, setFunc] = useState<FunctionType | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const [funcData, runsData, toolsData] = await Promise.all([
      api.getFunction(id),
      api.getRuns({ function_id: id, page_size: 5 }),
      api.getTools(),
    ]);
    setFunc(funcData);
    setRuns(runsData.runs);
    setTools(toolsData.tools);
    setLoading(false);
  }, [id]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <LoadingSkeleton />;
  if (!func) return <NotFoundState resource="Function" />;

  // Compute KPIs
  const completedRuns = runs.filter((r) => r.status === "completed");
  const failedRuns = runs.filter((r) => r.status === "failed");
  const totalRuns = completedRuns.length + failedRuns.length;
  const successRate = totalRuns > 0 ? (completedRuns.length / totalRuns) * 100 : 0;
  const avgDurationMs = completedRuns.reduce((sum, r) => {
    if (r.started_at && r.ended_at) return sum + (new Date(r.ended_at).getTime() - new Date(r.started_at).getTime());
    return sum;
  }, 0);
  const avgDuration = completedRuns.length > 0 ? `${(avgDurationMs / completedRuns.length / 1000).toFixed(1)}s` : "-";

  const agentConfig = (func.agent_config || {}) as Record<string, unknown>;
  const model = (agentConfig.model as string) || "claude-sonnet-4-6";

  return (
    <div className="space-y-6">
      <FunctionHeader func={func} />

      <FunctionKPIs
        totalRuns={totalRuns}
        successRate={successRate}
        avgDuration={avgDuration}
        totalCost={totalRuns * 0.015}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <RecentRuns runs={runs} functionId={func.function_id} />
          {func.is_inline && <SystemPromptCard systemPrompt={func.system_prompt} />}
        </div>
        <div className="space-y-6">
          {func.is_inline && (
            <AgentConfigCard model={model} agentConfig={agentConfig} functionConfig={func.config} />
          )}
          <AttachedToolsCard
            toolNames={func.tools_config || []}
            tools={tools.map((t) => ({ name: t.name, description: t.description, requires_approval: t.requires_approval }))}
          />
          <TriggerCard triggerType={func.trigger_type} triggerValue={func.trigger_value} triggerExpression={func.trigger_expression} />
          {!func.is_inline && func.endpoint_url && (
            <div className="rounded-lg border p-4 space-y-2">
              <h3 className="text-sm font-medium">Worker Endpoint</h3>
              <p className="font-mono text-xs text-muted-foreground break-all">{func.endpoint_url}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
