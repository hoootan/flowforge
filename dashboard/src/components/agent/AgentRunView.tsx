"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Brain, Zap, DollarSign, RotateCw } from "lucide-react";

interface AgentRunViewProps {
  agentResult: {
    output: string;
    status: "completed" | "max_iterations" | "max_tool_calls" | "failed";
    iterations: number;
    tool_calls_count: number;
    tokens_used: number;
    messages: any[];
    tool_calls: any[];
  };
}

function getStatusBadge(status: string) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    completed: "default",
    max_iterations: "outline",
    max_tool_calls: "outline",
    failed: "destructive",
  };

  const labels: Record<string, string> = {
    completed: "Completed",
    max_iterations: "Max Iterations",
    max_tool_calls: "Max Tool Calls",
    failed: "Failed",
  };

  return (
    <Badge variant={variants[status] || "outline"} className="capitalize">
      {labels[status] || status}
    </Badge>
  );
}

function estimateCost(tokensUsed: number): string {
  // Rough estimate: $0.015 per 1K tokens (average for Claude/GPT-4)
  const costPer1k = 0.015;
  const cost = (tokensUsed / 1000) * costPer1k;
  return cost < 0.01 ? "<$0.01" : `$${cost.toFixed(2)}`;
}

export function AgentRunView({ agentResult }: AgentRunViewProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            <CardTitle>Agent Execution</CardTitle>
          </div>
          {getStatusBadge(agentResult.status)}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Agent Output */}
        <div>
          <span className="text-sm font-medium text-muted-foreground">Output</span>
          <div className="mt-2 rounded-lg border bg-muted/50 p-3">
            <p className="text-sm whitespace-pre-wrap">{agentResult.output}</p>
          </div>
        </div>

        <Separator />

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/20">
              <RotateCw className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{agentResult.iterations}</p>
              <p className="text-xs text-muted-foreground">Iterations</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/20">
              <Zap className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{agentResult.tool_calls_count}</p>
              <p className="text-xs text-muted-foreground">Tool Calls</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/20">
              <Brain className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{agentResult.tokens_used.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">Tokens</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-100 dark:bg-yellow-900/20">
              <DollarSign className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{estimateCost(agentResult.tokens_used)}</p>
              <p className="text-xs text-muted-foreground">Est. Cost</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
