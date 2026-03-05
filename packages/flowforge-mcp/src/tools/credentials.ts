import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { type McpContext, directFetch } from "../server.js";

export function registerCredentialTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_credentials",
    "List all stored credentials. Values are never returned — only masked prefixes for identification.",
    {},
    async () => {
      try {
        const data = await directFetch(ctx, "GET", "/credentials");
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(data, null, 2) },
          ],
        };
      } catch (err) {
        return {
          content: [
            { type: "text" as const, text: `Error: ${(err as Error).message}` },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "flowforge_create_credential",
    "Create a new encrypted credential. Use credentials in webhook tool headers/URLs via {{credential:name}} placeholders.",
    {
      name: z.string().describe("Unique credential name (e.g., 'supabase_key')"),
      value: z.string().describe("The secret value to encrypt and store"),
      credential_type: z
        .enum(["api_key", "bearer_token", "basic_auth", "custom"])
        .optional()
        .default("api_key")
        .describe("Type of credential"),
      description: z
        .string()
        .optional()
        .describe("Optional description of what this credential is for"),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "POST", "/credentials", {
          name: args.name,
          value: args.value,
          credential_type: args.credential_type,
          description: args.description,
        });
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(data, null, 2) },
          ],
        };
      } catch (err) {
        return {
          content: [
            { type: "text" as const, text: `Error: ${(err as Error).message}` },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "flowforge_delete_credential",
    "Delete a stored credential by name.",
    {
      name: z.string().describe("The credential name to delete"),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "DELETE", `/credentials/${encodeURIComponent(args.name)}`);
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(data, null, 2) },
          ],
        };
      } catch (err) {
        return {
          content: [
            { type: "text" as const, text: `Error: ${(err as Error).message}` },
          ],
          isError: true,
        };
      }
    }
  );
}
