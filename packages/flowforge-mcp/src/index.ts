import { createClient } from "flowforge-client";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import express from "express";
import { createMcpServer } from "./server.js";

function parseArgs(argv: string[]) {
  const args = argv.slice(2);
  const result: Record<string, string> = {};

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--help" || args[i] === "-h") {
      result.help = "true";
    } else if (args[i].startsWith("--") && i + 1 < args.length) {
      const key = args[i].slice(2);
      result[key] = args[++i];
    }
  }

  return result;
}

function printUsage() {
  console.log(`
flowforge-mcp — MCP server for FlowForge

Usage:
  flowforge-mcp [options]

Options:
  --server-url <url>    FlowForge server URL (env: FLOWFORGE_SERVER_URL, default: http://localhost:8000)
  --api-key <key>       FlowForge API key (env: FLOWFORGE_API_KEY)
  --transport <type>    Transport type: sse or stdio (default: sse)
  --port <number>       SSE server port (default: 3100)
  --help, -h            Show this help message

Examples:
  # Start SSE server (default)
  flowforge-mcp --server-url http://localhost:8000 --api-key ff_live_xxx

  # Start with stdio transport (for Claude Code process management)
  flowforge-mcp --transport stdio

  # Use environment variables
  FLOWFORGE_SERVER_URL=http://localhost:8000 FLOWFORGE_API_KEY=ff_live_xxx flowforge-mcp
`);
}

async function main() {
  const args = parseArgs(process.argv);

  if (args.help) {
    printUsage();
    process.exit(0);
  }

  const serverUrl =
    args["server-url"] ||
    process.env.FLOWFORGE_SERVER_URL ||
    "http://localhost:8000";
  const apiKey = args["api-key"] || process.env.FLOWFORGE_API_KEY;
  const transport = args.transport || "sse";
  const port = parseInt(args.port || "3100", 10);

  if (!apiKey) {
    console.warn(
      "Warning: No API key provided. Set --api-key or FLOWFORGE_API_KEY for authenticated access."
    );
  }

  const client = createClient(serverUrl, { apiKey });

  if (transport === "stdio") {
    const server = createMcpServer(client, { serverUrl, apiKey });
    const stdioTransport = new StdioServerTransport();
    await server.connect(stdioTransport);
    console.error("FlowForge MCP server running on stdio");
  } else if (transport === "sse") {
    const app = express();
    app.use(express.json());

    const sessions = new Map<
      string,
      { server: ReturnType<typeof createMcpServer>; transport: SSEServerTransport }
    >();

    app.get("/sse", async (req, res) => {
      const server = createMcpServer(client, { serverUrl, apiKey });
      const sseTransport = new SSEServerTransport("/messages", res);
      sessions.set(sseTransport.sessionId, {
        server,
        transport: sseTransport,
      });

      res.on("close", () => {
        sessions.delete(sseTransport.sessionId);
      });

      await server.connect(sseTransport);
    });

    app.post("/messages", async (req, res) => {
      const sessionId = req.query.sessionId as string;
      const session = sessions.get(sessionId);
      if (session) {
        await session.transport.handlePostMessage(req, res);
      } else {
        res.status(400).json({ error: "Unknown session" });
      }
    });

    app.get("/health", (_req, res) => {
      res.json({ status: "ok", sessions: sessions.size });
    });

    app.listen(port, () => {
      console.error(`FlowForge MCP server running on http://localhost:${port}/sse`);
      console.error(`Connecting to FlowForge at ${serverUrl}`);
    });
  } else {
    console.error(`Unknown transport: ${transport}. Use "sse" or "stdio".`);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
