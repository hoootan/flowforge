import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerSkillTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_skills",
    "List skill templates — reusable function+tool configs and imported knowledge from marketplaces.",
    {
      category: z.string().optional().describe("Filter by category (e.g., 'development', 'devops')"),
      source: z.enum(["local", "skills_sh", "github", "external"]).optional().describe("Filter by source"),
      search: z.string().optional().describe("Search by name"),
    },
    async (args) => {
      try {
        const params: Record<string, string> = {};
        if (args.category) params.category = args.category;
        if (args.source) params.source = args.source;
        if (args.search) params.search = args.search;
        const qs = new URLSearchParams(params).toString();
        const data = await directFetch(ctx, "GET", `/skills${qs ? `?${qs}` : ""}`) as { skills: unknown[]; total: number };
        return {
          content: [{ type: "text" as const, text: JSON.stringify({ items: data.skills, total: data.total }, null, 2) }],
        };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_search_marketplace",
    "Search the skills.sh marketplace for community-built agent skills. Returns results with install counts and preview URLs.",
    {
      query: z.string().describe("Search query (e.g., 'react', 'docker', 'python patterns')"),
      limit: z.number().default(10).describe("Max results"),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "GET", `/skills/marketplace/search?q=${encodeURIComponent(args.query)}&limit=${args.limit}`);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_preview_skill",
    "Preview a SKILL.md file from a GitHub repository before importing. Shows parsed frontmatter and markdown body.",
    {
      repo: z.string().describe("GitHub owner/repo (e.g., 'vercel-labs/skills')"),
      path: z.string().default("SKILL.md").describe("Path to SKILL.md within the repo"),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "GET", `/skills/marketplace/preview?repo=${encodeURIComponent(args.repo)}&path=${encodeURIComponent(args.path)}`);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_import_skill",
    "Import a skill from the marketplace into FlowForge. Downloads the SKILL.md and creates a local skill template.",
    {
      repo: z.string().describe("GitHub owner/repo to import from"),
      path: z.string().default("SKILL.md").describe("Path to SKILL.md"),
      source: z.enum(["skills_sh", "github"]).default("skills_sh").describe("Import source"),
      name_override: z.string().optional().describe("Override the skill name"),
      category: z.string().optional().describe("Category for the imported skill"),
      tags: z.array(z.string()).optional().describe("Tags for discovery"),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "POST", "/skills/marketplace/import", args);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_set_function_skills",
    "Set which skills are enabled for a function. Enabled skills inject knowledge into the agent's system prompt at runtime.",
    {
      function_id: z.string().describe("The function ID (user-defined, e.g., 'process-order')"),
      skill_ids: z.array(z.string()).describe("List of skill template UUIDs to enable. Pass empty array to disable all."),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "PUT", `/functions/${args.function_id}/skills`, args.skill_ids);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );
}
