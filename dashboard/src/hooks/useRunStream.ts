"use client";

import { useState, useEffect, useCallback, useRef } from "react";

export type RunEventType =
  | "step_started"
  | "step_completed"
  | "step_failed"
  | "thinking"
  | "thinking_chunk"
  | "tool_call_started"
  | "tool_call_completed"
  | "approval_required"
  | "approval_resolved"
  | "run_started"
  | "run_paused"
  | "run_resumed"
  | "run_completed"
  | "run_failed";

export interface RunEvent {
  type: RunEventType;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface ThinkingChunk {
  content: string;
  stepId: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  status: "started" | "completed" | "failed";
}

export interface UseRunStreamOptions {
  runId: string;
  enabled?: boolean;
  onEvent?: (event: RunEvent) => void;
  onComplete?: () => void;
  onError?: (error: Error) => void;
}

export interface UseRunStreamResult {
  isConnected: boolean;
  isComplete: boolean;
  thinkingContent: string;
  toolCalls: ToolCall[];
  events: RunEvent[];
  error: Error | null;
  reconnect: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useRunStream({
  runId,
  enabled = true,
  onEvent,
  onComplete,
  onError,
}: UseRunStreamOptions): UseRunStreamResult {
  const [isConnected, setIsConnected] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [thinkingContent, setThinkingContent] = useState("");
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const handleEvent = useCallback(
    (eventType: RunEventType, data: Record<string, unknown>) => {
      const event: RunEvent = {
        type: eventType,
        data,
        timestamp: new Date().toISOString(),
      };

      setEvents((prev) => [...prev, event]);
      onEvent?.(event);

      switch (eventType) {
        case "thinking_chunk":
          setThinkingContent((prev) => prev + (data.chunk as string || ""));
          break;

        case "thinking":
          // Reset thinking content on new thinking step
          if (data.status === "calling_llm") {
            setThinkingContent("");
          }
          break;

        case "tool_call_started":
          setToolCalls((prev) => [
            ...prev,
            {
              id: data.tool_call_id as string,
              name: data.tool_name as string,
              arguments: data.arguments as Record<string, unknown>,
              status: "started",
            },
          ]);
          break;

        case "tool_call_completed":
          setToolCalls((prev) =>
            prev.map((tc) =>
              tc.id === data.tool_call_id
                ? { ...tc, result: data.result as string, status: "completed" }
                : tc
            )
          );
          break;

        case "run_completed":
        case "run_failed":
          setIsComplete(true);
          onComplete?.();
          break;
      }
    },
    [onEvent, onComplete]
  );

  const connect = useCallback(() => {
    if (!enabled || !runId) return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setError(null);
    setIsComplete(false);

    const url = `${API_BASE_URL}/api/v1/runs/${runId}/stream`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onerror = (e) => {
      setIsConnected(false);
      const err = new Error("SSE connection failed");
      setError(err);
      onError?.(err);
    };

    // Handle specific event types
    const eventTypes: RunEventType[] = [
      "step_started",
      "step_completed",
      "step_failed",
      "thinking",
      "thinking_chunk",
      "tool_call_started",
      "tool_call_completed",
      "approval_required",
      "approval_resolved",
      "run_started",
      "run_paused",
      "run_resumed",
      "run_completed",
      "run_failed",
    ];

    eventTypes.forEach((type) => {
      eventSource.addEventListener(type, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          handleEvent(type, data);
        } catch (err) {
          console.error(`Failed to parse ${type} event:`, err);
        }
      });
    });

    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [runId, enabled, handleEvent, onError]);

  useEffect(() => {
    const cleanup = connect();
    return () => {
      cleanup?.();
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connect]);

  const reconnect = useCallback(() => {
    setEvents([]);
    setThinkingContent("");
    setToolCalls([]);
    connect();
  }, [connect]);

  return {
    isConnected,
    isComplete,
    thinkingContent,
    toolCalls,
    events,
    error,
    reconnect,
  };
}
