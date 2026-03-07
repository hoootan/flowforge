"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Bot, ChevronDown, ChevronRight, Wrench } from "lucide-react";

interface SubAgentCardProps {
  toolCall: {
    id: string;
    tool_name: string;
    arguments: Record<string, unknown>;
    result?: string;
    is_sub_agent?: boolean;
    sub_agent_result?: {
      result?: string;
      iterations?: number;
      tool_calls_count?: number;
      tokens_used?: Record<string, number>;
      tool_calls?: Array<{
        id: string;
        tool_name: string;
        arguments: Record<string, unknown>;
        result?: string;
        iteration?: number;
      }>;
    };
  };
}

export function SubAgentCard({ toolCall }: SubAgentCardProps) {
  const [expanded, setExpanded] = useState(false);
  const subResult = toolCall.sub_agent_result;
  const task = (toolCall.arguments?.task as string) || "No task specified";

  return (
    <Card className="border-dashed border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-primary/50 bg-primary/10">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div>
              <CardTitle className="text-sm flex items-center gap-2">
                Sub-Agent: {toolCall.tool_name}
                <Badge variant="secondary" className="text-xs">
                  delegated
                </Badge>
              </CardTitle>
              <CardDescription className="text-xs mt-0.5 line-clamp-1">
                {task}
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {subResult && (
              <div className="flex gap-1.5 text-xs text-muted-foreground">
                {subResult.iterations !== undefined && (
                  <span>{subResult.iterations} iter</span>
                )}
                {subResult.tool_calls_count !== undefined && (
                  <>
                    <span>&middot;</span>
                    <span>{subResult.tool_calls_count} tools</span>
                  </>
                )}
                {subResult.tokens_used?.total !== undefined && (
                  <>
                    <span>&middot;</span>
                    <span>{subResult.tokens_used.total} tokens</span>
                  </>
                )}
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0 space-y-3">
          {/* Task */}
          <div>
            <span className="text-xs font-medium text-muted-foreground">Task</span>
            <div className="mt-1 rounded border bg-muted/50 p-2">
              <p className="text-sm whitespace-pre-wrap">{task}</p>
            </div>
          </div>

          {/* Sub-agent tool calls */}
          {subResult?.tool_calls && subResult.tool_calls.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Wrench className="h-3 w-3 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground">
                  Sub-Agent Tool Calls ({subResult.tool_calls.length})
                </span>
              </div>
              <div className="space-y-2 pl-4 border-l-2 border-primary/20">
                {subResult.tool_calls.map((tc, idx) => (
                  <div key={tc.id || idx} className="rounded border bg-background p-2">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className="text-xs gap-1">
                        <Wrench className="h-3 w-3" />
                        {tc.tool_name}
                      </Badge>
                      {tc.iteration !== undefined && (
                        <span className="text-xs text-muted-foreground">
                          iter {tc.iteration}
                        </span>
                      )}
                    </div>
                    {tc.result && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-3">
                        {tc.result}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Result */}
          {toolCall.result && (
            <div>
              <span className="text-xs font-medium text-muted-foreground">Result</span>
              <div className="mt-1 rounded border bg-muted/50 p-2">
                <p className="text-sm whitespace-pre-wrap line-clamp-10">{toolCall.result}</p>
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
