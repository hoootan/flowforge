"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { CollapsibleJson } from "@/components/ui/collapsible-json";
import {
  ArrowLeft,
  CheckCircle,
  Clock,
  XCircle,
  Pause,
  PlayCircle,
  Bot,
  Brain,
  Timer,
  Zap,
  RotateCw,
  Copy,
  StopCircle,
  Wrench,
} from "lucide-react";
import { toast } from "sonner";
import { api, RunWithSteps, Step } from "@/lib/api";
import { NotFoundState } from "@/components/empty-state";
import { hasAgentSteps, extractAgentResult } from "@/lib/hooks/useAgent";
import { AgentRunView } from "@/components/agent/AgentRunView";
import { AgentTimeline } from "@/components/agent/AgentTimeline";
import { useRunStream } from "@/hooks/useRunStream";

function getStepIcon(type: string) {
  switch (type) {
    case "run":
      return <PlayCircle className="h-4 w-4" />;
    case "ai":
      return <Brain className="h-4 w-4" />;
    case "sleep":
      return <Timer className="h-4 w-4" />;
    case "wait_for_event":
      return <Clock className="h-4 w-4" />;
    case "send_event":
      return <Zap className="h-4 w-4" />;
    case "agent":
      return <Brain className="h-4 w-4" />;
    case "sub_agent":
      return <Bot className="h-4 w-4" />;
    default:
      return <PlayCircle className="h-4 w-4" />;
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case "completed":
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case "running":
      return <Clock className="h-5 w-5 text-blue-500 animate-spin" />;
    case "failed":
      return <XCircle className="h-5 w-5 text-red-500" />;
    case "paused":
    case "sleeping":
    case "waiting":
      return <Pause className="h-5 w-5 text-yellow-500" />;
    default:
      return <Clock className="h-5 w-5 text-muted-foreground" />;
  }
}

function getStatusBadge(status: string) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    completed: "default",
    running: "secondary",
    failed: "destructive",
    paused: "outline",
    sleeping: "outline",
    waiting: "outline",
  };

  return (
    <Badge variant={variants[status] || "outline"} className="capitalize">
      {status}
    </Badge>
  );
}

function computeAIUsageTotals(steps: Step[]): { totalTokens: number; totalCost: number } {
  return steps.reduce(
    (acc, step) => {
      if (step.step_type !== "ai" || !step.output) return acc;
      const usage = (step.output as { usage?: { total_tokens?: number; cost_usd?: number } }).usage;
      return {
        totalTokens: acc.totalTokens + (usage?.total_tokens ?? 0),
        totalCost: acc.totalCost + (usage?.cost_usd ?? 0),
      };
    },
    { totalTokens: 0, totalCost: 0 }
  );
}

function formatDuration(startedAt: string | null, endedAt: string | null): string {
  if (!startedAt) return "—";
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  return date.toLocaleString();
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Skeleton className="h-96 w-full" />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    </div>
  );
}

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [run, setRun] = useState<RunWithSteps | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchRun = useCallback(async () => {
    const data = await api.getRun(id);
    setRun(data);
    return data;
  }, [id]);

  useEffect(() => {
    setLoading(true);
    fetchRun().finally(() => setLoading(false));
  }, [fetchRun]);

  const isActive = run?.status === "running" || run?.status === "pending" || run?.status === "paused";

  // Debounced refetch to avoid hammering the API on rapid events
  const refetchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debouncedFetchRun = useCallback(() => {
    if (refetchTimer.current) clearTimeout(refetchTimer.current);
    refetchTimer.current = setTimeout(() => {
      fetchRun();
    }, 300);
  }, [fetchRun]);

  const { isConnected } = useRunStream({
    runId: id,
    enabled: isActive,
    onEvent: (event) => {
      switch (event.type) {
        case "step_started":
        case "step_completed":
        case "step_failed":
        case "tool_call_completed":
        case "approval_required":
        case "approval_resolved":
        case "sub_agent_started":
        case "sub_agent_completed":
        case "run_started":
        case "run_paused":
        case "run_resumed":
        case "run_completed":
        case "run_failed":
          debouncedFetchRun();
          break;
      }
    },
  });

  // Polling fallback for when SSE connection fails or events are missed
  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(() => {
      fetchRun();
    }, isConnected ? 10000 : 3000);
    return () => clearInterval(interval);
  }, [isActive, isConnected, fetchRun]);

  const handleReplay = async () => {
    const result = await api.replayRun(id);
    if (result) {
      // Navigate to new run
      window.location.href = `/runs/${result.id}`;
    }
  };

  const handleCancel = async () => {
    const result = await api.cancelRun(id);
    if (result?.success) {
      toast.success("Run cancelled successfully");
      // Refresh run data
      const data = await api.getRun(id);
      setRun(data);
    } else {
      toast.error("Failed to cancel run");
    }
  };

  const handleCopyId = () => {
    navigator.clipboard.writeText(id);
  };

  const canCancel = run?.status === "running" || run?.status === "pending" || run?.status === "paused";

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (!run) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/runs">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
        </div>
        <NotFoundState resource="Run" />
      </div>
    );
  }

  const triggerData = run.trigger_data as { event?: { name?: string; data?: Record<string, unknown> } };
  const isAgentRun = hasAgentSteps(run);
  const agentResult = extractAgentResult(run);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/runs">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{run.function_id}</h1>
            {getStatusBadge(run.status)}
            {isConnected && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                Live
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
            <span className="font-mono">{run.id.slice(0, 8)}...</span>
            <span>&bull;</span>
            <span>Attempt {run.attempt}/{run.max_attempts}</span>
            <span>&bull;</span>
            <span>{formatDuration(run.started_at, run.ended_at)}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {canCancel && (
            <Button variant="destructive" size="sm" onClick={handleCancel}>
              <StopCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleReplay}>
            <RotateCw className="mr-2 h-4 w-4" />
            Replay
          </Button>
          <Button variant="outline" size="sm" onClick={handleCopyId}>
            <Copy className="mr-2 h-4 w-4" />
            Copy ID
          </Button>
        </div>
      </div>

      {/* Content */}
      {isAgentRun && agentResult ? (
        /* Agent-specific view */
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Agent Timeline */}
          <div className="lg:col-span-2 space-y-4">
            <AgentTimeline agentResult={agentResult} />
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Agent Stats */}
            <AgentRunView agentResult={agentResult} />

            {/* Run Info */}
            <Card>
              <CardHeader>
                <CardTitle>Run Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {(() => {
                  const { totalTokens, totalCost } = computeAIUsageTotals(run.steps);
                  if (totalTokens === 0) return null;
                  return (
                    <>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Total Tokens</span>
                        <span className="font-mono text-sm">{totalTokens.toLocaleString()}</span>
                      </div>
                      {totalCost > 0 && (
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Total Cost</span>
                          <span className="font-mono text-sm">${totalCost.toFixed(4)}</span>
                        </div>
                      )}
                      <Separator />
                    </>
                  );
                })()}
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Status</span>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(run.status)}
                    <span className="capitalize">{run.status}</span>
                  </div>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Started</span>
                  <span className="text-sm">{formatTimestamp(run.started_at)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Ended</span>
                  <span className="text-sm">
                    {run.ended_at ? formatTimestamp(run.ended_at) : "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Duration</span>
                  <span className="font-mono text-sm">{formatDuration(run.started_at, run.ended_at)}</span>
                </div>
              </CardContent>
            </Card>

            {/* Trigger Data */}
            <Card>
              <CardHeader>
                <CardTitle>Trigger Data</CardTitle>
              </CardHeader>
              <CardContent>
                <CollapsibleJson
                  value={triggerData.event?.data || run.trigger_data}
                  maxHeightClassName="max-h-64"
                />
              </CardContent>
            </Card>

            {/* Error (if failed) */}
            {run.error && (
              <Card className="border-red-200">
                <CardHeader>
                  <CardTitle className="text-red-600">Error</CardTitle>
                </CardHeader>
                <CardContent>
                  <CollapsibleJson
                    value={run.error}
                    maxHeightClassName="max-h-64"
                    className="border-red-200 bg-red-50 text-red-600"
                  />
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      ) : (
        /* Regular step-based view */
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Steps Timeline */}
          <div className="lg:col-span-2 space-y-4">
            <Card>
            <CardHeader>
              <CardTitle>Step Timeline</CardTitle>
              <CardDescription>
                Execution flow and step-by-step progress
              </CardDescription>
            </CardHeader>
            <CardContent>
              {run.steps.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">No steps executed yet.</p>
              ) : (
                <div className="relative">
                  {run.steps.map((step: Step, index: number) => (
                    <div key={step.id} className="flex gap-4 pb-6 last:pb-0">
                      {/* Timeline connector */}
                      <div className="flex flex-col items-center">
                        <div
                          className={`flex h-10 w-10 items-center justify-center rounded-full border-2 ${
                            step.status === "completed"
                              ? "border-green-500 bg-green-50 text-green-600"
                              : step.status === "running"
                              ? "border-blue-500 bg-blue-50 text-blue-600"
                              : step.status === "failed"
                              ? "border-red-500 bg-red-50 text-red-600"
                              : "border-muted bg-muted text-muted-foreground"
                          }`}
                        >
                          {getStepIcon(step.step_type)}
                        </div>
                        {index < run.steps.length - 1 && (
                          <div className="w-0.5 flex-1 bg-border" />
                        )}
                      </div>

                      {/* Step content */}
                      <div className="flex-1 pb-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{step.step_id}</span>
                            <Badge variant="outline" className="text-xs">
                              {step.step_type}
                            </Badge>
                            {getStatusBadge(step.status)}
                          </div>
                          <span className="font-mono text-sm text-muted-foreground">
                            {formatDuration(step.started_at, step.ended_at)}
                          </span>
                        </div>

                        {/* Step output preview */}
                        {step.output && (
                          <div className="rounded-lg border bg-muted/50 p-3">
                            {step.step_type === "ai" ? (
                              <div className="space-y-2">
                                {(step.output as { content?: string }).content && (
                                  <p className="text-sm">{(step.output as { content?: string }).content}</p>
                                )}
                                {(step.output as { tool_calls?: { id: string; name: string; arguments: Record<string, unknown> }[] }).tool_calls && (
                                  <div className="space-y-1.5">
                                    {(step.output as { tool_calls: { id: string; name: string; arguments: Record<string, unknown> }[] }).tool_calls.map((tc) => (
                                      <div key={tc.id} className="flex items-start gap-2 rounded border bg-background p-2">
                                        <Wrench className="h-3.5 w-3.5 mt-0.5 text-muted-foreground shrink-0" />
                                        <div className="min-w-0">
                                          <span className="text-sm font-medium">{tc.name}</span>
                                          <pre className="text-xs text-muted-foreground mt-0.5 whitespace-pre-wrap break-all">{JSON.stringify(tc.arguments, null, 2)}</pre>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                                <div className="flex gap-4 text-xs text-muted-foreground">
                                  <span>Model: {(step.output as { model?: string }).model}</span>
                                  <span>Tokens: {(step.output as { usage?: { total_tokens?: number } }).usage?.total_tokens}</span>
                                  <span>Cost: ${(step.output as { usage?: { cost_usd?: number } }).usage?.cost_usd?.toFixed(4)}</span>
                                </div>
                              </div>
                            ) : (
                              <CollapsibleJson value={step.output} maxHeightClassName="max-h-64" />
                            )}
                          </div>
                        )}

                        {/* Step error */}
                        {step.error && (
                          <div className="mt-2">
                            <CollapsibleJson
                              value={step.error}
                              maxHeightClassName="max-h-64"
                              className="border-red-200 bg-red-50 text-red-600"
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Run Info */}
          <Card>
            <CardHeader>
              <CardTitle>Run Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {(() => {
                const { totalTokens, totalCost } = computeAIUsageTotals(run.steps);
                if (totalTokens === 0) return null;
                return (
                  <>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Total Tokens</span>
                      <span className="font-mono text-sm">{totalTokens.toLocaleString()}</span>
                    </div>
                    {totalCost > 0 && (
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Total Cost</span>
                        <span className="font-mono text-sm">${totalCost.toFixed(4)}</span>
                      </div>
                    )}
                    <Separator />
                  </>
                );
              })()}
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <div className="flex items-center gap-2">
                  {getStatusIcon(run.status)}
                  <span className="capitalize">{run.status}</span>
                </div>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Started</span>
                <span className="text-sm">{formatTimestamp(run.started_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Ended</span>
                <span className="text-sm">
                  {run.ended_at ? formatTimestamp(run.ended_at) : "—"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Duration</span>
                <span className="font-mono text-sm">{formatDuration(run.started_at, run.ended_at)}</span>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Trigger</span>
                <Badge variant="outline" className="font-mono text-xs">
                  {run.trigger_type}
                </Badge>
              </div>
              {run.event_id && (
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Event ID</span>
                  <span className="font-mono text-xs">{run.event_id.slice(0, 8)}...</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Event Data */}
          <Card>
            <CardHeader>
              <CardTitle>Trigger Data</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="input">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="input">Input</TabsTrigger>
                  <TabsTrigger value="output">Output</TabsTrigger>
                </TabsList>
                <TabsContent value="input" className="mt-4">
                  <CollapsibleJson
                    value={triggerData.event?.data || run.trigger_data}
                    maxHeightClassName="max-h-64"
                  />
                </TabsContent>
                <TabsContent value="output" className="mt-4">
                  <CollapsibleJson
                    value={run.output ?? "No output yet"}
                    maxHeightClassName="max-h-64"
                  />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Error (if failed) */}
          {run.error && (
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="text-red-600">Error</CardTitle>
              </CardHeader>
              <CardContent>
                <CollapsibleJson
                  value={run.error}
                  maxHeightClassName="max-h-64"
                  className="border-red-200 bg-red-50 text-red-600"
                />
              </CardContent>
            </Card>
          )}
          </div>
        </div>
      )}
    </div>
  );
}
