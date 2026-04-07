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
  Activity,
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
  Wrench,
} from "lucide-react";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
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
      return <CheckCircle className="h-5 w-5 text-emerald-500" />;
    case "running":
      return <Clock className="h-5 w-5 text-primary animate-spin" />;
    case "failed":
      return <XCircle className="h-5 w-5 text-destructive" />;
    case "paused":
    case "sleeping":
    case "waiting":
      return <Pause className="h-5 w-5 text-amber-500" />;
    default:
      return <Clock className="h-5 w-5 text-muted-foreground" />;
  }
}

const statusBadgeStyles: Record<string, string> = {
  completed: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400",
  running: "border-primary/20 bg-primary/10 text-primary",
  failed: "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400",
  paused: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400",
  sleeping: "border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-800 dark:bg-cyan-950 dark:text-cyan-400",
  waiting: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400",
};

function getStatusBadge(status: string) {
  return (
    <Badge variant="outline" className={`capitalize ${statusBadgeStyles[status] || ""}`}>
      {status}
    </Badge>
  );
}

// ── Step color mapping for waterfall (matches Paper design) ────

const stepTypeColors: Record<string, { bg: string; text: string; label: string }> = {
  run: { bg: "bg-[var(--chart-1)]", text: "text-white", label: "run" },
  ai: { bg: "bg-[var(--chart-6)]", text: "text-white", label: "ai" },
  wait_for_event: { bg: "bg-[var(--chart-4)]", text: "text-black", label: "wait" },
  sleep: { bg: "bg-[var(--chart-2)]", text: "text-white", label: "sleep" },
  invoke: { bg: "bg-[var(--chart-3)]", text: "text-white", label: "invoke" },
  send_event: { bg: "bg-[var(--chart-3)]", text: "text-white", label: "send" },
  agent: { bg: "bg-[var(--chart-6)]", text: "text-white", label: "agent" },
  sub_agent: { bg: "bg-[var(--chart-6)]", text: "text-white", label: "sub_agent" },
};

// ── Waterfall helpers ───────────────────────────────────────────

/** Format ms to human-readable: 120ms, 3.2s, 2m 15s, 1h 30m */
function formatWaterfallDuration(ms: number): string {
  if (ms < 0) ms = 0;
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const totalSec = Math.round(ms / 1000);
  if (totalSec < 3600) {
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return s > 0 ? `${m}m ${s}s` : `${m}m`;
  }
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

/** Strip common step_id prefixes like "stage:N-" for cleaner display */
function shortenStepId(id: string): string {
  return id.replace(/^stage:\d+-/, "") || id;
}

/** Compute the actual time span that steps occupy. */
function computeStepSpan(
  steps: Step[],
  fallbackMs: number,
  now: number,
): { spanStart: number; spanDuration: number } {
  const starts: number[] = [];
  const ends: number[] = [];
  for (const s of steps) {
    if (s.started_at) starts.push(new Date(s.started_at).getTime());
    if (s.ended_at) ends.push(new Date(s.ended_at).getTime());
    else if (s.started_at) ends.push(now);
  }
  if (starts.length === 0) return { spanStart: 0, spanDuration: fallbackMs };
  const spanStart = Math.min(...starts);
  const spanEnd = Math.max(...ends);
  return { spanStart, spanDuration: Math.max(spanEnd - spanStart, 1) };
}

// ── Waterfall Timeline Component ───────────────────────────────

const INITIAL_VISIBLE_STEPS = 15;

function WaterfallTimeline({
  steps,
  totalDuration,
  runStartedAt,
  now,
}: {
  steps: Step[];
  totalDuration: number;
  runStartedAt?: string | null;
  now: number;
}) {
  const [expanded, setExpanded] = useState(false);

  if (steps.length === 0) return null;

  // Zoom to actual step span instead of full run duration
  const { spanStart, spanDuration } = computeStepSpan(steps, totalDuration, now);

  // Limit visible steps
  const visibleSteps = expanded ? steps : steps.slice(0, INITIAL_VISIBLE_STEPS);
  const hiddenCount = steps.length - INITIAL_VISIBLE_STEPS;

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((pct) => ({
    label: formatWaterfallDuration(spanDuration * pct),
    pct: pct * 100,
  }));

  return (
    <div className="space-y-3">
      {/* Time axis */}
      <div className="relative h-5 text-xs text-muted-foreground ml-[200px]">
        {ticks.map((tick) => (
          <span
            key={tick.pct}
            className="absolute font-mono"
            style={{
              left: `${tick.pct}%`,
              transform:
                tick.pct === 100
                  ? "translateX(-100%)"
                  : tick.pct === 0
                    ? "none"
                    : "translateX(-50%)",
            }}
          >
            {tick.label}
          </span>
        ))}
      </div>

      {/* Step bars */}
      <div className="space-y-1.5">
        {visibleSteps.map((step) => {
          const stepStart = step.started_at
            ? new Date(step.started_at).getTime()
            : spanStart;
          const stepEnd = step.ended_at
            ? new Date(step.ended_at).getTime()
            : now;
          const offset = Math.max(
            ((stepStart - spanStart) / spanDuration) * 100,
            0,
          );
          const width = Math.max(
            ((stepEnd - stepStart) / spanDuration) * 100,
            3,
          );
          const duration = stepEnd - stepStart;
          const colors = stepTypeColors[step.step_type] || stepTypeColors.run;

          return (
            <div key={step.id} className="flex items-center gap-3 h-7">
              <span
                className="w-[188px] truncate text-right text-xs font-mono text-muted-foreground flex-shrink-0"
                title={step.step_id}
              >
                {shortenStepId(step.step_id)}
              </span>
              <div className="relative flex-1 h-full">
                <div
                  className={`absolute top-0 h-full rounded ${colors.bg} ${step.status === "failed" ? "!bg-destructive" : ""} flex items-center px-2`}
                  style={{
                    left: `${offset}%`,
                    width: `${Math.min(width, 100 - offset)}%`,
                    minWidth: "48px",
                  }}
                >
                  <span
                    className={`text-[11px] font-medium ${step.status === "failed" ? "text-white" : colors.text} truncate whitespace-nowrap`}
                  >
                    {formatWaterfallDuration(duration)}
                    {width > 8 && (
                      <span className="opacity-60 ml-1">{colors.label}</span>
                    )}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Expand / collapse */}
      {hiddenCount > 0 && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="text-xs text-primary hover:underline font-medium ml-[200px]"
        >
          Show {hiddenCount} more step{hiddenCount > 1 ? "s" : ""}
        </button>
      )}
      {expanded && hiddenCount > 0 && (
        <button
          onClick={() => setExpanded(false)}
          className="text-xs text-muted-foreground hover:text-foreground font-medium ml-[200px]"
        >
          Show fewer
        </button>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-3 pt-2 text-xs text-muted-foreground">
        {Object.entries(stepTypeColors)
          .slice(0, 6)
          .map(([type, colors]) => (
            <span key={type} className="flex items-center gap-1.5">
              <span className={`h-2.5 w-2.5 rounded-sm ${colors.bg}`} />
              {colors.label}
            </span>
          ))}
      </div>
    </div>
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
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const ticker = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(ticker);
  }, []);

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
  const { totalTokens, totalCost } = computeAIUsageTotals(run.steps);
  const runDurationMs = run.started_at
    ? (run.ended_at ? new Date(run.ended_at).getTime() : now) - new Date(run.started_at).getTime()
    : 0;
  const aiModel = run.steps.find((s) => s.step_type === "ai" && s.output)?.output as { model?: string } | undefined;
  const aiLatency = run.steps.filter((s) => s.step_type === "ai" && s.started_at && s.ended_at).reduce((sum, s) => {
    return sum + (new Date(s.ended_at!).getTime() - new Date(s.started_at!).getTime());
  }, 0);

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
            <h1 className="text-2xl font-bold tracking-tight font-mono">{run.function_id}</h1>
            {getStatusBadge(run.status)}
            {isConnected && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Live
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
            <span className="font-mono text-xs">{run.id.slice(0, 12)}</span>
            <span className="text-border">|</span>
            <span>Trigger: {run.trigger_type}</span>
            <span className="text-border">|</span>
            <span>Duration: {formatDuration(run.started_at, run.ended_at)}</span>
            <span className="text-border">|</span>
            <span>Started {run.started_at ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true }) : "—"}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {canCancel && (
            <Button variant="outline" size="sm" onClick={handleCancel}>
              Cancel
            </Button>
          )}
          <Button size="sm" onClick={handleReplay}>
            <RotateCw className="mr-2 h-4 w-4" />
            Replay
          </Button>
        </div>
      </div>

      {/* Run Stats Cards (matching Paper design) */}
      {totalTokens > 0 && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="bg-muted/30">
            <CardContent className="flex items-center gap-3 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Activity className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold tabular-nums">{totalTokens.toLocaleString()}</p>
                <p className="text-xs text-muted-foreground">Total Tokens</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-muted/30">
            <CardContent className="flex items-center gap-3 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
                <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">$</span>
              </div>
              <div>
                <p className="text-2xl font-bold tabular-nums">${totalCost.toFixed(3)}</p>
                <p className="text-xs text-muted-foreground">Total Cost</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-muted/30">
            <CardContent className="flex items-center gap-3 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--chart-6)]/10">
                <Brain className="h-5 w-5 text-[var(--chart-6)]" />
              </div>
              <div>
                <p className="text-2xl font-bold">{aiModel?.model || "—"}</p>
                <p className="text-xs text-muted-foreground">Model Used</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-muted/30">
            <CardContent className="flex items-center gap-3 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10">
                <Timer className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-2xl font-bold tabular-nums">{aiLatency > 0 ? `${aiLatency}ms` : "—"}</p>
                <p className="text-xs text-muted-foreground">AI Latency</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

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
            {/* Waterfall Timeline Card */}
            {run.steps.length > 0 && runDurationMs > 0 && (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>Execution Timeline</CardTitle>
                    <CardDescription>
                      Step-by-step waterfall view — {run.steps.length} steps
                    </CardDescription>
                  </div>
                </CardHeader>
                <CardContent>
                  <WaterfallTimeline steps={run.steps} totalDuration={runDurationMs} runStartedAt={run.started_at} now={now} />
                </CardContent>
              </Card>
            )}

            <Card>
            <CardHeader>
              <CardTitle>Step Details</CardTitle>
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
                              ? "border-emerald-500 bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400"
                              : step.status === "running"
                              ? "border-primary bg-primary/10 text-primary"
                              : step.status === "failed"
                              ? "border-destructive bg-red-50 text-destructive dark:bg-red-950"
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
