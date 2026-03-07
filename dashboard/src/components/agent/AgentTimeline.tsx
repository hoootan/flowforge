"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Bot, Brain, ChevronDown, ChevronRight, Wrench } from "lucide-react";
import { ToolCallDetail } from "./ToolCallDetail";
import { SubAgentCard } from "./SubAgentCard";

interface AgentTimelineProps {
  agentResult: {
    iterations: number;
    messages: any[];
    tool_calls: any[];
  };
}

interface IterationData {
  iteration: number;
  thinking?: {
    content: string;
    model?: string;
    tokens?: number;
  };
  toolCalls: any[];
}

function parseIterations(messages: any[], toolCalls: any[]): IterationData[] {
  const iterations: IterationData[] = [];
  let currentIteration = 0;

  // Group tool calls by iteration
  const toolCallsByIteration = new Map<number, any[]>();
  toolCalls.forEach((tc) => {
    const iter = tc.iteration || 0;
    if (!toolCallsByIteration.has(iter)) {
      toolCallsByIteration.set(iter, []);
    }
    toolCallsByIteration.get(iter)?.push(tc);
  });

  // Process messages to extract iterations
  let lastAssistantMessage = null;
  for (const msg of messages) {
    if (msg.role === "assistant") {
      if (lastAssistantMessage) {
        // Previous iteration complete
        const iterToolCalls = toolCallsByIteration.get(currentIteration) || [];
        iterations.push({
          iteration: currentIteration,
          thinking: {
            content: lastAssistantMessage.content || "",
            model: lastAssistantMessage.model,
            tokens: lastAssistantMessage.tokens,
          },
          toolCalls: iterToolCalls,
        });
        currentIteration++;
      }
      lastAssistantMessage = msg;
    }
  }

  // Add final iteration
  if (lastAssistantMessage) {
    const iterToolCalls = toolCallsByIteration.get(currentIteration) || [];
    iterations.push({
      iteration: currentIteration,
      thinking: {
        content: lastAssistantMessage.content || "",
        model: lastAssistantMessage.model,
        tokens: lastAssistantMessage.tokens,
      },
      toolCalls: iterToolCalls,
    });
  }

  return iterations;
}

function IterationCard({ data }: { data: IterationData }) {
  const [expanded, setExpanded] = useState(false);
  const hasToolCalls = data.toolCalls.length > 0;

  return (
    <div className="relative">
      {/* Timeline connector */}
      <div className="absolute left-5 top-12 bottom-0 w-0.5 bg-border" />

      <Card className="relative">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-primary bg-background">
                <span className="text-sm font-semibold">{data.iteration + 1}</span>
              </div>
              <div>
                <CardTitle className="text-base">Iteration {data.iteration + 1}</CardTitle>
                <CardDescription className="text-xs">
                  {hasToolCalls
                    ? `${data.toolCalls.length} tool call${data.toolCalls.length !== 1 ? "s" : ""}`
                    : "Final response"}
                </CardDescription>
              </div>
            </div>
            {hasToolCalls && (
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
            )}
          </div>
        </CardHeader>

        {/* Thinking content */}
        {data.thinking && data.thinking.content && (
          <CardContent className="pt-0">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium text-muted-foreground">Thinking</span>
                {data.thinking.tokens && (
                  <Badge variant="outline" className="text-xs">
                    {data.thinking.tokens} tokens
                  </Badge>
                )}
              </div>
              <div className="rounded-lg border bg-muted/50 p-3">
                <p className="text-sm whitespace-pre-wrap">{data.thinking.content}</p>
              </div>
            </div>
          </CardContent>
        )}

        {/* Tool calls - expandable */}
        {hasToolCalls && expanded && (
          <CardContent className="pt-4 border-t">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Wrench className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Tool Calls</span>
              </div>
              <div className="space-y-3">
                {data.toolCalls.map((toolCall, idx) =>
                  toolCall.is_sub_agent || toolCall.sub_agent_result ? (
                    <SubAgentCard key={toolCall.id || idx} toolCall={toolCall} />
                  ) : (
                    <ToolCallDetail key={toolCall.id || idx} toolCall={toolCall} />
                  )
                )}
              </div>
            </div>
          </CardContent>
        )}

        {/* Tool calls preview when collapsed */}
        {hasToolCalls && !expanded && (
          <CardContent className="pt-0">
            <div className="flex flex-wrap gap-2">
              {data.toolCalls.map((tc, idx) => (
                <Badge
                  key={idx}
                  variant={tc.is_sub_agent || tc.sub_agent_result ? "secondary" : "outline"}
                  className="gap-1"
                >
                  {tc.is_sub_agent || tc.sub_agent_result ? (
                    <Bot className="h-3 w-3" />
                  ) : (
                    <Wrench className="h-3 w-3" />
                  )}
                  {tc.tool_name}
                  {tc.requires_approval && (
                    <span className="ml-1 text-yellow-600">*</span>
                  )}
                </Badge>
              ))}
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
}

export function AgentTimeline({ agentResult }: AgentTimelineProps) {
  const iterations = parseIterations(agentResult.messages, agentResult.tool_calls);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Timeline</CardTitle>
        <CardDescription>
          Iteration-by-iteration breakdown of agent execution
        </CardDescription>
      </CardHeader>
      <CardContent>
        {iterations.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">No iterations recorded.</p>
        ) : (
          <div className="space-y-6">
            {iterations.map((iter) => (
              <IterationCard key={iter.iteration} data={iter} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
