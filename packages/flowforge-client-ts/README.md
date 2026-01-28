# FlowForge TypeScript Client

A type-safe, Supabase-style TypeScript client for interacting with FlowForge server from Node.js, Next.js, or any JavaScript runtime.

## Installation

```bash
npm install flowforge-client
# or
pnpm add flowforge-client
```

## Quick Start

```typescript
import { createClient } from 'flowforge-client';

const ff = createClient('http://localhost:8000');

// All methods return { data, error } - never throws
const { data, error } = await ff.events.send('order/created', {
  order_id: '123',
  customer: 'Alice',
  total: 99.99
});

if (error) {
  console.error('Failed to send event:', error.message);
} else {
  console.log('Event ID:', data.id);
  console.log('Triggered runs:', data.runs);
}

// Wait for the run to complete
const { data: run } = await ff.runs.waitFor(data.runs[0].id);
console.log('Run output:', run?.output);
```

## Usage in Next.js

### Server Actions

```typescript
// app/actions.ts
'use server'

import { createClient } from 'flowforge-client';

const ff = createClient(process.env.FLOWFORGE_URL!);

export async function submitOrder(formData: FormData) {
  const { data, error } = await ff.events.send('order/created', {
    customer: formData.get('customer'),
    items: JSON.parse(formData.get('items') as string),
  });

  if (error) throw new Error(error.message);
  return { eventId: data.id, runId: data.runs[0]?.id };
}
```

### API Routes

```typescript
// app/api/workflow/route.ts
import { createClient } from 'flowforge-client';
import { NextResponse } from 'next/server';

const ff = createClient(process.env.FLOWFORGE_URL!);

export async function POST(request: Request) {
  const payload = await request.json();
  const { data, error } = await ff.events.send('user/signup', payload);

  if (error) {
    return NextResponse.json({ error: error.message }, { status: error.status });
  }

  return NextResponse.json({
    eventId: data.id,
    runs: data.runs,
  });
}
```

## API Reference

### Creating a Client

```typescript
import { createClient } from 'flowforge-client';

// Simple URL
const ff = createClient('http://localhost:8000');

// With options
const ff = createClient('http://localhost:8000', {
  apiKey: 'your-api-key',        // Optional
  tenantId: 'tenant-123',        // Optional (multi-tenant)
});
```

### Events

```typescript
// Send an event
const { data, error } = await ff.events.send('order/created', { order_id: '123' });

// With options
const { data } = await ff.events.send('order/created', { order_id: '123' }, {
  id: 'custom-event-id',
  user_id: 'user-456',
});

// Get an event
const { data: event } = await ff.events.get('event-id');

// Query events with filters
const { data: events } = await ff.events
  .select()
  .eq('name', 'order/*')
  .limit(10)
  .execute();
```

### Runs

```typescript
// Get a run with its steps
const { data: run } = await ff.runs.get('run-id');
console.log(run.status);  // 'pending' | 'running' | 'completed' | 'failed'
console.log(run.steps);   // Array of step details

// Query runs with type-safe filters
const { data: runs } = await ff.runs
  .select()
  .eq('status', 'completed')
  .eq('function_id', 'process-order')
  .order('created_at', 'desc')
  .limit(10)
  .execute();

// Wait for completion (polling)
const { data: completedRun, error } = await ff.runs.waitFor('run-id', {
  timeout: 60000,  // 60 seconds
  interval: 1000,  // poll every second
});

// Cancel a run
await ff.runs.cancel('run-id');

// Replay a failed run
const { data: newRun } = await ff.runs.replay('run-id');
```

### Functions

```typescript
// Query functions with type-safe filters
const { data: fns } = await ff.functions
  .select()
  .eq('trigger_type', 'event')
  .eq('is_active', true)
  .execute();

// Get function details
const { data: fn } = await ff.functions.get('process-order');

// Create a new function
const { data: created } = await ff.functions.create({
  id: 'my-workflow',
  name: 'My Workflow',
  trigger_type: 'event',
  trigger_value: 'order/*',
  endpoint_url: 'http://localhost:3000/api/workflows/order',
});

// Update a function
await ff.functions.update('my-workflow', { is_active: false });

// Delete a function
await ff.functions.delete('my-workflow');
```

### Tools

```typescript
// Query tools
const { data: tools } = await ff.tools
  .select()
  .eq('requires_approval', true)
  .eq('is_active', true)
  .execute();

// Get a tool
const { data: tool } = await ff.tools.get('send-email');

// Create a tool
await ff.tools.create({
  name: 'send-email',
  description: 'Send an email to a recipient',
  parameters: {
    type: 'object',
    properties: {
      to: { type: 'string', description: 'Recipient email' },
      subject: { type: 'string' },
      body: { type: 'string' },
    },
    required: ['to', 'subject', 'body'],
  },
  requires_approval: true,
});

// Update a tool
await ff.tools.update('send-email', { requires_approval: false });

// Delete a tool
await ff.tools.delete('my-tool');
```

### Approvals (Human-in-the-Loop)

```typescript
// Query pending approvals
const { data: pending } = await ff.approvals
  .select()
  .eq('status', 'pending')
  .execute();

// Get approval details
const { data: approval } = await ff.approvals.get('approval-id');

// Approve a tool call
await ff.approvals.approve('approval-id');

// Approve with modified arguments
await ff.approvals.approve('approval-id', {
  modifiedArguments: { amount: 100 },
});

// Reject a tool call
await ff.approvals.reject('approval-id', 'Amount too high');
```

### Health & Stats

```typescript
// Check server health
const { data: healthy } = await ff.health.check();
if (healthy) console.log('Server is healthy');

// Get statistics
const { data: stats } = await ff.health.stats();
console.log(stats.runs.completed);
console.log(stats.queue.pending);
```

## Error Handling

All methods return `{ data, error }` and never throw. This makes error handling explicit and type-safe:

```typescript
import { createClient, FlowForgeError } from 'flowforge-client';

const ff = createClient('http://localhost:8000');

const { data, error } = await ff.events.send('order/created', {});

if (error) {
  console.error('API Error:', error.message);
  console.error('Status:', error.status);
  console.error('Code:', error.code);
  console.error('Details:', error.detail);
}
```

## TypeScript Types

All types are exported for your convenience:

```typescript
import type {
  // Core types
  Run,
  RunWithSteps,
  RunStatus,
  Step,
  StepType,
  StepStatus,
  Event,
  FlowForgeFunction,
  Tool,
  Approval,
  Stats,
  HealthStatus,
  TriggerType,
  ApprovalStatus,

  // Filter types (for type-safe queries)
  RunFilters,
  FunctionFilters,
  EventFilters,
  ToolFilters,
  ApprovalFilters,

  // Input types
  CreateFunctionInput,
  UpdateFunctionInput,
  CreateToolInput,
  UpdateToolInput,
  SendEventInput,

  // Result type
  Result,
  FlowForgeError,
  ClientOptions,
} from 'flowforge-client';
```

## Query Builder

The client uses a chainable query builder for filtering and pagination:

```typescript
// Available methods
ff.runs
  .select()                              // Start a query
  .eq('status', 'completed')             // Exact match filter
  .order('created_at', 'desc')           // Sort results
  .limit(10)                             // Limit results
  .offset(20)                            // Skip results (pagination)
  .execute();                            // Execute and return array

// Get a single result
const { data: run } = await ff.runs
  .select()
  .eq('function_id', 'my-fn')
  .single();
```

## License

MIT
