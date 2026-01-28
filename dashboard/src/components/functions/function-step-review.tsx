"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Bot, Server, Zap, Clock, Globe, Wrench, Check, MessageSquare } from "lucide-react";
import type { FunctionMode } from "./function-step-type";
import type { TriggerType } from "./function-step-identity";
import type { Tool } from "@/lib/api";

const TRIGGER_LABELS: Record<TriggerType, { label: string; icon: typeof Zap }> = {
  event: { label: "Event", icon: Zap },
  cron: { label: "Schedule", icon: Clock },
  webhook: { label: "Webhook", icon: Globe },
};

interface FunctionStepReviewProps {
  mode: FunctionMode;
  id: string;
  name: string;
  triggerType: TriggerType;
  triggerValue: string;
  // AI Agent
  model: string;
  systemPrompt: string;
  selectedTools: string[];
  availableTools: Tool[];
  // Worker
  endpointUrl: string;
}

export function FunctionStepReview({
  mode,
  id,
  name,
  triggerType,
  triggerValue,
  model,
  systemPrompt,
  selectedTools,
  availableTools,
  endpointUrl,
}: FunctionStepReviewProps) {
  const TriggerIcon = TRIGGER_LABELS[triggerType].icon;
  const ModeIcon = mode === "inline" ? Bot : Server;

  const selectedToolObjects = availableTools.filter((t) => selectedTools.includes(t.name));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">Review & Create</h2>
        <p className="text-sm text-muted-foreground">
          Review your function configuration before creating it.
        </p>
      </div>

      {/* Summary card */}
      <Card>
        <CardContent className="p-5 space-y-5">
          {/* Identity */}
          <div className="flex items-start justify-between">
            <div>
              <div className="text-sm text-muted-foreground">Function</div>
              <div className="flex items-center gap-2 mt-1">
                <code className="font-mono font-medium">{id || "—"}</code>
                <span className="text-muted-foreground">·</span>
                <span>{name || "—"}</span>
              </div>
            </div>
            {id && name && <Check className="h-5 w-5 text-green-500" />}
          </div>

          {/* Type and Trigger */}
          <div className="flex items-center gap-6 pt-4 border-t">
            <div className="flex items-center gap-2">
              <ModeIcon className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">
                {mode === "inline" ? "AI Agent" : "Worker"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <TriggerIcon className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">{TRIGGER_LABELS[triggerType].label}</span>
              <Badge variant="secondary" className="text-xs font-mono">
                {triggerValue || "—"}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Mode-specific details */}
      {mode === "inline" ? (
        <>
          {/* Model */}
          <div className="space-y-2">
            <div className="text-sm font-medium">Model</div>
            <Card className="bg-muted/30">
              <CardContent className="p-3">
                <code className="text-sm font-mono">{model}</code>
              </CardContent>
            </Card>
          </div>

          {/* Instructions preview */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              Instructions
            </div>
            <Card className="bg-muted/30">
              <CardContent className="p-3">
                <p className="text-sm text-muted-foreground line-clamp-4 whitespace-pre-wrap">
                  {systemPrompt || "No instructions provided"}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Tools */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Wrench className="h-4 w-4 text-muted-foreground" />
                Tools
              </div>
              <Badge variant="secondary" className="text-xs">
                {selectedTools.length} selected
              </Badge>
            </div>
            {selectedTools.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {selectedToolObjects.map((tool) => (
                  <Badge key={tool.name} variant="outline" className="font-mono text-xs">
                    {tool.name}
                  </Badge>
                ))}
              </div>
            ) : (
              <Card className="bg-muted/30">
                <CardContent className="p-3 text-sm text-muted-foreground">
                  No tools selected. AI will only respond with text.
                </CardContent>
              </Card>
            )}
          </div>
        </>
      ) : (
        /* Worker details */
        <div className="space-y-2">
          <div className="text-sm font-medium">Endpoint URL</div>
          <Card className="bg-muted/30">
            <CardContent className="p-3">
              <code className="text-sm font-mono break-all">
                {endpointUrl || "—"}
              </code>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Ready indicator */}
      <Card className="bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900">
        <CardContent className="p-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
            <Check className="h-5 w-5 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <div className="font-medium text-green-900 dark:text-green-100">
              Ready to create
            </div>
            <p className="text-sm text-green-800 dark:text-green-200">
              Your function configuration is complete. Click &quot;Create Function&quot; to finish.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
