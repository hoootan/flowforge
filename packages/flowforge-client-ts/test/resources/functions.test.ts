import { describe, it, expect, vi, beforeEach } from "vitest";
import { createClient } from "../../src/client";
import type { FlowForgeClient } from "../../src/client";

describe("FunctionsResource", () => {
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
    it("should list functions", async () => {
      const functionsResponse = {
        functions: [
          { id: "fn-1", name: "Process Order", trigger_type: "event" },
          { id: "fn-2", name: "Send Notification", trigger_type: "event" },
        ],
        total: 2,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => functionsResponse,
      });

      const result = await client.functions.list();

      expect(result.data).toEqual(functionsResponse);
    });

    it("should filter by trigger_type", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ functions: [], total: 0 }),
      });

      await client.functions.list({ trigger_type: "cron" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("trigger_type=cron"),
        expect.any(Object)
      );
    });
  });

  describe("get", () => {
    it("should get a function by ID", async () => {
      const fn = {
        id: "fn-123",
        function_id: "process-order",
        name: "Process Order",
        trigger_type: "event",
        trigger_value: "order/created",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => fn,
      });

      const result = await client.functions.get("process-order");

      expect(result.data).toEqual(fn);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/functions/process-order",
        expect.any(Object)
      );
    });
  });

  describe("create", () => {
    it("should create a new function", async () => {
      const newFn = {
        id: "process-order",
        name: "Process Order",
        trigger_type: "event",
        trigger_value: "order/created",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => newFn,
      });

      const result = await client.functions.create({
        id: "process-order",
        name: "Process Order",
        trigger_type: "event",
        trigger_value: "order/created",
      });

      expect(result.data).toEqual(newFn);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/functions",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("process-order"),
        })
      );
    });
  });

  describe("update", () => {
    it("should update an existing function", async () => {
      const updatedFn = {
        id: "fn-123",
        name: "Updated Name",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => updatedFn,
      });

      const result = await client.functions.update("process-order", {
        name: "Updated Name",
      });

      expect(result.data).toEqual(updatedFn);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/functions/process-order",
        expect.objectContaining({
          method: "PUT",
        })
      );
    });
  });

  describe("delete", () => {
    it("should delete a function", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const result = await client.functions.delete("process-order");

      expect(result.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/functions/process-order",
        expect.objectContaining({
          method: "DELETE",
        })
      );
    });
  });
});
