import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { type McpContext, directFetch } from "../server.js";

export function registerCredentialTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_credentials",
    "List all stored credentials, ordered by name. Secret values are NEVER returned — each entry includes only a masked prefix for identification plus metadata (type, description, created_at). Takes no filter parameters; returns every credential visible to the current API key. To inspect usage, reference credentials in tool configs via {{credential:name}} placeholders.",
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
    "Create a new encrypted credential the workflow tools can reference. Once stored, use the credential in webhook tool URLs or headers via {{credential:name}} placeholders (e.g. 'Authorization: Bearer {{credential:openai_key}}'). The raw value is never readable again after creation — rotate by calling this again with the same name.",
    {
      name: z
        .string()
        .describe("Unique credential identifier (e.g. 'supabase_key'). Referenced as {{credential:name}} elsewhere."),
      value: z
        .string()
        .describe("The raw secret to encrypt and store (API key, token, password, etc.). Never returned by any subsequent call."),
      credential_type: z
        .enum(["api_key", "bearer_token", "basic_auth", "custom"])
        .optional()
        .default("api_key")
        .describe("Type tag for UI display and future typed placeholders: api_key (default), bearer_token, basic_auth, or custom."),
      description: z
        .string()
        .optional()
        .describe("Optional human-readable note explaining what this credential is for."),
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
    "Delete a stored credential by name. Irreversible — the encrypted value is wiped and cannot be undone. Any webhook tool referencing {{credential:name}} will fail on its next call until you create a new credential with the same name (see flowforge_create_credential) or edit the tool to remove the reference.",
    {
      name: z
        .string()
        .describe("The credential name to delete (from flowforge_list_credentials)."),
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
