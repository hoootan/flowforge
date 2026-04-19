import { describe, it, expect, beforeAll } from "vitest";
import type { ZodTypeAny } from "zod";

import type { McpContext } from "../src/server.js";
import { registerAgentTools } from "../src/tools/agents.js";
import { registerApprovalTools } from "../src/tools/approvals.js";
import { registerCommentTools } from "../src/tools/comments.js";
import { registerCredentialTools } from "../src/tools/credentials.js";
import { registerEventTools } from "../src/tools/events.js";
import { registerFunctionTools } from "../src/tools/functions.js";
import { registerHealthTools } from "../src/tools/health.js";
import { registerNotificationTools } from "../src/tools/notifications.js";
import { registerRunTools } from "../src/tools/runs.js";
import { registerSkillTools } from "../src/tools/skills.js";
import { registerTaskTools } from "../src/tools/tasks.js";
import { registerToolTools } from "../src/tools/tools.js";

// See packages/flowforge-mcp/README.md §1–5 for the standard these rules enforce.
const MIN_DESCRIPTION_LENGTH = 80;
const DESTRUCTIVE_PATTERN = /^flowforge_(delete|archive|reject|cancel)_/;
const LIST_PATTERN = /^flowforge_list_/;

const DESTRUCTIVE_PHRASES = [
  "irreversible",
  "cannot be undone",
  "soft-delete",
  "soft delete",
  "preserved",
  "can be restored",
];

const LIST_ORDER_PHRASES = [
  "ordered",
  "order ",
  "order.",
  "sorted",
  "descending",
  "ascending",
  "most recent",
  "newest first",
  "oldest first",
];

interface CapturedTool {
  name: string;
  description: string;
  schema: Record<string, ZodTypeAny>;
}

class FakeMcpServer {
  tools: CapturedTool[] = [];
  tool(
    name: string,
    description: string,
    schema: Record<string, ZodTypeAny>,
    _handler: unknown,
  ): void {
    this.tools.push({ name, description, schema });
  }
}

function fakeContext(): McpContext {
  // None of the registration functions call through to the client/fetcher at
  // registration time — they only wire handlers. The stub just has to type-check.
  return {
    client: {} as McpContext["client"],
    serverUrl: "http://localhost:8000",
    apiKey: "test",
  };
}

function collectAllTools(): CapturedTool[] {
  const server = new FakeMcpServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const s = server as unknown as any;
  const ctx = fakeContext();
  registerAgentTools(s, ctx);
  registerApprovalTools(s, ctx);
  registerCommentTools(s, ctx);
  registerCredentialTools(s, ctx);
  registerEventTools(s, ctx);
  registerFunctionTools(s, ctx);
  registerHealthTools(s, ctx);
  registerNotificationTools(s, ctx);
  registerRunTools(s, ctx);
  registerSkillTools(s, ctx);
  registerTaskTools(s, ctx);
  registerToolTools(s, ctx);
  return server.tools;
}

function descriptionOf(field: ZodTypeAny): string | undefined {
  // Zod 3 stores the description on the instance and in _def.
  const direct = (field as { description?: string }).description;
  if (direct) return direct;
  const def = (field as { _def?: { description?: string } })._def;
  return def?.description;
}

// Strip parenthesized parentheticals so we don't count "(e.g., ...)" as sentences.
function sentenceCount(text: string): number {
  const stripped = text.replace(/\([^)]*\)/g, "");
  const matches = stripped.match(/[.!?](\s|$)/g);
  return matches ? matches.length : 0;
}

function containsAny(haystack: string, needles: string[]): boolean {
  const lower = haystack.toLowerCase();
  return needles.some((n) => lower.includes(n));
}

describe("MCP tool documentation standard", () => {
  let tools: CapturedTool[];

  beforeAll(() => {
    tools = collectAllTools();
    expect(tools.length).toBeGreaterThan(30); // sanity: all registrations fired
  });

  it("every tool has a description at least 80 chars long", () => {
    const offenders = tools
      .filter((t) => t.description.length < MIN_DESCRIPTION_LENGTH)
      .map((t) => `${t.name} (${t.description.length} chars): "${t.description}"`);
    expect(offenders, offenders.join("\n")).toEqual([]);
  });

  it("every tool description is at least two sentences", () => {
    const offenders = tools
      .filter((t) => sentenceCount(t.description) < 2)
      .map((t) => `${t.name}: "${t.description}"`);
    expect(offenders, offenders.join("\n")).toEqual([]);
  });

  it("every parameter has a non-empty .describe()", () => {
    const offenders: string[] = [];
    for (const t of tools) {
      for (const [key, field] of Object.entries(t.schema)) {
        const desc = descriptionOf(field);
        if (!desc || desc.trim().length === 0) {
          offenders.push(`${t.name}.${key}`);
        }
      }
    }
    expect(offenders, offenders.join("\n")).toEqual([]);
  });

  it("destructive tools warn about irreversibility or soft-delete", () => {
    const offenders = tools
      .filter((t) => DESTRUCTIVE_PATTERN.test(t.name))
      .filter((t) => !containsAny(t.description, DESTRUCTIVE_PHRASES))
      .map((t) => `${t.name}: "${t.description}"`);
    expect(offenders, offenders.join("\n")).toEqual([]);
  });

  it("list tools describe their ordering", () => {
    const offenders = tools
      .filter((t) => LIST_PATTERN.test(t.name))
      .filter((t) => !containsAny(t.description, LIST_ORDER_PHRASES))
      .map((t) => `${t.name}: "${t.description}"`);
    expect(offenders, offenders.join("\n")).toEqual([]);
  });
});
