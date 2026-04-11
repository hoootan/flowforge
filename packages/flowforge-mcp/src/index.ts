import { createClient } from "flowforge-client";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import express from "express";
import { createMcpServer } from "./server.js";
import { randomUUID } from "crypto";

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
  console.error(`
flowforge-mcp — MCP server for FlowForge (v0.2.0)

Usage:
  flowforge-mcp [options]

Options:
  --server-url <url>    FlowForge server URL (env: FLOWFORGE_SERVER_URL, default: http://localhost:8000)
  --api-key <key>       FlowForge API key (env: FLOWFORGE_API_KEY)
  --transport <type>    Transport: stdio (default) or http
  --port <number>       HTTP server port (default: 3100)
  --help, -h            Show this help message

Examples:
  # stdio transport (for Claude Code / Claude Desktop)
  flowforge-mcp --server-url http://localhost:8000 --api-key ff_live_xxx

  # HTTP transport (Streamable HTTP, for remote clients)
  flowforge-mcp --transport http --port 3100

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
  const transport = args.transport || "stdio";
  const port = parseInt(args.port || "3100", 10);

  if (!apiKey) {
    console.error(
      "Warning: No API key provided. Set --api-key or FLOWFORGE_API_KEY. HTTP transport will be unauthenticated."
    );
  }

  const client = createClient(serverUrl, { apiKey });

  if (transport === "stdio") {
    // Stdio transport — for local process management (Claude Code, Claude Desktop)
    const server = createMcpServer(client, { serverUrl, apiKey });
    const stdioTransport = new StdioServerTransport();
    await server.connect(stdioTransport);
    // Log to stderr only — stdout is reserved for MCP JSON-RPC messages
    console.error("FlowForge MCP server running on stdio");
  } else if (transport === "http") {
    // Streamable HTTP transport — replaces deprecated SSE
    const app = express();
    app.use(express.json());

    // Auth middleware for MCP endpoint (not /health)
    if (apiKey) {
      app.use("/mcp", (req, res, next) => {
        const provided = req.headers["x-flowforge-api-key"];
        if (provided !== apiKey) {
          res.status(401).json({ error: "Invalid or missing X-FlowForge-API-Key header" });
          return;
        }
        next();
      });
    } else {
      console.error("WARNING: HTTP transport running without API key. All MCP requests will be unauthenticated.");
    }

    // Single transport instance — handles all HTTP methods on /mcp
    const httpTransport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => randomUUID(),
    });

    const server = createMcpServer(client, { serverUrl, apiKey });
    await server.connect(httpTransport);

    // All MCP methods (POST, GET, DELETE) on /mcp
    app.all("/mcp", async (req, res) => {
      await httpTransport.handleRequest(req, res, req.body);
    });

    app.get("/health", (_req, res) => {
      res.json({ status: "ok", version: "0.2.0" });
    });

    app.listen(port, () => {
      console.error(`FlowForge MCP server running on http://localhost:${port}/mcp`);
      console.error(`Transport: Streamable HTTP`);
      console.error(`Connecting to FlowForge at ${serverUrl}`);
    });
  } else {
    console.error(`Unknown transport: ${transport}. Use "stdio" or "http".`);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
