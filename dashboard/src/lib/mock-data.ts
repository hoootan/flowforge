/**
 * Mock data for local development — based on real FlowForge data models.
 * Only used when NEXT_PUBLIC_USE_MOCK=true.
 */

import type {
  Run,
  RunWithSteps,
  Step,
  Function,
  Tool,
  Event,
  Stats,
  PendingApproval,
  ApiKey,
  AIProvider,
  UsageSummary,
  DailyUsage,
  UsageByProvider,
  UsageByModel,
  ModelPricingConfig,
  EffectiveModelPricing,
  DefaultModelPricing,
  Credential,
} from "./api";
import type { User, UserWithPermissions } from "@/lib/auth/types";

// ── Helpers ──────────────────────────────────────────────────────────
function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

function hoursAgo(n: number): string {
  const d = new Date();
  d.setHours(d.getHours() - n);
  return d.toISOString();
}

function minutesAgo(n: number): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - n);
  return d.toISOString();
}

function minutesAfter(base: string, n: number): string {
  const d = new Date(base);
  d.setMinutes(d.getMinutes() + n);
  return d.toISOString();
}

function secondsAfter(base: string, n: number): string {
  const d = new Date(base);
  d.setSeconds(d.getSeconds() + n);
  return d.toISOString();
}

// ── Stable IDs ───────────────────────────────────────────────────────
const TENANT_ID = "t-00000000-0000-0000-0000-000000000001";

const FN_IDS = {
  processOrder: "fn-001",
  sendWelcomeEmail: "fn-002",
  syncInventory: "fn-003",
  handleRefund: "fn-004",
  generateReport: "fn-005",
  webhookStripe: "fn-006",
};

const RUN_IDS = Array.from({ length: 20 }, (_, i) =>
  `run-${String(i + 1).padStart(3, "0")}`
);

const USER_IDS = {
  admin: "usr-001",
  member: "usr-002",
  viewer: "usr-003",
};

// ── Functions ────────────────────────────────────────────────────────
export const mockFunctions: Function[] = [
  {
    id: FN_IDS.processOrder,
    function_id: "process-order",
    name: "Process Order",
    trigger_type: "event",
    trigger_value: "order/created",
    trigger_expression: null,
    endpoint_url: null,
    is_inline: true,
    system_prompt: "You are an order processing agent. Validate the order, check inventory, charge payment, and send confirmation.",
    tools_config: ["query_database", "send_email"],
    agent_config: { model: "gpt-4o", max_iterations: 5, max_tool_calls: 10 },
    config: { retries: 3, timeout: "5m", concurrency_limit: 10 },
    is_active: true,
    created_at: daysAgo(30),
    updated_at: daysAgo(2),
  },
  {
    id: FN_IDS.sendWelcomeEmail,
    function_id: "send-welcome-email",
    name: "Send Welcome Email",
    trigger_type: "event",
    trigger_value: "user/signed_up",
    trigger_expression: null,
    endpoint_url: null,
    is_inline: true,
    system_prompt: "Generate a personalized welcome email for the new user.",
    tools_config: ["send_email"],
    agent_config: { model: "gpt-4o-mini", max_iterations: 2, max_tool_calls: 3 },
    config: { retries: 2, timeout: "2m" },
    is_active: true,
    created_at: daysAgo(25),
    updated_at: daysAgo(5),
  },
  {
    id: FN_IDS.syncInventory,
    function_id: "sync-inventory",
    name: "Sync Inventory",
    trigger_type: "cron",
    trigger_value: "*/15 * * * *",
    trigger_expression: null,
    endpoint_url: "http://worker:8001/sync-inventory",
    is_inline: false,
    system_prompt: null,
    tools_config: null,
    agent_config: null,
    config: { retries: 3, timeout: "10m" },
    is_active: true,
    created_at: daysAgo(20),
    updated_at: daysAgo(1),
  },
  {
    id: FN_IDS.handleRefund,
    function_id: "handle-refund",
    name: "Handle Refund",
    trigger_type: "event",
    trigger_value: "payment/refund_requested",
    trigger_expression: "data.amount > 0",
    endpoint_url: null,
    is_inline: true,
    system_prompt: "Process the refund request. Verify eligibility, process the refund, and notify the customer.",
    tools_config: ["query_database", "send_email", "slack_notify"],
    agent_config: { model: "claude-sonnet-4-20250514", max_iterations: 4, max_tool_calls: 8 },
    config: { retries: 2, timeout: "3m" },
    is_active: true,
    created_at: daysAgo(15),
    updated_at: daysAgo(3),
  },
  {
    id: FN_IDS.generateReport,
    function_id: "generate-report",
    name: "Generate Weekly Report",
    trigger_type: "cron",
    trigger_value: "0 9 * * 1",
    trigger_expression: null,
    endpoint_url: null,
    is_inline: true,
    system_prompt: "Generate a comprehensive weekly report summarizing sales, inventory, and customer metrics.",
    tools_config: ["query_database", "generate_pdf", "send_email"],
    agent_config: {
      model: "gpt-4o",
      max_iterations: 8,
      max_tool_calls: 20,
      sub_agents: {
        "data-analyst": {
          system_prompt: "Analyze sales and inventory data.",
          model: "gpt-4o-mini",
          tools: ["query_database"],
          max_iterations: 3,
          description: "Fetches and analyzes raw data",
        },
      },
    },
    config: { retries: 1, timeout: "15m" },
    is_active: true,
    created_at: daysAgo(10),
    updated_at: daysAgo(1),
  },
  {
    id: FN_IDS.webhookStripe,
    function_id: "webhook-stripe",
    name: "Stripe Webhook Handler",
    trigger_type: "webhook",
    trigger_value: "/webhooks/stripe",
    trigger_expression: null,
    endpoint_url: "http://worker:8001/stripe-handler",
    is_inline: false,
    system_prompt: null,
    tools_config: null,
    agent_config: null,
    config: { retries: 5, timeout: "1m" },
    is_active: false,
    created_at: daysAgo(8),
    updated_at: daysAgo(8),
  },
];

// ── Runs ─────────────────────────────────────────────────────────────
const runBase = (
  i: number,
  fnId: string,
  status: Run["status"],
  createdOffset: number,
  extra: Partial<Run> = {}
): Run => ({
  id: RUN_IDS[i],
  function_id: fnId,
  event_id: status !== "cancelled" ? `evt-${String(i + 1).padStart(3, "0")}` : null,
  status,
  trigger_type: "event",
  trigger_data: { event_name: "order/created", event_data: { order_id: `ORD-${1000 + i}` } },
  output: status === "completed" ? { result: "success", processed: true } : null,
  error: status === "failed" ? { message: "Step execution failed", code: "STEP_ERROR", traceback: "Traceback (most recent call last):\n  File \"process_order.py\", line 42\n    raise ValueError(\"Invalid order\")" } : null,
  attempt: status === "failed" ? 3 : 1,
  max_attempts: 3,
  started_at: hoursAgo(createdOffset),
  ended_at: ["completed", "failed", "cancelled"].includes(status)
    ? minutesAfter(hoursAgo(createdOffset), 2)
    : null,
  created_at: hoursAgo(createdOffset),
  ...extra,
});

export const mockRuns: Run[] = [
  // Completed (12)
  runBase(0, FN_IDS.processOrder, "completed", 1),
  runBase(1, FN_IDS.sendWelcomeEmail, "completed", 2),
  runBase(2, FN_IDS.processOrder, "completed", 5),
  runBase(3, FN_IDS.syncInventory, "completed", 8, { trigger_type: "cron", trigger_data: { scheduled_at: hoursAgo(8) } }),
  runBase(4, FN_IDS.handleRefund, "completed", 12, { trigger_data: { event_name: "payment/refund_requested", event_data: { amount: 49.99, reason: "Item damaged" } } }),
  runBase(5, FN_IDS.processOrder, "completed", 18),
  runBase(6, FN_IDS.sendWelcomeEmail, "completed", 24),
  runBase(7, FN_IDS.processOrder, "completed", 36),
  runBase(8, FN_IDS.syncInventory, "completed", 48, { trigger_type: "cron" }),
  runBase(9, FN_IDS.handleRefund, "completed", 72, { trigger_data: { event_name: "payment/refund_requested", event_data: { amount: 129.00, reason: "Wrong item" } } }),
  runBase(10, FN_IDS.generateReport, "completed", 96, { trigger_type: "cron" }),
  runBase(11, FN_IDS.processOrder, "completed", 120),
  // Failed (3)
  runBase(12, FN_IDS.processOrder, "failed", 3, { error: { message: "Payment gateway timeout", code: "TIMEOUT" } }),
  runBase(13, FN_IDS.handleRefund, "failed", 15, { error: { message: "Insufficient funds for refund", code: "INSUFFICIENT_FUNDS" } }),
  runBase(14, FN_IDS.syncInventory, "failed", 30, { error: { message: "API rate limit exceeded", code: "RATE_LIMITED" }, trigger_type: "cron" }),
  // Running (2)
  runBase(15, FN_IDS.processOrder, "running", 0.1),
  runBase(16, FN_IDS.generateReport, "running", 0.05, { trigger_type: "cron" }),
  // Pending (1)
  runBase(17, FN_IDS.sendWelcomeEmail, "pending", 0.02),
  // Paused (1)
  runBase(18, FN_IDS.handleRefund, "paused", 0.5, { trigger_data: { event_name: "payment/refund_requested", event_data: { amount: 250.00, reason: "Duplicate charge" } } }),
  // Cancelled (1)
  runBase(19, FN_IDS.processOrder, "cancelled", 6),
];

// ── Steps (for detailed runs) ────────────────────────────────────────
function makeSteps(runId: string, baseTime: string): Step[] {
  const s = (
    idx: number,
    stepId: string,
    stepType: Step["step_type"],
    status: Step["status"],
    offsetSec: number,
    durationSec: number,
    extra: Partial<Step> = {}
  ): Step => {
    const started = secondsAfter(baseTime, offsetSec);
    const ended = ["completed", "failed"].includes(status)
      ? secondsAfter(started, durationSec)
      : null;
    return {
      id: `${runId}-step-${idx}`,
      step_id: stepId,
      step_type: stepType,
      status,
      input: extra.input ?? null,
      output: status === "completed" ? (extra.output ?? { result: "ok" }) : null,
      error: status === "failed" ? (extra.error ?? { message: "Step failed" }) : null,
      attempt: 1,
      max_attempts: 3,
      started_at: started,
      ended_at: ended,
      created_at: started,
      ...extra,
    };
  };

  return [
    s(0, "validate-input", "run", "completed", 0, 1, {
      input: { order_id: "ORD-1001" },
      output: { valid: true, customer_id: "cust-42" },
    }),
    s(1, "fetch-customer", "run", "completed", 2, 3, {
      input: { customer_id: "cust-42" },
      output: { name: "Alice Johnson", email: "alice@example.com", tier: "premium" },
    }),
    s(2, "check-inventory", "run", "completed", 6, 2, {
      input: { items: ["SKU-100", "SKU-201"] },
      output: { available: true, warehouse: "US-WEST" },
    }),
    s(3, "calculate-pricing", "ai", "completed", 9, 5, {
      input: { prompt: "Calculate final price with premium discount" },
      output: { total: 89.99, discount: 10.00, tax: 7.20 },
    }),
    s(4, "charge-payment", "run", "completed", 15, 4, {
      input: { amount: 89.99, method: "card_ending_4242" },
      output: { transaction_id: "txn_abc123", status: "captured" },
    }),
    s(5, "send-confirmation", "invoke", "completed", 20, 2, {
      input: { function_id: "send-welcome-email", data: { email: "alice@example.com" } },
      output: { run_id: "run-nested-001" },
    }),
    s(6, "wait-for-shipping", "wait_for_event", "completed", 23, 120, {
      input: { event: "shipping/label_created", match: "data.order_id == 'ORD-1001'" },
      output: { tracking_number: "1Z999AA10123456784" },
    }),
    s(7, "notify-customer", "run", "completed", 144, 1, {
      input: { email: "alice@example.com", tracking: "1Z999AA10123456784" },
      output: { sent: true },
    }),
  ];
}

function makeAgentSteps(runId: string, baseTime: string): Step[] {
  return [
    {
      id: `${runId}-step-0`,
      step_id: "agent-analyze",
      step_type: "agent",
      status: "completed",
      input: { prompt: "Analyze sales data for the past week" },
      output: { output: "Weekly sales increased by 12% compared to the previous week.", iterations: 3, tool_calls_count: 5, tokens_used: 4200 },
      error: null,
      attempt: 1,
      max_attempts: 1,
      started_at: baseTime,
      ended_at: secondsAfter(baseTime, 45),
      created_at: baseTime,
    },
    {
      id: `${runId}-step-1`,
      step_id: "sub-agent-data",
      step_type: "sub_agent",
      status: "completed",
      input: { agent_id: "data-analyst", prompt: "Query total revenue by category" },
      output: { output: "Revenue breakdown: Electronics $45K, Clothing $28K, Home $15K", iterations: 2, tool_calls_count: 3 },
      error: null,
      attempt: 1,
      max_attempts: 1,
      started_at: secondsAfter(baseTime, 5),
      ended_at: secondsAfter(baseTime, 25),
      created_at: secondsAfter(baseTime, 5),
    },
    {
      id: `${runId}-step-2`,
      step_id: "generate-pdf-report",
      step_type: "run",
      status: "completed",
      input: { template: "weekly-report", data: { revenue: 88000, growth: 0.12 } },
      output: { pdf_url: "/reports/weekly-2024-w15.pdf", pages: 8 },
      error: null,
      attempt: 1,
      max_attempts: 3,
      started_at: secondsAfter(baseTime, 46),
      ended_at: secondsAfter(baseTime, 52),
      created_at: secondsAfter(baseTime, 46),
    },
    {
      id: `${runId}-step-3`,
      step_id: "email-report",
      step_type: "run",
      status: "completed",
      input: { to: "team@company.com", subject: "Weekly Report" },
      output: { sent: true, message_id: "msg-abc-123" },
      error: null,
      attempt: 1,
      max_attempts: 3,
      started_at: secondsAfter(baseTime, 53),
      ended_at: secondsAfter(baseTime, 55),
      created_at: secondsAfter(baseTime, 53),
    },
  ];
}

export const mockRunsWithSteps: Record<string, RunWithSteps> = {
  [RUN_IDS[0]]: { ...mockRuns[0], steps: makeSteps(RUN_IDS[0], mockRuns[0].started_at!) },
  [RUN_IDS[2]]: { ...mockRuns[2], steps: makeSteps(RUN_IDS[2], mockRuns[2].started_at!) },
  [RUN_IDS[10]]: { ...mockRuns[10], steps: makeAgentSteps(RUN_IDS[10], mockRuns[10].started_at!) },
  [RUN_IDS[12]]: {
    ...mockRuns[12],
    steps: [
      ...makeSteps(RUN_IDS[12], mockRuns[12].started_at!).slice(0, 4),
      {
        id: `${RUN_IDS[12]}-step-4`,
        step_id: "charge-payment",
        step_type: "run",
        status: "failed",
        input: { amount: 89.99, method: "card_ending_4242" },
        output: null,
        error: { message: "Payment gateway timeout", code: "TIMEOUT" },
        attempt: 3,
        max_attempts: 3,
        started_at: secondsAfter(mockRuns[12].started_at!, 15),
        ended_at: secondsAfter(mockRuns[12].started_at!, 45),
        created_at: secondsAfter(mockRuns[12].started_at!, 15),
      },
    ],
  },
};

// ── Events ───────────────────────────────────────────────────────────
export const mockEvents: Event[] = [
  { id: "evt-001", event_id: "evt-ext-001", name: "order/created", data: { order_id: "ORD-1001", customer: "Alice Johnson", total: 99.99, items: ["SKU-100", "SKU-201"] }, timestamp: hoursAgo(1), received_at: hoursAgo(1), user_id: null, processed: true },
  { id: "evt-002", event_id: "evt-ext-002", name: "user/signed_up", data: { email: "bob@example.com", name: "Bob Smith", plan: "pro" }, timestamp: hoursAgo(2), received_at: hoursAgo(2), user_id: null, processed: true },
  { id: "evt-003", event_id: "evt-ext-003", name: "order/created", data: { order_id: "ORD-1002", customer: "Carol White", total: 249.50 }, timestamp: hoursAgo(5), received_at: hoursAgo(5), user_id: null, processed: true },
  { id: "evt-004", event_id: "evt-ext-004", name: "payment/refund_requested", data: { order_id: "ORD-0998", amount: 49.99, reason: "Item damaged" }, timestamp: hoursAgo(12), received_at: hoursAgo(12), user_id: null, processed: true },
  { id: "evt-005", event_id: "evt-ext-005", name: "inventory/low", data: { sku: "SKU-100", current_stock: 3, threshold: 10 }, timestamp: hoursAgo(15), received_at: hoursAgo(15), user_id: null, processed: true },
  { id: "evt-006", event_id: "evt-ext-006", name: "order/created", data: { order_id: "ORD-1003", customer: "Dave Brown", total: 34.99 }, timestamp: hoursAgo(18), received_at: hoursAgo(18), user_id: null, processed: true },
  { id: "evt-007", event_id: "evt-ext-007", name: "user/signed_up", data: { email: "eve@example.com", name: "Eve Davis", plan: "free" }, timestamp: hoursAgo(24), received_at: hoursAgo(24), user_id: null, processed: true },
  { id: "evt-008", event_id: "evt-ext-008", name: "webhook/stripe", data: { type: "charge.succeeded", amount: 9999, currency: "usd" }, timestamp: hoursAgo(30), received_at: hoursAgo(30), user_id: null, processed: true },
  { id: "evt-009", event_id: "evt-ext-009", name: "order/created", data: { order_id: "ORD-1004", customer: "Frank Miller", total: 189.00 }, timestamp: hoursAgo(36), received_at: hoursAgo(36), user_id: null, processed: true },
  { id: "evt-010", event_id: "evt-ext-010", name: "payment/refund_requested", data: { order_id: "ORD-0995", amount: 129.00, reason: "Wrong item" }, timestamp: hoursAgo(48), received_at: hoursAgo(48), user_id: null, processed: true },
  { id: "evt-011", event_id: "evt-ext-011", name: "inventory/low", data: { sku: "SKU-305", current_stock: 1, threshold: 5 }, timestamp: hoursAgo(52), received_at: hoursAgo(52), user_id: null, processed: false },
  { id: "evt-012", event_id: "evt-ext-012", name: "order/created", data: { order_id: "ORD-1005", customer: "Grace Lee", total: 450.00 }, timestamp: hoursAgo(60), received_at: hoursAgo(60), user_id: null, processed: true },
  { id: "evt-013", event_id: "evt-ext-013", name: "user/signed_up", data: { email: "hank@example.com", name: "Hank Wilson", plan: "pro" }, timestamp: hoursAgo(68), received_at: hoursAgo(68), user_id: null, processed: true },
  { id: "evt-014", event_id: "evt-ext-014", name: "webhook/stripe", data: { type: "invoice.paid", amount: 29900, currency: "usd" }, timestamp: hoursAgo(70), received_at: hoursAgo(70), user_id: null, processed: true },
  { id: "evt-015", event_id: "evt-ext-015", name: "payment/refund_requested", data: { order_id: "ORD-0990", amount: 250.00, reason: "Duplicate charge" }, timestamp: minutesAgo(30), received_at: minutesAgo(30), user_id: null, processed: false },
];

// ── Tools ────────────────────────────────────────────────────────────
export const mockTools: Tool[] = [
  {
    id: "tool-001", name: "send_email", description: "Send an email to a recipient with subject and body.",
    parameters: { type: "object", properties: { to: { type: "string" }, subject: { type: "string" }, body: { type: "string" } }, required: ["to", "subject", "body"] },
    tool_type: "custom", code: "import smtplib\n\ndef execute(to, subject, body):\n    # Send email via SMTP\n    pass", webhook_url: null, webhook_method: "POST", webhook_headers: null,
    is_builtin: false, requires_approval: false, approval_timeout: null, is_active: true, created_at: daysAgo(28), updated_at: daysAgo(5),
  },
  {
    id: "tool-002", name: "query_database", description: "Execute a read-only SQL query against the application database.",
    parameters: { type: "object", properties: { query: { type: "string", description: "SQL query to execute" }, params: { type: "array", items: { type: "string" } } }, required: ["query"] },
    tool_type: "custom", code: "import asyncpg\n\nasync def execute(query, params=None):\n    # Execute query\n    pass", webhook_url: null, webhook_method: "POST", webhook_headers: null,
    is_builtin: false, requires_approval: true, approval_timeout: "30m", is_active: true, created_at: daysAgo(28), updated_at: daysAgo(3),
  },
  {
    id: "tool-003", name: "slack_notify", description: "Send a notification to a Slack channel.",
    parameters: { type: "object", properties: { channel: { type: "string" }, message: { type: "string" }, blocks: { type: "array" } }, required: ["channel", "message"] },
    tool_type: "webhook", code: null, webhook_url: "https://hooks.slack.com/services/T00/B00/xxx", webhook_method: "POST", webhook_headers: { "Content-Type": "application/json" },
    is_builtin: false, requires_approval: false, approval_timeout: null, is_active: true, created_at: daysAgo(20), updated_at: daysAgo(10),
  },
  {
    id: "tool-004", name: "search_web", description: "Search the web for information using a query string.",
    parameters: { type: "object", properties: { query: { type: "string" }, max_results: { type: "number", default: 5 } }, required: ["query"] },
    tool_type: "builtin", code: null, webhook_url: null, webhook_method: "POST", webhook_headers: null,
    is_builtin: true, requires_approval: false, approval_timeout: null, is_active: true, created_at: daysAgo(30), updated_at: daysAgo(30),
  },
  {
    id: "tool-005", name: "generate_pdf", description: "Generate a PDF document from a template and data.",
    parameters: { type: "object", properties: { template: { type: "string" }, data: { type: "object" }, filename: { type: "string" } }, required: ["template", "data"] },
    tool_type: "custom", code: "from weasyprint import HTML\n\ndef execute(template, data, filename=None):\n    # Generate PDF\n    pass", webhook_url: null, webhook_method: "POST", webhook_headers: null,
    is_builtin: false, requires_approval: false, approval_timeout: null, is_active: true, created_at: daysAgo(14), updated_at: daysAgo(7),
  },
];

// ── Users ────────────────────────────────────────────────────────────
export const mockUsers: User[] = [
  { id: USER_IDS.admin, email: "admin@flowforge.dev", name: "Alex Rivera", role: "admin", is_active: true, last_login_at: minutesAgo(15), created_at: daysAgo(60) },
  { id: USER_IDS.member, email: "sarah@flowforge.dev", name: "Sarah Kim", role: "member", is_active: true, last_login_at: hoursAgo(3), created_at: daysAgo(45) },
  { id: USER_IDS.viewer, email: "viewer@flowforge.dev", name: "Jordan Lee", role: "viewer", is_active: true, last_login_at: daysAgo(2), created_at: daysAgo(30) },
];

export const mockCurrentUser: UserWithPermissions = {
  ...mockUsers[0],
  tenant_id: TENANT_ID,
  permissions: {
    can_manage_users: true,
    can_create_resources: true,
    is_admin: true,
    is_member: false,
    is_viewer: false,
  },
  totp_enabled: false,
};

// ── API Keys ─────────────────────────────────────────────────────────
export const mockApiKeys: ApiKey[] = [
  { id: "key-001", name: "Production API Key", key_prefix: "ff_live_a1b2", key_type: "live", scopes: ["events:send", "events:read", "runs:read", "runs:manage", "functions:read", "functions:manage", "tools:read", "tools:manage"], expires_at: null, last_used_at: minutesAgo(5), is_active: true, created_at: daysAgo(45) },
  { id: "key-002", name: "Development Key", key_prefix: "ff_test_c3d4", key_type: "test", scopes: ["events:send", "events:read", "runs:read", "runs:manage", "functions:read", "functions:manage", "tools:read", "tools:manage"], expires_at: null, last_used_at: hoursAgo(1), is_active: true, created_at: daysAgo(40) },
  { id: "key-003", name: "Dashboard Read-Only", key_prefix: "ff_ro_e5f6", key_type: "ro", scopes: ["events:read", "runs:read", "functions:read", "tools:read", "approvals:read"], expires_at: daysAgo(-90), last_used_at: daysAgo(3), is_active: true, created_at: daysAgo(30) },
];

// ── AI Providers ─────────────────────────────────────────────────────
export const mockAIProviders: AIProvider[] = [
  { id: "prov-001", provider_name: "openai", display_name: "OpenAI", api_key_prefix: "sk-...abc", auth_type: "api_key", base_url: null, is_active: true, is_default: true, config: {}, created_at: daysAgo(50), updated_at: daysAgo(5) },
  { id: "prov-002", provider_name: "anthropic", display_name: "Anthropic", api_key_prefix: "sk-ant...xyz", auth_type: "api_key", base_url: null, is_active: true, is_default: false, config: {}, created_at: daysAgo(40), updated_at: daysAgo(10) },
];

// ── Stats ────────────────────────────────────────────────────────────
export const mockStats: Stats = {
  runs: { total: 1247, completed: 1089, failed: 98, running: 2 },
  functions: { total: 6, active: 5 },
  events: { today: 23, total: 892 },
  queue: { pending: 1, running: 2, scheduled: 3 },
};

// ── Pending Approvals ────────────────────────────────────────────────
export const mockApprovals: PendingApproval[] = [
  {
    id: "appr-001", tool_call_id: "tc-001", tool_name: "query_database",
    arguments: { query: "SELECT * FROM orders WHERE status = 'pending' LIMIT 100", params: [] },
    run_id: RUN_IDS[15], function_id: FN_IDS.processOrder,
    agent_conversation: [
      { role: "assistant", content: "I need to check the pending orders in the database." },
      { role: "tool_use", content: "", tool_name: "query_database", tool_input: { query: "SELECT * FROM orders WHERE status = 'pending' LIMIT 100" } },
    ],
    created_at: minutesAgo(8), status: "pending", timeout_at: minutesAfter(minutesAgo(8), 30),
  },
  {
    id: "appr-002", tool_call_id: "tc-002", tool_name: "send_email",
    arguments: { to: "team@company.com", subject: "Urgent: Inventory Alert", body: "SKU-100 is critically low." },
    run_id: RUN_IDS[16], function_id: FN_IDS.generateReport,
    agent_conversation: [
      { role: "assistant", content: "I should notify the team about the low inventory." },
    ],
    created_at: minutesAgo(3), status: "pending", timeout_at: minutesAfter(minutesAgo(3), 60),
  },
];

// ── Usage Data ───────────────────────────────────────────────────────
export const mockUsageSummary: UsageSummary = {
  total_requests: 342,
  total_tokens: 52400,
  prompt_tokens: 38200,
  completion_tokens: 14200,
  total_cost_usd: 2.34,
  avg_latency_ms: 340,
  period_start: daysAgo(30),
  period_end: new Date().toISOString(),
};

export const mockDailyUsage: DailyUsage[] = Array.from({ length: 14 }, (_, i) => {
  const base = 20 + Math.floor(Math.random() * 15);
  return {
    date: daysAgo(13 - i).split("T")[0],
    requests: base,
    total_tokens: base * 150 + Math.floor(Math.random() * 500),
    cost_usd: parseFloat((base * 0.007 + Math.random() * 0.05).toFixed(3)),
  };
});

export const mockUsageByProvider: UsageByProvider[] = [
  { provider: "openai", requests: 240, total_tokens: 36800, cost_usd: 1.64, avg_latency_ms: 310 },
  { provider: "anthropic", requests: 102, total_tokens: 15600, cost_usd: 0.70, avg_latency_ms: 395 },
];

export const mockUsageByModel: UsageByModel[] = [
  { model: "gpt-4o", provider: "openai", requests: 150, total_tokens: 28000, cost_usd: 1.12, avg_latency_ms: 380 },
  { model: "gpt-4o-mini", provider: "openai", requests: 90, total_tokens: 8800, cost_usd: 0.52, avg_latency_ms: 210 },
  { model: "claude-sonnet-4-20250514", provider: "anthropic", requests: 102, total_tokens: 15600, cost_usd: 0.70, avg_latency_ms: 395 },
];

// ── Audit Logs ───────────────────────────────────────────────────────
export const mockAuditLogs = [
  { id: "aud-001", timestamp: minutesAgo(15), tenant_id: TENANT_ID, actor_id: USER_IDS.admin, actor_type: "user", actor_display: "Alex Rivera", action: "login_success", resource_type: null, resource_id: null, resource_display: null, details: { method: "password" }, ip_address: "192.168.1.100", user_agent: "Mozilla/5.0", correlation_id: null, success: true, error_message: null },
  { id: "aud-002", timestamp: hoursAgo(2), tenant_id: TENANT_ID, actor_id: USER_IDS.admin, actor_type: "user", actor_display: "Alex Rivera", action: "function_created", resource_type: "function", resource_id: FN_IDS.generateReport, resource_display: "Generate Weekly Report", details: { trigger_type: "cron" }, ip_address: "192.168.1.100", user_agent: "Mozilla/5.0", correlation_id: null, success: true, error_message: null },
  { id: "aud-003", timestamp: hoursAgo(5), tenant_id: TENANT_ID, actor_id: USER_IDS.admin, actor_type: "user", actor_display: "Alex Rivera", action: "api_key_created", resource_type: "api_key", resource_id: "key-001", resource_display: "Production API Key", details: { key_type: "live" }, ip_address: "192.168.1.100", user_agent: "Mozilla/5.0", correlation_id: null, success: true, error_message: null },
  { id: "aud-004", timestamp: hoursAgo(8), tenant_id: TENANT_ID, actor_id: USER_IDS.admin, actor_type: "user", actor_display: "Alex Rivera", action: "user_role_changed", resource_type: "user", resource_id: USER_IDS.member, resource_display: "Sarah Kim", details: { old_role: "viewer", new_role: "member" }, ip_address: "192.168.1.100", user_agent: "Mozilla/5.0", correlation_id: null, success: true, error_message: null },
  { id: "aud-005", timestamp: hoursAgo(12), tenant_id: TENANT_ID, actor_id: USER_IDS.admin, actor_type: "user", actor_display: "Alex Rivera", action: "provider_created", resource_type: "ai_provider", resource_id: "prov-002", resource_display: "Anthropic", details: { provider_name: "anthropic" }, ip_address: "192.168.1.100", user_agent: "Mozilla/5.0", correlation_id: null, success: true, error_message: null },
  { id: "aud-006", timestamp: daysAgo(1), tenant_id: TENANT_ID, actor_id: USER_IDS.member, actor_type: "user", actor_display: "Sarah Kim", action: "login_success", resource_type: null, resource_id: null, resource_display: null, details: { method: "password" }, ip_address: "10.0.0.25", user_agent: "Mozilla/5.0", correlation_id: null, success: true, error_message: null },
  { id: "aud-007", timestamp: daysAgo(1), tenant_id: TENANT_ID, actor_id: USER_IDS.member, actor_type: "user", actor_display: "Sarah Kim", action: "tool_created", resource_type: "tool", resource_id: "tool-005", resource_display: "generate_pdf", details: { tool_type: "custom" }, ip_address: "10.0.0.25", user_agent: "Mozilla/5.0", correlation_id: null, success: true, error_message: null },
  { id: "aud-008", timestamp: daysAgo(2), tenant_id: TENANT_ID, actor_id: null, actor_type: "system", actor_display: "System", action: "rate_limit_exceeded", resource_type: null, resource_id: null, resource_display: null, details: { endpoint: "/api/v1/events", limit: 100 }, ip_address: "203.0.113.50", user_agent: "python-requests/2.31", correlation_id: null, success: false, error_message: "Rate limit exceeded: 100 req/min" },
  { id: "aud-009", timestamp: daysAgo(3), tenant_id: TENANT_ID, actor_id: USER_IDS.admin, actor_type: "user", actor_display: "Alex Rivera", action: "function_updated", resource_type: "function", resource_id: FN_IDS.processOrder, resource_display: "Process Order", details: { changed_fields: ["tools_config", "agent_config"] }, ip_address: "192.168.1.100", user_agent: "Mozilla/5.0", correlation_id: null, success: true, error_message: null },
  { id: "aud-010", timestamp: daysAgo(4), tenant_id: TENANT_ID, actor_id: null, actor_type: "api_key", actor_display: "ff_live_a1b2", action: "login_failed", resource_type: null, resource_id: null, resource_display: null, details: { reason: "Invalid credentials" }, ip_address: "198.51.100.10", user_agent: "curl/8.1", correlation_id: null, success: false, error_message: "Authentication failed" },
];

// ── Credentials ──────────────────────────────────────────────────────
export const mockCredentials: Credential[] = [
  { id: "cred-001", name: "Stripe API Key", credential_type: "api_key", value_prefix: "sk_live_...abc", description: "Production Stripe API key for payment processing", is_active: true, created_at: daysAgo(40), updated_at: daysAgo(5) },
  { id: "cred-002", name: "SendGrid Token", credential_type: "bearer_token", value_prefix: "SG....xyz", description: "SendGrid API token for transactional emails", is_active: true, created_at: daysAgo(35), updated_at: daysAgo(10) },
];

// ── Model Pricing ────────────────────────────────────────────────────
export const mockModelPricingConfigs: ModelPricingConfig[] = [
  { id: "mp-001", model_id: "gpt-4o", provider: "openai", input_price_per_m: 2.50, output_price_per_m: 10.00, display_name: "GPT-4o", is_active: true, is_global: false, created_at: daysAgo(20), updated_at: daysAgo(5) },
  { id: "mp-002", model_id: "claude-sonnet-4-20250514", provider: "anthropic", input_price_per_m: 3.00, output_price_per_m: 15.00, display_name: "Claude Sonnet", is_active: true, is_global: false, created_at: daysAgo(20), updated_at: daysAgo(5) },
  { id: "mp-003", model_id: "gpt-4o-mini", provider: "openai", input_price_per_m: 0.15, output_price_per_m: 0.60, display_name: "GPT-4o Mini", is_active: true, is_global: false, created_at: daysAgo(15), updated_at: daysAgo(5) },
  { id: "mp-004", model_id: "claude-haiku-4-5-20251001", provider: "anthropic", input_price_per_m: 0.80, output_price_per_m: 4.00, display_name: "Claude Haiku", is_active: true, is_global: false, created_at: daysAgo(15), updated_at: daysAgo(5) },
];

export const mockEffectiveModelPricing: EffectiveModelPricing[] = mockModelPricingConfigs.map((c) => ({
  model_id: c.model_id,
  provider: c.provider,
  input_price_per_m: c.input_price_per_m,
  output_price_per_m: c.output_price_per_m,
  display_name: c.display_name,
  source: "tenant" as const,
  pricing_id: c.id,
}));

export const mockDefaultModelPricing: DefaultModelPricing[] = [
  { model_id: "gpt-4o", provider: "openai", input_price_per_m: 2.50, output_price_per_m: 10.00 },
  { model_id: "gpt-4o-mini", provider: "openai", input_price_per_m: 0.15, output_price_per_m: 0.60 },
  { model_id: "claude-sonnet-4-20250514", provider: "anthropic", input_price_per_m: 3.00, output_price_per_m: 15.00 },
  { model_id: "claude-haiku-4-5-20251001", provider: "anthropic", input_price_per_m: 0.80, output_price_per_m: 4.00 },
];

// ── Known Providers ──────────────────────────────────────────────────
export const mockKnownProviders = [
  { name: "openai", display_name: "OpenAI", models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"], default_model: "gpt-4o" },
  { name: "anthropic", display_name: "Anthropic", models: ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"], default_model: "claude-sonnet-4-20250514" },
  { name: "google", display_name: "Google AI", models: ["gemini-1.5-pro", "gemini-1.5-flash"], default_model: "gemini-1.5-pro" },
  { name: "mistral", display_name: "Mistral AI", models: ["mistral-large-latest", "mistral-medium-latest"], default_model: "mistral-large-latest" },
];
