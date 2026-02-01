import { describe, it, expect, vi, beforeEach } from "vitest";
import { createClient } from "../../src/client";
import type { FlowForgeClient } from "../../src/client";

describe("EventsResource", () => {
  let mockFetch: ReturnType<typeof vi.fn>;
  let client: FlowForgeClient;

  beforeEach(() => {
    mockFetch = vi.fn();
    client = createClient("http://localhost:8000", {
      fetch: mockFetch,
      retry: { maxAttempts: 1 },
    });
  });

  describe("send", () => {
    it("should send an event with name and data", async () => {
      const eventResponse = {
        id: "evt-123",
        event_id: "evt-123",
        name: "order/created",
        data: { order_id: "123" },
        timestamp: "2024-01-01T00:00:00Z",
        received_at: "2024-01-01T00:00:00Z",
        user_id: null,
        processed: false,
        runs: [{ id: "run-1", function_id: "process-order" }],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => eventResponse,
      });

      const result = await client.events.send("order/created", { order_id: "123" });

      expect(result.data).toEqual(eventResponse);
      expect(result.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/events",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            name: "order/created",
            data: { order_id: "123" },
          }),
        })
      );
    });

    it("should include optional id and user_id", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "custom-id" }),
      });

      await client.events.send("test/event", { value: 1 }, {
        id: "custom-id",
        user_id: "user-123",
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({
            name: "test/event",
            data: { value: 1 },
            id: "custom-id",
            user_id: "user-123",
          }),
        })
      );
    });

    it("should handle send errors", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: "Invalid event data" }),
      });

      const result = await client.events.send("invalid", {});

      expect(result.data).toBeNull();
      expect(result.error?.status).toBe(400);
      expect(result.error?.message).toBe("Invalid event data");
    });
  });

  describe("list", () => {
    it("should list events with default parameters", async () => {
      const eventsResponse = {
        events: [
          { id: "evt-1", name: "order/created" },
          { id: "evt-2", name: "order/updated" },
        ],
        total: 2,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => eventsResponse,
      });

      const result = await client.events.list();

      expect(result.data).toEqual(eventsResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/events?",
        expect.objectContaining({ method: "GET" })
      );
    });

    it("should apply filters to list request", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ events: [], total: 0 }),
      });

      await client.events.list({ name: "order/created" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("name=order%2Fcreated"),
        expect.any(Object)
      );
    });
  });

  describe("get", () => {
    it("should get a single event by ID", async () => {
      const event = {
        id: "evt-123",
        name: "order/created",
        data: { order_id: "123" },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => event,
      });

      const result = await client.events.get("evt-123");

      expect(result.data).toEqual(event);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/events/evt-123",
        expect.objectContaining({ method: "GET" })
      );
    });
  });
});
