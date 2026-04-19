import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerTaskTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_tasks",
    "List tasks as a flat array, ordered by creation time (newest first). Tasks are Kanban work items assignable to humans or agents. Use flowforge_get_task_board instead when you want tasks grouped into status columns, or flowforge_get_task for a single task.",
    {
      status: z
        .enum(["todo", "in_progress", "in_review", "done", "blocked", "cancelled"])
        .optional()
        .describe("Filter by status. One of: todo, in_progress, in_review, done, blocked, cancelled."),
      priority: z
        .enum(["urgent", "high", "medium", "low", "none"])
        .optional()
        .describe("Filter by priority. One of: urgent, high, medium, low, none."),
      assignee_agent_id: z
        .string()
        .optional()
        .describe("Filter to tasks assigned to this agent UUID (from flowforge_list_agents)."),
      assignee_user_id: z
        .string()
        .optional()
        .describe("Filter to tasks assigned to this user UUID."),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of tasks to return. Server caps at 100."),
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
    "Get the Kanban board view — tasks grouped into status columns (todo, in_progress, in_review, done, blocked, cancelled). Use this when you want a bird's-eye view of project status. For a flat list with more filter knobs, use flowforge_list_tasks.",
    {
      assignee_agent_id: z
        .string()
        .optional()
        .describe("Restrict the board to tasks assigned to this agent UUID."),
      assignee_user_id: z
        .string()
        .optional()
        .describe("Restrict the board to tasks assigned to this user UUID."),
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
    "Get the full record of a single task: title, description, assignee, linked function/run, labels, and comment/sub-task counts. Use after flowforge_list_tasks or flowforge_get_task_board to drill into a specific task. For the comment thread itself, use flowforge_list_comments.",
    {
      task_id: z
        .string()
        .describe("The task UUID (from flowforge_list_tasks or flowforge_get_task_board)."),
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
    "Create a new task on the Kanban board. Tasks auto-get human-readable identifiers like FF-1, FF-2. To update an existing task, use flowforge_update_task; to see what already exists, use flowforge_list_tasks or flowforge_get_task_board.",
    {
      title: z
        .string()
        .describe("Short task title shown on the card."),
      description: z
        .string()
        .optional()
        .describe("Longer task description (markdown supported)."),
      priority: z
        .enum(["urgent", "high", "medium", "low", "none"])
        .default("none")
        .describe("Priority level. One of: urgent, high, medium, low, none. Default none."),
      assignee_agent_id: z
        .string()
        .optional()
        .describe("Assign to an agent by UUID (from flowforge_list_agents). Mutually exclusive with assignee_user_id."),
      assignee_user_id: z
        .string()
        .optional()
        .describe("Assign to a user by UUID. Mutually exclusive with assignee_agent_id."),
      function_id: z
        .string()
        .optional()
        .describe("Link this task to a FlowForge function UUID (from flowforge_list_functions) so completing the task ties back to a workflow."),
      labels: z
        .array(z.string())
        .optional()
        .describe("Free-form labels for filtering (e.g. ['bug', 'backend']). Optional."),
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
    "Update fields on an existing task — change status (moves the card between columns), reassign, retitle, or re-prioritize. Only provided fields are changed; omitted fields keep their current value. For creating a new task, use flowforge_create_task; to remove one, use flowforge_delete_task.",
    {
      task_id: z
        .string()
        .describe("The task UUID to update (from flowforge_list_tasks)."),
      title: z
        .string()
        .optional()
        .describe("New task title."),
      status: z
        .enum(["todo", "in_progress", "in_review", "done", "blocked", "cancelled"])
        .optional()
        .describe("New status. Changing status moves the card to that Kanban column."),
      priority: z
        .enum(["urgent", "high", "medium", "low", "none"])
        .optional()
        .describe("New priority level."),
      assignee_agent_id: z
        .string()
        .optional()
        .describe("Reassign to an agent by UUID. Mutually exclusive with assignee_user_id."),
      assignee_user_id: z
        .string()
        .optional()
        .describe("Reassign to a user by UUID. Mutually exclusive with assignee_agent_id."),
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
    "Delete a task from the board. Irreversible — the task and its comments are removed and cannot be undone. If you only want to hide the task, move it to 'cancelled' status via flowforge_update_task instead.",
    {
      task_id: z
        .string()
        .describe("The task UUID to delete (from flowforge_list_tasks)."),
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
