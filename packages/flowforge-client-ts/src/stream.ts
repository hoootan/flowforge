/**
 * RunStream — SSE stream wrapper for FlowForge run events.
 */

import { parseSSEStream } from "./sse-parser";
import {
  FlowForgeError,
  type RunEventType,
  type RunStreamEvent,
  type StreamConfig,
  type StreamOptions,
} from "./types";

const TERMINAL_EVENTS: Set<RunEventType> = new Set([
  "run_completed",
  "run_failed",
]);

export class RunStream {
  private abortController: AbortController;
  private iteratorStarted = false;
  private closed = false;

  constructor(
    private runId: string,
    private config: StreamConfig,
    private options: StreamOptions = {}
  ) {
    this.abortController = new AbortController();
  }

  /**
   * Async iterator — use with `for await...of`.
   */
  async *[Symbol.asyncIterator](): AsyncGenerator<RunStreamEvent> {
    if (this.iteratorStarted) {
      throw new FlowForgeError("Stream already consumed", 0, "STREAM_CONSUMED");
    }
    this.iteratorStarted = true;

    const includeHistory = this.options.includeHistory ?? true;
    const timeout = this.options.timeout ?? 300;

    const params = new URLSearchParams({
      include_history: String(includeHistory),
      timeout: String(timeout),
    });

    const url = `${this.config.baseUrl}/api/v1/runs/${this.runId}/stream?${params}`;

    const headers: Record<string, string> = {
      Accept: "text/event-stream",
    };
    if (this.config.apiKey) {
      headers["X-FlowForge-API-Key"] = this.config.apiKey;
    }

    // Combine external signal with our own abort controller
    const signals: AbortSignal[] = [this.abortController.signal];
    if (this.options.signal) {
      signals.push(this.options.signal);
    }

    let response: Response;
    try {
      response = await this.config.fetchFn(url, {
        method: "GET",
        headers,
        signal:
          signals.length === 1
            ? signals[0]
            : anySignal(signals),
      });
    } catch (err) {
      const error = new FlowForgeError(
        err instanceof Error ? err.message : "Stream connection failed",
        0,
        "STREAM_ERROR"
      );
      this.options.onError?.(error);
      throw error;
    }

    if (!response.ok) {
      const body = await response.text().catch(() => "");
      const error = new FlowForgeError(
        body || `HTTP ${response.status}`,
        response.status,
        "STREAM_HTTP_ERROR"
      );
      this.options.onError?.(error);
      throw error;
    }

    if (!response.body) {
      const error = new FlowForgeError(
        "Response body is empty",
        0,
        "STREAM_EMPTY"
      );
      this.options.onError?.(error);
      throw error;
    }

    try {
      for await (const sse of parseSSEStream(response.body)) {
        if (this.closed) return;

        let data: Record<string, unknown>;
        try {
          data = JSON.parse(sse.data);
        } catch {
          continue;
        }

        const event: RunStreamEvent = {
          type: sse.event as RunEventType,
          data,
          runId: this.runId,
          timestamp:
            (data.timestamp as string) ??
            (data.ts as string) ??
            new Date().toISOString(),
        };

        this.options.onEvent?.(event);
        yield event;

        if (TERMINAL_EVENTS.has(event.type)) {
          this.options.onComplete?.(event);
          return;
        }
      }
    } catch (err) {
      if (this.closed) return;
      const error = new FlowForgeError(
        err instanceof Error ? err.message : "Stream error",
        0,
        "STREAM_ERROR"
      );
      this.options.onError?.(error);
      throw error;
    }
  }

  /**
   * Consume the entire stream via callbacks. Returns the terminal event or null.
   */
  async drain(): Promise<RunStreamEvent | null> {
    let last: RunStreamEvent | null = null;
    for await (const event of this) {
      last = event;
    }
    return last;
  }

  /**
   * Collect all events into an array.
   */
  async collect(): Promise<RunStreamEvent[]> {
    const events: RunStreamEvent[] = [];
    for await (const event of this) {
      events.push(event);
    }
    return events;
  }

  /**
   * Cancel the stream.
   */
  close(): void {
    this.closed = true;
    this.abortController.abort();
  }
}

/**
 * Combine multiple AbortSignals into one.
 */
function anySignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();

  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort(signal.reason);
      return controller.signal;
    }
    signal.addEventListener("abort", () => controller.abort(signal.reason), {
      once: true,
    });
  }

  return controller.signal;
}
