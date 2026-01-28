# Agent Dashboard Components

React components for visualizing FlowForge AI agent execution and managing tool call approvals.

## Components

### AgentRunView

Displays high-level agent execution summary with key metrics.

```tsx
import { AgentRunView } from "@/components/agent";

<AgentRunView agentResult={{
  output: "I found 3 restaurants...",
  status: "completed",
  iterations: 5,
  tool_calls_count: 8,
  tokens_used: 3420,
  messages: [...],
  tool_calls: [...]
}} />
```

**Features**:
- Agent status badge
- Final output text
- Stats grid: iterations, tool calls, tokens, estimated cost

### AgentTimeline

Timeline visualization of agent iterations with expandable tool calls.

```tsx
import { AgentTimeline } from "@/components/agent";

<AgentTimeline agentResult={{
  iterations: 5,
  messages: [...],
  tool_calls: [...]
}} />
```

**Features**:
- Iteration-by-iteration breakdown
- LLM thinking content per iteration
- Expandable tool call details
- Visual timeline connector
- Approval indicators

### ToolCallDetail

Detailed view of a single tool call with arguments, results, and approval status.

```tsx
import { ToolCallDetail } from "@/components/agent";

<ToolCallDetail toolCall={{
  id: "call_123",
  tool_name: "web_search",
  arguments: { query: "best restaurants NYC" },
  result: { results: [...] },
  execution_time_ms: 450,
  requires_approval: false
}} />
```

**Features**:
- JSON-formatted arguments
- Result or error display
- Execution time
- Approval status badge
- Rejection reason (if applicable)

### ApprovalInbox

List of pending approvals with approve/reject actions.

```tsx
import { ApprovalInbox } from "@/components/agent";
import { useApprovals, useApproveToolCall, useRejectToolCall } from "@/lib/hooks/useAgent";

function ApprovalsPage() {
  const { approvals, refetch } = useApprovals(true);
  const { approve } = useApproveToolCall();
  const { reject } = useRejectToolCall();

  const handleApprove = async (id: string) => {
    await approve(id);
    refetch();
  };

  const handleReject = async (id: string, reason: string) => {
    await reject(id, reason);
    refetch();
  };

  return (
    <ApprovalInbox
      approvals={approvals}
      onApprove={handleApprove}
      onReject={handleReject}
    />
  );
}
```

**Features**:
- Pending approvals list
- Tool arguments preview
- Agent conversation context
- Approve/Reject buttons
- Rejection reason dialog
- Empty state

## Hooks

### useAgentRun

Fetch a run with agent details.

```tsx
import { useAgentRun } from "@/lib/hooks/useAgent";

const { run, loading, error, refetch } = useAgentRun("run_123");
```

### useApprovals

Fetch pending approvals.

```tsx
import { useApprovals } from "@/lib/hooks/useAgent";

const { approvals, loading, error, refetch } = useApprovals(true);
```

### useApproveToolCall

Approve a tool call.

```tsx
import { useApproveToolCall } from "@/lib/hooks/useAgent";

const { approve, loading, error } = useApproveToolCall();
await approve("approval_123");
```

### useRejectToolCall

Reject a tool call with reason.

```tsx
import { useRejectToolCall } from "@/lib/hooks/useAgent";

const { reject, loading, error } = useRejectToolCall();
await reject("approval_123", "Insufficient permissions");
```

## Helpers

### hasAgentSteps

Check if a run contains agent steps.

```tsx
import { hasAgentSteps } from "@/lib/hooks/useAgent";

if (hasAgentSteps(run)) {
  // Render agent view
}
```

### extractAgentResult

Extract agent result from a run's step output.

```tsx
import { extractAgentResult } from "@/lib/hooks/useAgent";

const agentResult = extractAgentResult(run);
if (agentResult) {
  // Render AgentRunView, AgentTimeline
}
```

## Usage in Run Detail Page

```tsx
import { hasAgentSteps, extractAgentResult } from "@/lib/hooks/useAgent";
import { AgentRunView, AgentTimeline } from "@/components/agent";

export default function RunDetailPage({ params }) {
  const { id } = use(params);
  const [run, setRun] = useState<RunWithSteps | null>(null);

  const isAgentRun = hasAgentSteps(run);
  const agentResult = extractAgentResult(run);

  return (
    <div>
      {isAgentRun && agentResult ? (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <AgentTimeline agentResult={agentResult} />
          </div>
          <div>
            <AgentRunView agentResult={agentResult} />
          </div>
        </div>
      ) : (
        // Regular step-based view
      )}
    </div>
  );
}
```

## Styling

Components use Tailwind CSS and follow the existing dashboard design system:

- **shadcn/ui** primitives (Card, Badge, Button, etc.)
- **lucide-react** icons
- **Responsive layout** with grid/flex
- **Dark mode** support via next-themes
- **Consistent spacing** and typography

## Data Format

### AgentResult

```typescript
interface AgentResult {
  output: string;
  status: "completed" | "max_iterations" | "max_tool_calls" | "failed";
  iterations: number;
  tool_calls_count: number;
  tokens_used: number;
  messages: any[];
  tool_calls: any[];
}
```

### PendingApproval

```typescript
interface PendingApproval {
  id: string;
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  run_id: string;
  function_id: string;
  agent_conversation: any[];
  created_at: string;
}
```

## API Requirements

The components expect these API endpoints:

- `GET /api/v1/runs/{id}` - Returns run with agent step output
- `GET /api/v1/approvals?pending_only=true` - Returns pending approvals
- `POST /api/v1/approvals/{id}/approve` - Approves a tool call
- `POST /api/v1/approvals/{id}/reject` - Rejects a tool call

See API client at `/dashboard/src/lib/api.ts` for implementation details.
