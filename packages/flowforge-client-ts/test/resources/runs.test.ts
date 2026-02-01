import { describe, it, expect, vi, beforeEach } from "vitest";
import { createClient } from "../../src/client";
import type { FlowForgeClient } from "../../src/client";

describe("RunsResource", () => {
  let mockFetch: ReturnType<typeof vi.fn>;
  let client: FlowForgeClient;

  beforeEach(() => {
    mockFetch = vi.fn();
    client = createClient("http://localhost:8000", {
      fetch: mockFetch,
      retry: { maxAttempts: 1 },
    });
  });

  describe("list", () => {
    it("should list runs with default parameters", async () => {
      const runsResponse = {
        runs: [
          { id: "run-1", status: "completed" },
          { id: "run-2", status: "running" },
        ],
        total: 2,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => runsResponse,
      });

      const result = await client.runs.list();

      expect(result.data).toEqual(runsResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/runs"),
        expect.objectContaining({ method: "GET" })
      );
    });

    it("should filter runs by status", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ runs: [], total: 0 }),
      });

      await client.runs.list({ status: "failed" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("status=failed"),
        expect.any(Object)
      );
    });

    it("should filter runs by function_id", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ runs: [], total: 0 }),
      });

      await client.runs.list({ function_id: "my-function" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("function_id=my-function"),
        expect.any(Object)
      );
    });
  });

  describe("get", () => {
    it("should get a single run by ID", async () => {
      const run = {
        id: "run-123",
        function_id: "my-function",
        status: "completed",
        output: { result: "success" },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => run,
      });

      const result = await client.runs.get("run-123");

      expect(result.data).toEqual(run);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/runs/run-123",
        expect.objectContaining({ method: "GET" })
      );
    });

    it("should handle 404 errors", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: "Run not found" }),
      });

      const result = await client.runs.get("nonexistent");

      expect(result.data).toBeNull();
      expect(result.error?.status).toBe(404);
    });
  });

  describe("cancel", () => {
    it("should cancel a running run", async () => {
      const cancelledRun = {
        id: "run-123",
        status: "cancelled",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => cancelledRun,
      });

      const result = await client.runs.cancel("run-123");

      expect(result.data).toEqual(cancelledRun);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/runs/run-123/cancel",
        expect.objectContaining({ method: "POST" })
      );
    });
  });

  describe("retry", () => {
    it("should retry a failed run", async () => {
      const newRun = {
        id: "run-456",
        status: "pending",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => newRun,
      });

      const result = await client.runs.retry("run-123");

      expect(result.data).toEqual(newRun);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/runs/run-123/retry",
        expect.objectContaining({ method: "POST" })
      );
    });
  });

  describe("getSteps", () => {
    it("should get steps for a run", async () => {
      const steps = [
        { id: "step-1", step_id: "process", status: "completed" },
        { id: "step-2", step_id: "notify", status: "pending" },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => steps,
      });

      const result = await client.runs.getSteps("run-123");

      expect(result.data).toEqual(steps);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/runs/run-123/steps",
        expect.objectContaining({ method: "GET" })
      );
    });
  });
});
