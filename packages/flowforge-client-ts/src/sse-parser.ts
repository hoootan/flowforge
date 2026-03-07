/**
 * Minimal SSE parser for ReadableStream.
 * Works in Node.js 18+ and browsers — no dependencies.
 */

export interface SSEEvent {
  event: string;
  data: string;
}

/**
 * Parse an SSE stream from a ReadableStream<Uint8Array>.
 * Yields SSEEvent objects for each complete event block.
 * Skips comment lines (starting with `:`) and keepalives.
 */
export async function* parseSSEStream(
  body: ReadableStream<Uint8Array>
): AsyncGenerator<SSEEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventType = "";
  const dataLines: string[] = [];

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep the last potentially incomplete line in the buffer
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        // Comment / keepalive
        if (line.startsWith(":")) {
          continue;
        }

        // Blank line = dispatch event
        if (line === "") {
          if (eventType && dataLines.length > 0) {
            yield { event: eventType, data: dataLines.join("\n") };
          }
          eventType = "";
          dataLines.length = 0;
          continue;
        }

        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }
    }

    // Flush any remaining event in buffer
    if (eventType && dataLines.length > 0) {
      yield { event: eventType, data: dataLines.join("\n") };
    }
  } finally {
    reader.releaseLock();
  }
}
