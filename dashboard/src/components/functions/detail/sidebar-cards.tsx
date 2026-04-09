"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Wrench, ShieldAlert } from "lucide-react";

// ── Agent Config Card ────────────────────────────────────────

export function AgentConfigCard({
  model,
  agentConfig,
  functionConfig,
}: {
  model: string;
  agentConfig: Record<string, unknown>;
  functionConfig: Record<string, unknown>;
}) {
  const rows = [
    { label: "Model", value: model },
    { label: "Max Iterations", value: (agentConfig?.max_iterations as number) || 30 },
    { label: "Max Tool Calls", value: (agentConfig?.max_tool_calls as number) || 50 },
    { label: "Retries", value: (functionConfig?.retries as number) || 3 },
    { label: "Timeout", value: (functionConfig?.timeout as string) || "300s" },
    { label: "Concurrency", value: (functionConfig?.concurrency_limit as number) || 5 },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Agent Configuration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-0">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between py-2.5 border-b last:border-0">
            <span className="text-sm text-muted-foreground">{row.label}</span>
            <span className="text-sm font-mono font-medium">{row.value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ── Attached Tools Card ──────────────────────────────────────

export function AttachedToolsCard({
  toolNames,
  tools,
}: {
  toolNames: string[];
  tools?: { name: string; description: string; requires_approval: boolean }[];
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Attached Tools</CardTitle>
          <Badge variant="secondary" className="text-xs">{toolNames.length} tools</Badge>
        </div>
      </CardHeader>
      <CardContent>
        {toolNames.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">No tools attached</p>
        ) : (
          <div className="space-y-1">
            {toolNames.map((name) => {
              const tool = tools?.find((t) => t.name === name);
              return (
                <div key={name} className="flex items-center gap-3 py-2 px-2 rounded-md hover:bg-muted/50">
                  <div className="h-8 w-8 rounded-md bg-muted flex items-center justify-center shrink-0">
                    <Wrench className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium font-mono">{name}</p>
                    {tool?.description && <p className="text-xs text-muted-foreground truncate">{tool.description}</p>}
                  </div>
                  {tool?.requires_approval && (
                    <Badge variant="outline" className="text-xs text-amber-600 border-amber-300 shrink-0">
                      <ShieldAlert className="h-3 w-3 mr-1" /> approval
                    </Badge>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Trigger Card ─────────────────────────────────────────────

const triggerBadge: Record<string, string> = {
  event: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
  cron: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  webhook: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
};

export function TriggerCard({
  triggerType,
  triggerValue,
  triggerExpression,
}: {
  triggerType: string;
  triggerValue: string;
  triggerExpression: string | null;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Trigger</CardTitle>
      </CardHeader>
      <CardContent className="space-y-0">
        <div className="flex items-center justify-between py-2.5 border-b">
          <span className="text-sm text-muted-foreground">Type</span>
          <Badge variant="secondary" className={`text-xs ${triggerBadge[triggerType] || ""}`}>{triggerType}</Badge>
        </div>
        <div className="flex items-center justify-between py-2.5 border-b">
          <span className="text-sm text-muted-foreground">
            {triggerType === "event" ? "Event Name" : triggerType === "cron" ? "Schedule" : "Path"}
          </span>
          <span className="text-sm font-mono font-medium">{triggerValue}</span>
        </div>
        <div className="flex items-center justify-between py-2.5">
          <span className="text-sm text-muted-foreground">Filter</span>
          <span className="text-sm font-mono text-muted-foreground">{triggerExpression || "none"}</span>
        </div>
      </CardContent>
    </Card>
  );
}

// ── System Prompt Card ───────────────────────────────────────

export function SystemPromptCard({ systemPrompt }: { systemPrompt: string | null }) {
  if (!systemPrompt) return null;
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">System Prompt</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="bg-muted/50 rounded-lg p-4 text-sm leading-relaxed font-mono whitespace-pre-wrap max-h-[300px] overflow-y-auto">
          {systemPrompt}
        </div>
      </CardContent>
    </Card>
  );
}
