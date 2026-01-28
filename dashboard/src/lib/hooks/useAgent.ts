"use client";

import { useState, useEffect, useCallback } from "react";
import { api, RunWithSteps, PendingApproval } from "@/lib/api";

/**
 * Hook to fetch a run with agent details
 */
export function useAgentRun(runId: string | null) {
  const [run, setRun] = useState<RunWithSteps | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRun = useCallback(async () => {
    if (!runId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await api.getRun(runId);
      setRun(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch run");
      setRun(null);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchRun();
  }, [fetchRun]);

  return { run, loading, error, refetch: fetchRun };
}

/**
 * Hook to fetch pending approvals
 */
export function useApprovals(pendingOnly: boolean = true) {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApprovals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getApprovals({ pending_only: pendingOnly });
      setApprovals(data.approvals);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch approvals");
      setApprovals([]);
    } finally {
      setLoading(false);
    }
  }, [pendingOnly]);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  return { approvals, loading, error, refetch: fetchApprovals };
}

/**
 * Hook to approve a tool call
 */
export function useApproveToolCall() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const approve = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.approveToolCall(id);
      if (!result?.success) {
        throw new Error(result?.message || "Failed to approve");
      }
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to approve tool call";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { approve, loading, error };
}

/**
 * Hook to reject a tool call
 */
export function useRejectToolCall() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reject = useCallback(async (id: string, reason: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.rejectToolCall(id, reason);
      if (!result?.success) {
        throw new Error(result?.message || "Failed to reject");
      }
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to reject tool call";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { reject, loading, error };
}

/**
 * Helper to check if a run contains agent steps
 */
export function hasAgentSteps(run: RunWithSteps | null): boolean {
  if (!run) return false;
  return run.steps.some((step) => step.step_type === "agent");
}

/**
 * Helper to extract agent result from a step
 */
export function extractAgentResult(run: RunWithSteps | null) {
  if (!run) return null;

  const agentStep = run.steps.find((step) => step.step_type === "agent");
  if (!agentStep || !agentStep.output) return null;

  // Agent output is stored in the step's output field
  return agentStep.output as any;
}
