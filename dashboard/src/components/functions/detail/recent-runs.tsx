"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import type { Run } from "@/lib/api";

const statusDot: Record<string, string> = {
  running: "bg-blue-500", completed: "bg-green-500", failed: "bg-red-500",
  pending: "bg-yellow-500", paused: "bg-amber-500", cancelled: "bg-gray-400",
};

function formatDuration(startedAt: string | null, endedAt: string | null): string {
  if (!startedAt) return "-";
  const ms = (endedAt ? new Date(endedAt).getTime() : Date.now()) - new Date(startedAt).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

export function RecentRuns({ runs, functionId }: { runs: Run[]; functionId: string }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Recent Runs</CardTitle>
          <Link href={`/runs?function_id=${functionId}`} className="text-xs text-primary hover:underline flex items-center gap-1">
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {runs.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">No runs yet</p>
        ) : (
          <div className="space-y-1">
            {runs.map((run) => (
              <Link key={run.id} href={`/runs/${run.id}`} className="flex items-center gap-3 py-2 px-2 rounded-md hover:bg-muted/50 transition-colors">
                <span className={`h-2 w-2 rounded-full shrink-0 ${statusDot[run.status] || "bg-gray-400"}`} />
                <span className="font-mono text-xs text-muted-foreground w-20 truncate">{run.id.slice(0, 12)}</span>
                <Badge variant="secondary" className="text-xs">{run.status}</Badge>
                <span className="flex-1" />
                <span className="text-xs text-muted-foreground">{run.started_at ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true }) : "pending"}</span>
                <span className="text-xs font-mono text-muted-foreground w-14 text-right">{formatDuration(run.started_at, run.ended_at)}</span>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
