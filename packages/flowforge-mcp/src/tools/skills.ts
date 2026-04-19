import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerSkillTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_skills",
    "List installed skill templates, ordered by import date (newest first). Skills are reusable knowledge packets injected into an agent's system prompt at runtime — either authored locally or imported from a marketplace. To browse skills that aren't installed yet, use flowforge_search_marketplace.",
    {
      category: z
        .string()
        .optional()
        .describe("Filter by category string (e.g. 'development', 'devops', 'content')."),
      source: z
        .enum(["local", "skills_sh", "github", "external"])
        .optional()
        .describe("Filter by origin: 'local' (authored here), 'skills_sh' (from skills.sh), 'github', or 'external'."),
      search: z
        .string()
        .optional()
        .describe("Substring search against skill names and descriptions."),
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
    "Search the skills.sh community marketplace for skills you can install. Returns match results with install counts and preview URLs, ordered by relevance. Use flowforge_preview_skill to inspect a specific result before installing, then flowforge_import_skill to install.",
    {
      query: z
        .string()
        .describe("Search query for the marketplace (e.g. 'react', 'docker', 'python patterns')."),
      limit: z
        .number()
        .default(10)
        .describe("Maximum number of marketplace results to return."),
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
    "Fetch and parse a remote SKILL.md file from a GitHub repo without installing it. Shows the frontmatter (name, description, tags) and markdown body so you can confirm it's the right skill. Use flowforge_import_skill next to actually install it.",
    {
      repo: z
        .string()
        .describe("GitHub owner/repo path (e.g. 'vercel-labs/skills')."),
      path: z
        .string()
        .default("SKILL.md")
        .describe("Path to the SKILL.md within the repo. Default 'SKILL.md'."),
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
    "Install a skill from the marketplace into FlowForge by downloading its SKILL.md and creating a local skill template. After installing, wire it into a function or agent via flowforge_set_function_skills or flowforge_set_agent_skills. Preview first with flowforge_preview_skill if you're unsure.",
    {
      repo: z
        .string()
        .describe("GitHub owner/repo path to import from (e.g. 'vercel-labs/skills')."),
      path: z
        .string()
        .default("SKILL.md")
        .describe("Path to the SKILL.md within the repo. Default 'SKILL.md'."),
      source: z
        .enum(["skills_sh", "github"])
        .default("skills_sh")
        .describe("Source tag for bookkeeping: 'skills_sh' (default) or 'github'."),
      name_override: z
        .string()
        .optional()
        .describe("Override the skill name from the SKILL.md frontmatter. Useful to avoid collisions."),
      category: z
        .string()
        .optional()
        .describe("Category label applied locally (e.g. 'devops'). Shown in flowforge_list_skills filters."),
      tags: z
        .array(z.string())
        .optional()
        .describe("Free-form tags for local discovery."),
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
    "Set the complete list of skills enabled for a function. Enabled skills have their SKILL.md content injected into the agent's system prompt at each run. Replaces wholesale — pass an empty array to disable all skills. The agent-side equivalent is flowforge_set_agent_skills.",
    {
      function_id: z
        .string()
        .describe("The user-defined function_id (e.g. 'process-order') or its UUID."),
      skill_ids: z
        .array(z.string())
        .describe("List of skill template UUIDs to enable (from flowforge_list_skills). Empty array disables all skills."),
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
