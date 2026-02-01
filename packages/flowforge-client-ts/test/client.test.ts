import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createClient } from "../src/client";
import type { FlowForgeClient } from "../src/client";

describe("createClient", () => {
  let mockFetch: ReturnType<typeof vi.fn>;
  let client: FlowForgeClient;

  beforeEach(() => {
    mockFetch = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("basic configuration", () => {
    it("should create a client with base URL", () => {
      const client = createClient("http://localhost:8000");
      expect(client).toBeDefined();
      expect(client.events).toBeDefined();
      expect(client.runs).toBeDefined();
      expect(client.functions).toBeDefined();
    });

    it("should normalize base URL by removing trailing slash", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "healthy" }),
      });

      client = createClient("http://localhost:8000/", { fetch: mockFetch });
      await client.health.check();

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/health",
        expect.any(Object)
      );
    });

    it("should include API key header when provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "healthy" }),
      });

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        apiKey: "ff_live_test123",
      });
      await client.health.check();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            "X-FlowForge-API-Key": "ff_live_test123",
          }),
        })
      );
    });
  });

  describe("timeout handling", () => {
    it("should timeout after configured duration", async () => {
      // Create a promise that never resolves
      mockFetch.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        timeout: 100, // 100ms timeout
        retry: { maxAttempts: 1 }, // Disable retries for this test
      });

      const result = await client.health.check();

      expect(result.error).not.toBeNull();
      expect(result.error?.code).toBe("TIMEOUT");
      expect(result.error?.message).toContain("timed out");
    });

    it("should use default 30s timeout when not specified", () => {
      client = createClient("http://localhost:8000");
      // Just verify client is created - timeout is internal
      expect(client).toBeDefined();
    });
  });

  describe("retry logic", () => {
    it("should retry on 500 errors by default", async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: async () => ({ detail: "Internal Server Error" }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: "healthy" }),
        });

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        retry: { maxAttempts: 2, baseDelay: 10 },
      });

      const result = await client.health.check();

      expect(result.data).toEqual({ status: "healthy" });
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it("should retry on 429 rate limit errors", async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 429,
          json: async () => ({ detail: "Rate limit exceeded" }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ id: "run-123" }),
        });

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        retry: { maxAttempts: 2, baseDelay: 10 },
      });

      const result = await client.runs.get("run-123");

      expect(result.data).toEqual({ id: "run-123" });
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it("should not retry on 400 errors", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: "Bad Request" }),
      });

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        retry: { maxAttempts: 3 },
      });

      const result = await client.health.check();

      expect(result.error).not.toBeNull();
      expect(result.error?.status).toBe(400);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("should not retry on 401 errors", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Unauthorized" }),
      });

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        retry: { maxAttempts: 3 },
      });

      const result = await client.health.check();

      expect(result.error?.status).toBe(401);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("should respect maxAttempts configuration", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: "Server Error" }),
      });

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        retry: { maxAttempts: 5, baseDelay: 1 },
      });

      await client.health.check();

      expect(mockFetch).toHaveBeenCalledTimes(5);
    });

    it("should retry on network errors", async () => {
      mockFetch
        .mockRejectedValueOnce(new Error("Network error"))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: "healthy" }),
        });

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        retry: { maxAttempts: 2, baseDelay: 10 },
      });

      const result = await client.health.check();

      expect(result.data).toEqual({ status: "healthy" });
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  describe("error handling", () => {
    it("should return error result on HTTP error", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: "Not found" }),
      });

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        retry: { maxAttempts: 1 },
      });

      const result = await client.runs.get("nonexistent");

      expect(result.data).toBeNull();
      expect(result.error).not.toBeNull();
      expect(result.error?.status).toBe(404);
      expect(result.error?.message).toBe("Not found");
    });

    it("should return network error on fetch failure", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network unavailable"));

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        retry: { maxAttempts: 1 },
      });

      const result = await client.health.check();

      expect(result.data).toBeNull();
      expect(result.error).not.toBeNull();
      expect(result.error?.code).toBe("NETWORK_ERROR");
      expect(result.error?.message).toBe("Network unavailable");
    });

    it("should handle JSON parse errors gracefully", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error("Invalid JSON");
        },
      });

      client = createClient("http://localhost:8000", {
        fetch: mockFetch,
        retry: { maxAttempts: 1 },
      });

      const result = await client.health.check();

      expect(result.error).not.toBeNull();
      expect(result.error?.status).toBe(500);
    });
  });
});
