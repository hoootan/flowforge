"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { CollapsibleJson } from "@/components/ui/collapsible-json";
import { CheckCircle, XCircle, Clock, AlertCircle } from "lucide-react";

interface ToolCallDetailProps {
  toolCall: {
    id: string;
    tool_name: string;
    arguments: Record<string, any>;
    result?: any;
    error?: string;
    execution_time_ms?: number;
    requires_approval?: boolean;
    approval_status?: "pending" | "approved" | "rejected";
    rejection_reason?: string;
  };
}

function formatExecutionTime(ms?: number): string {
  if (!ms) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function getApprovalBadge(status?: string) {
  if (!status) return null;

  const config = {
    pending: { variant: "outline" as const, label: "Pending Approval", icon: Clock },
    approved: { variant: "default" as const, label: "Approved", icon: CheckCircle },
    rejected: { variant: "destructive" as const, label: "Rejected", icon: XCircle },
  };

  const { variant, label, icon: Icon } = config[status as keyof typeof config] || config.pending;

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}

export function ToolCallDetail({ toolCall }: ToolCallDetailProps) {
  return (
    <Card className="border-l-4 border-l-primary">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">{toolCall.tool_name}</CardTitle>
            {toolCall.requires_approval && getApprovalBadge(toolCall.approval_status)}
          </div>
          <span className="font-mono text-xs text-muted-foreground">
            {formatExecutionTime(toolCall.execution_time_ms)}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Arguments */}
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="text-sm font-medium">Arguments</span>
            <Badge variant="outline" className="text-xs">JSON</Badge>
          </div>
          <CollapsibleJson value={toolCall.arguments} maxHeightClassName="max-h-48" />
        </div>

        <Separator />

        {/* Result or Error */}
        {toolCall.error ? (
          <div>
            <div className="mb-2 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-500" />
              <span className="text-sm font-medium text-red-600">Error</span>
            </div>
            <CollapsibleJson
              value={toolCall.error}
              maxHeightClassName="max-h-48"
              className="border-red-200 bg-red-50 text-red-600 dark:bg-red-900/20 dark:border-red-900"
            />
          </div>
        ) : toolCall.result !== undefined ? (
          <div>
            <div className="mb-2 flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span className="text-sm font-medium">Result</span>
            </div>
            <CollapsibleJson value={toolCall.result} maxHeightClassName="max-h-48" />
          </div>
        ) : (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span className="text-sm">No result yet</span>
          </div>
        )}

        {/* Rejection Reason */}
        {toolCall.approval_status === "rejected" && toolCall.rejection_reason && (
          <>
            <Separator />
            <div>
              <div className="mb-2 flex items-center gap-2">
                <XCircle className="h-4 w-4 text-red-500" />
                <span className="text-sm font-medium text-red-600">Rejection Reason</span>
              </div>
              <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:border-red-900">
                {toolCall.rejection_reason}
              </p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
