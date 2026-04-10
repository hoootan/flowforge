import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerTaskTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_tasks",
    "List tasks with optional filters. Tasks are Kanban-style work items assignable to humans or agents.",
    {
      status: z.enum(["todo", "in_progress", "in_review", "done", "blocked", "cancelled"]).optional().describe("Filter by status"),
      priority: z.enum(["urgent", "high", "medium", "low", "none"]).optional().describe("Filter by priority"),
      assignee_agent_id: z.string().optional().describe("Filter by assigned agent UUID"),
      assignee_user_id: z.string().optional().describe("Filter by assigned user UUID"),
      limit: z.number().default(20).describe("Max results"),
    },
    async (args) => {
      try {
        const params: Record<string, string> = {};
        if (args.status) params.status = args.status;
        if (args.priority) params.priority = args.priority;
        if (args.assignee_agent_id) params.assignee_agent_id = args.assignee_agent_id;
        if (args.assignee_user_id) params.assignee_user_id = args.assignee_user_id;
        params.limit = String(args.limit);
        const qs = new URLSearchParams(params).toString();
        const data = await directFetch(ctx, "GET", `/tasks?${qs}`) as { tasks: unknown[]; total: number };
        return {
          content: [{ type: "text" as const, text: JSON.stringify({ items: data.tasks, total: data.total, has_more: data.tasks.length >= args.limit }, null, 2) }],
        };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_get_task_board",
    "Get the Kanban board view — tasks grouped by status columns (todo, in_progress, in_review, done, blocked, cancelled).",
    {
      assignee_agent_id: z.string().optional().describe("Filter board by agent"),
      assignee_user_id: z.string().optional().describe("Filter board by user"),
    },
    async (args) => {
      try {
        const params: Record<string, string> = {};
        if (args.assignee_agent_id) params.assignee_agent_id = args.assignee_agent_id;
        if (args.assignee_user_id) params.assignee_user_id = args.assignee_user_id;
        const qs = new URLSearchParams(params).toString();
        const data = await directFetch(ctx, "GET", `/tasks/board${qs ? `?${qs}` : ""}`);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_get_task",
    "Get details of a specific task including assignee, comments count, sub-tasks, and linked function/run.",
    {
      task_id: z.string().describe("The task UUID"),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "GET", `/tasks/${args.task_id}`);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_create_task",
    "Create a new task on the board. Tasks get auto-assigned human-readable identifiers (FF-1, FF-2, etc.).",
    {
      title: z.string().describe("Task title"),
      description: z.string().optional().describe("Task description (markdown)"),
      priority: z.enum(["urgent", "high", "medium", "low", "none"]).default("none").describe("Priority level"),
      assignee_agent_id: z.string().optional().describe("Assign to an agent by UUID"),
      assignee_user_id: z.string().optional().describe("Assign to a user by UUID"),
      function_id: z.string().optional().describe("Link to a FlowForge function UUID"),
      labels: z.array(z.string()).optional().describe("Tags/labels for the task"),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "POST", "/tasks", args);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_update_task",
    "Update a task — change status (drag between columns), reassign, update priority, or link to a run.",
    {
      task_id: z.string().describe("The task UUID"),
      title: z.string().optional().describe("New title"),
      status: z.enum(["todo", "in_progress", "in_review", "done", "blocked", "cancelled"]).optional().describe("New status"),
      priority: z.enum(["urgent", "high", "medium", "low", "none"]).optional().describe("New priority"),
      assignee_agent_id: z.string().optional().describe("Reassign to agent"),
      assignee_user_id: z.string().optional().describe("Reassign to user"),
    },
    async (args) => {
      try {
        const { task_id, ...updates } = args;
        const data = await directFetch(ctx, "PATCH", `/tasks/${task_id}`, updates);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_delete_task",
    "Delete a task from the board. This action cannot be undone.",
    {
      task_id: z.string().describe("The task UUID to delete"),
    },
    async (args) => {
      try {
        await directFetch(ctx, "DELETE", `/tasks/${args.task_id}`);
        return { content: [{ type: "text" as const, text: `Task ${args.task_id} deleted.` }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );
}
