'use client';

import React, { useEffect, useRef } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Brain, Wrench, CheckCircle, XCircle, Loader2, Bot, Eye } from 'lucide-react';
import type { RunEvent, ToolCall } from '@/hooks/useRunStream';

interface LiveActivityPanelProps {
  isConnected: boolean;
  isComplete: boolean;
  thinkingContent: string;
  toolCalls: ToolCall[];
  events: RunEvent[];
}

function ThinkingBubble({ content }: { content: string }) {
  return (
    <div className="bg-muted/50 rounded-lg p-3 border border-dashed border-muted-foreground/20">
      <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
        <Brain className="h-3 w-3 animate-pulse" />
        <span>Thinking...</span>
      </div>
      <p className="text-sm whitespace-pre-wrap font-mono text-xs leading-relaxed max-h-32 overflow-y-auto">
        {content || 'Processing...'}
      </p>
    </div>
  );
}

function ToolCallEntry({ toolCall }: { toolCall: ToolCall }) {
  const statusIcon = {
    started: <Loader2 className="h-3 w-3 animate-spin text-blue-500" />,
    completed: <CheckCircle className="h-3 w-3 text-green-500" />,
    failed: <XCircle className="h-3 w-3 text-red-500" />,
  }[toolCall.status];

  return (
    <div className="bg-background border rounded-lg p-3 space-y-1">
      <div className="flex items-center gap-2">
        <Wrench className="h-3 w-3 text-muted-foreground" />
        <span className="text-xs font-mono font-medium">{toolCall.name}</span>
        {statusIcon}
      </div>
      {toolCall.arguments && Object.keys(toolCall.arguments).length > 0 && (
        <pre className="text-xs text-muted-foreground font-mono overflow-x-auto max-h-16 overflow-y-auto">
          {JSON.stringify(toolCall.arguments, null, 2).slice(0, 200)}
        </pre>
      )}
      {toolCall.result && (
        <div className="text-xs text-green-600 dark:text-green-400 font-mono truncate">
          {String(toolCall.result).slice(0, 100)}
        </div>
      )}
    </div>
  );
}

function EventEntry({ event }: { event: RunEvent }) {
  const icons: Record<string, React.ReactNode> = {
    step_started: <Loader2 className="h-3 w-3 text-blue-500" />,
    step_completed: <CheckCircle className="h-3 w-3 text-green-500" />,
    step_failed: <XCircle className="h-3 w-3 text-red-500" />,
    run_started: <Bot className="h-3 w-3 text-blue-500" />,
    run_completed: <CheckCircle className="h-3 w-3 text-green-500" />,
    run_failed: <XCircle className="h-3 w-3 text-red-500" />,
    approval_required: <Eye className="h-3 w-3 text-yellow-500" />,
  };

  // Skip thinking events (shown separately)
  if (event.type === 'thinking_chunk' || event.type === 'thinking') return null;
  // Skip tool events (shown separately)
  if (event.type === 'tool_call_started' || event.type === 'tool_call_completed') return null;

  const time = new Date(event.timestamp).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  return (
    <div className="flex items-start gap-2 py-1">
      <span className="mt-0.5">{icons[event.type] || <Bot className="h-3 w-3" />}</span>
      <div className="flex-1 min-w-0">
        <span className="text-xs">{event.type.replace(/_/g, ' ')}</span>
        {typeof event.data?.step_id === 'string' && (
          <span className="text-xs text-muted-foreground ml-1 font-mono">
            ({event.data.step_id.slice(0, 20)})
          </span>
        )}
      </div>
      <span className="text-xs text-muted-foreground shrink-0">{time}</span>
    </div>
  );
}

export function LiveActivityPanel({
  isConnected,
  isComplete,
  thinkingContent,
  toolCalls,
  events,
}: LiveActivityPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length, thinkingContent, toolCalls.length]);

  const recentToolCalls = toolCalls.slice(-5);
  const significantEvents = events.filter(
    e => !['thinking_chunk', 'thinking', 'tool_call_started', 'tool_call_completed'].includes(e.type)
  );

  return (
    <Card className="sticky top-4">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Bot className="h-4 w-4" />
            Live Activity
          </CardTitle>
          <Badge
            variant={isComplete ? 'secondary' : isConnected ? 'default' : 'destructive'}
            className="text-xs"
          >
            {isComplete ? 'Complete' : isConnected ? 'Live' : 'Disconnected'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-[400px] overflow-y-auto" ref={scrollRef}>
          <div className="space-y-3 pr-3">
            {/* Active thinking */}
            {!isComplete && thinkingContent && (
              <ThinkingBubble content={thinkingContent} />
            )}

            {/* Recent tool calls */}
            {recentToolCalls.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Tool Calls
                </h4>
                {recentToolCalls.map(tc => (
                  <ToolCallEntry key={tc.id} toolCall={tc} />
                ))}
              </div>
            )}

            {/* Event log */}
            {significantEvents.length > 0 && (
              <div className="space-y-1">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Activity Log
                </h4>
                {significantEvents.slice(-20).map((event, i) => (
                  <EventEntry key={i} event={event} />
                ))}
              </div>
            )}

            {events.length === 0 && !thinkingContent && (
              <div className="text-center py-8 text-sm text-muted-foreground">
                {isConnected ? 'Waiting for activity...' : 'Connecting...'}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
