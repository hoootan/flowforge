'use client';

import { use, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, RotateCw, StopCircle, Share2, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';
import { api, type RunWithSteps, type Step } from '@/lib/api';
import { useRunStream } from '@/hooks/useRunStream';
import { VarStrip } from '@/components/ui/var-strip';
import { CodeBlock } from '@/components/ui/code-block';

type TimelineMode = 'gantt' | 'flame' | 'swim' | 'graph';
type StepRender = 'notebook' | 'thread' | 'ide' | 'terminal';

function statusBadge(s: string): string {
  if (s === 'completed') return 'status-badge ok';
  if (s === 'failed') return 'status-badge fail';
  if (s === 'running') return 'status-badge run';
  if (s === 'pending' || s === 'paused' || s === 'sleeping' || s === 'waiting') return 'status-badge warn';
  if (s === 'cancelled') return 'status-badge cancel';
  return 'status-badge';
}

function stepBarType(t: Step['step_type']): string {
  if (t === 'ai') return 'ai';
  if (t === 'run') return 'run';
  if (t === 'sleep') return 'sleep';
  if (t === 'wait_for_event' || t === 'invoke' || t === 'send_event') return 'wait';
  if (t === 'sub_agent' || t === 'agent') return 'tool';
  return 'run';
}

function fmtDuration(start?: string | null, end?: string | null, fallback = '—'): string {
  if (!start) return fallback;
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const ms = e - s;
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`;
}

export default function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [run, setRun] = useState<RunWithSteps | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeline, setTimeline] = useState<TimelineMode>('gantt');
  const [stepRender, setStepRender] = useState<StepRender>('notebook');
  const [selectedStep, setSelectedStep] = useState<Step | null>(null);

  const fetchRun = useCallback(async () => {
    const data = await api.getRun(id);
    setRun(data);
    return data;
  }, [id]);

  useEffect(() => {
    setLoading(true);
    fetchRun().finally(() => setLoading(false));
  }, [fetchRun]);

  const isActive = run?.status === 'running' || run?.status === 'pending' || run?.status === 'paused';

  const refetchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debouncedFetchRun = useCallback(() => {
    if (refetchTimer.current) clearTimeout(refetchTimer.current);
    refetchTimer.current = setTimeout(() => fetchRun(), 300);
  }, [fetchRun]);

  const { isConnected } = useRunStream({
    runId: id,
    enabled: isActive,
    onEvent: () => debouncedFetchRun()
  });

  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(() => fetchRun(), isConnected ? 10000 : 3000);
    return () => clearInterval(interval);
  }, [isActive, isConnected, fetchRun]);

  const handleReplay = async () => {
    const result = await api.replayRun(id);
    if (result?.id) window.location.href = `/runs/${result.id}`;
  };

  const handleCancel = async () => {
    const result = await api.cancelRun(id);
    if (result?.success) {
      toast.success('Run cancelled');
      fetchRun();
    } else toast.error('Failed to cancel');
  };

  const canCancel = isActive;

  if (loading || !run) {
    return (
      <div>
        <div className="page-hd">
          <div>
            <Link href="/runs" className="btn btn-sm"><ArrowLeft size={12} /> Runs</Link>
            <h1 style={{ marginTop: 12 }}>Loading run…</h1>
          </div>
        </div>
        <div className="hint">Fetching run details…</div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-hd">
        <div>
          <Link href="/runs" className="btn btn-sm" style={{ marginBottom: 8 }}>
            <ArrowLeft size={12} /> Runs
          </Link>
          <h1>
            <span className="mono" style={{ fontSize: 20 }}>#{run.id.slice(0, 8)}</span>{' '}
            <em>· {run.function_id}</em>
          </h1>
          <div style={{ display: 'flex', gap: 12, marginTop: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span className={statusBadge(run.status)}>{run.status}</span>
            {isActive && isConnected && <span className="tag tag-running">Live</span>}
          </div>
        </div>
        <div className="page-hd-right">
          <button className="btn"><FileText size={12} /> Logs</button>
          <button className="btn"><Share2 size={12} /> Share</button>
          {canCancel && (
            <button className="btn btn-danger" onClick={handleCancel}>
              <StopCircle size={12} /> Cancel
            </button>
          )}
          <button className="btn btn-primary" onClick={handleReplay}>
            <RotateCw size={12} /> Replay
          </button>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="panel-body">
          <div className="meta-grid">
            <div>
              <label>Function</label>
              <span className="v">{run.function_id}</span>
            </div>
            <div>
              <label>Trigger</label>
              <span className="v">{run.event_id ? 'event' : 'manual'}</span>
            </div>
            <div>
              <label>Duration</label>
              <span className="v">{fmtDuration(run.started_at, run.ended_at)}</span>
            </div>
            <div>
              <label>Steps</label>
              <span className="v">{run.steps?.length ?? 0}</span>
            </div>
            <div>
              <label>Started</label>
              <span className="v">{run.started_at ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true }) : '—'}</span>
            </div>
            <div>
              <label>Run ID</label>
              <span className="v">{run.id}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="panel-head">
          <div>
            <div className="panel-title">Execution timeline</div>
            <div className="panel-sub">{run.steps?.length ?? 0} steps</div>
          </div>
          <div className="panel-right">
            <VarStrip
              value={timeline}
              onChange={setTimeline}
              options={[
                { value: 'gantt', label: 'Gantt' },
                { value: 'flame', label: 'Flame' },
                { value: 'swim', label: 'Swim' },
                { value: 'graph', label: 'Graph' }
              ]}
            />
          </div>
        </div>
        <Timeline run={run} mode={timeline} onSelectStep={setSelectedStep} selected={selectedStep} />
      </div>

      {/* Steps + inspector */}
      <div className="split-2">
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">Steps</div>
            <div className="panel-sub">Ordered by execution</div>
          </div>
          <table className="ff-table">
            <thead>
              <tr>
                <th></th>
                <th>Step</th>
                <th>Type</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Attempt</th>
              </tr>
            </thead>
            <tbody>
              {run.steps?.length === 0 && (
                <tr><td colSpan={6} className="hint" style={{ padding: 14 }}>No steps yet.</td></tr>
              )}
              {run.steps?.map((s) => (
                <tr
                  key={s.id}
                  className="is-clickable"
                  onClick={() => setSelectedStep(s)}
                  style={selectedStep?.id === s.id ? { background: 'var(--bg-2)' } : undefined}
                >
                  <td><span className={`dot ${s.status === 'completed' ? 'dot-ok' : s.status === 'failed' ? 'dot-fail' : s.status === 'running' ? 'dot-run' : 'dot-warn'}`} /></td>
                  <td className="td-id"><b>{s.step_id}</b></td>
                  <td><span className={`tag ${s.step_type === 'ai' ? 'tag-violet' : s.step_type === 'sleep' ? 'tag-warn' : s.step_type === 'wait_for_event' ? 'tag-info' : 'tag-ok'}`}>{s.step_type}</span></td>
                  <td><span className={statusBadge(s.status)}>{s.status}</span></td>
                  <td className="mono">{fmtDuration(s.started_at, s.ended_at, '—')}</td>
                  <td className="mono">{s.attempt}/{s.max_attempts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel" style={{ position: 'sticky', top: 64 }}>
          <div className="panel-head">
            <div>
              <div className="panel-title">Inspector</div>
              <div className="panel-sub">{selectedStep ? selectedStep.step_id : 'Select a step'}</div>
            </div>
            {selectedStep && (
              <div className="panel-right">
                <VarStrip
                  value={stepRender}
                  onChange={setStepRender}
                  options={[
                    { value: 'notebook', label: 'NB' },
                    { value: 'terminal', label: 'TERM' },
                    { value: 'thread', label: 'THR' },
                    { value: 'ide', label: 'IDE' }
                  ]}
                />
              </div>
            )}
          </div>
          <div className="panel-body">
            {!selectedStep && <div className="hint">Click a step on the left to inspect.</div>}
            {selectedStep && <StepInspector step={selectedStep} mode={stepRender} />}
          </div>
        </div>
      </div>
    </div>
  );
}

function Timeline({ run, mode, onSelectStep, selected }: { run: RunWithSteps; mode: TimelineMode; onSelectStep: (s: Step) => void; selected: Step | null }) {
  const steps = run.steps ?? [];
  const range = useMemo(() => {
    const starts = steps.map((s) => s.started_at ? new Date(s.started_at).getTime() : null).filter(Boolean) as number[];
    const ends = steps.map((s) => s.ended_at ? new Date(s.ended_at).getTime() : Date.now()).filter(Boolean) as number[];
    const min = starts.length ? Math.min(...starts) : 0;
    const max = ends.length ? Math.max(...ends) : 1;
    return { min, max, span: Math.max(1, max - min) };
  }, [steps]);

  if (steps.length === 0) {
    return <div className="panel-body"><div className="hint">No steps to visualize yet.</div></div>;
  }

  if (mode === 'gantt') {
    return (
      <div className="timeline">
        <div className="timeline-track">
          {steps.map((s) => {
            const start = s.started_at ? new Date(s.started_at).getTime() : range.min;
            const end = s.ended_at ? new Date(s.ended_at).getTime() : Date.now();
            const left = ((start - range.min) / range.span) * 100;
            const width = Math.max(2, ((end - start) / range.span) * 100);
            return (
              <div key={s.id} className="timeline-row" onClick={() => onSelectStep(s)} style={{ cursor: 'pointer', opacity: selected?.id === s.id ? 1 : 0.95 }}>
                <span className="name" title={s.step_id}>{s.step_id}</span>
                <div className="timeline-track-line">
                  <div className={`timeline-bar ${stepBarType(s.step_type)}${s.status === 'failed' ? ' error' : ''}`} style={{ left: `${left}%`, width: `${width}%` }}>
                    {fmtDuration(s.started_at, s.ended_at, '')}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (mode === 'flame') {
    return (
      <div className="timeline">
        {steps.map((s, i) => {
          const start = s.started_at ? new Date(s.started_at).getTime() : range.min;
          const end = s.ended_at ? new Date(s.ended_at).getTime() : Date.now();
          const left = ((start - range.min) / range.span) * 100;
          const width = Math.max(4, ((end - start) / range.span) * 100);
          return (
            <div key={s.id} style={{ position: 'relative', height: 24, marginBottom: 2 }}>
              <div className={`timeline-bar ${stepBarType(s.step_type)}${s.status === 'failed' ? ' error' : ''}`}
                   onClick={() => onSelectStep(s)}
                   style={{ position: 'absolute', left: `${left}%`, width: `${width}%`, top: 0, bottom: 0, cursor: 'pointer' }}>
                {s.step_id}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="panel-body">
      <div className="hint">{mode === 'swim' ? 'Swim' : 'Graph'} view coming soon — try Gantt or Flame.</div>
    </div>
  );
}

type AiOutput = {
  content?: string;
  model?: string;
  provider?: string;
  usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number; cost_usd?: number; latency_ms?: number };
  finish_reason?: string;
  tool_calls?: Array<{ id?: string; function?: { name?: string; arguments?: unknown } }>;
};

type AgentOutput = {
  output?: string;
  status?: string;
  iterations?: number;
  tool_calls_count?: number;
  tokens_used?: number;
  messages?: Array<{ role?: string; content?: unknown; name?: string; tool_calls?: unknown }>;
  tool_calls?: unknown[];
};

type AiInput = {
  model?: string;
  messages?: Array<{ role?: string; content?: unknown }>;
  temperature?: number;
  max_tokens?: number;
  tools?: unknown[];
  tool_choice?: unknown;
};

function isAiOutput(o: unknown): o is AiOutput {
  return !!o && typeof o === 'object' && 'usage' in (o as object) && 'model' in (o as object);
}

function isAgentOutput(o: unknown): o is AgentOutput {
  return !!o && typeof o === 'object' && Array.isArray((o as AgentOutput).messages) && 'iterations' in (o as object);
}

function isAiInput(i: unknown): i is AiInput {
  return !!i && typeof i === 'object' && Array.isArray((i as AiInput).messages) && 'model' in (i as object);
}

function stringifyMessageContent(c: unknown): string {
  if (typeof c === 'string') return c;
  if (c == null) return '';
  return JSON.stringify(c, null, 2);
}

function looksLikeJson(s: string): boolean {
  const t = s.trim();
  return t.startsWith('{') || t.startsWith('[');
}

function RawToggle({ value }: { value: unknown }) {
  return (
    <details style={{ marginTop: 8 }}>
      <summary className="kicker" style={{ cursor: 'pointer', userSelect: 'none' }}>Raw JSON</summary>
      <div style={{ marginTop: 6 }}>
        <CodeBlock language="json" code={JSON.stringify(value, null, 2)} />
      </div>
    </details>
  );
}

function MessageThread({ messages }: { messages: Array<{ role?: string; content?: unknown; name?: string }> }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {messages.map((m, idx) => {
        const role = m.role || 'message';
        const text = stringifyMessageContent(m.content);
        return (
          <div key={idx} style={{ borderLeft: '2px solid var(--line)', paddingLeft: 10 }}>
            <div className="kicker" style={{ marginBottom: 4 }}>
              {role}{m.name ? ` · ${m.name}` : ''}
            </div>
            {looksLikeJson(text) ? (
              <CodeBlock language="json" code={text} />
            ) : (
              <pre className="snip" style={{ whiteSpace: 'pre-wrap' }}>{text || <em className="hint">(empty)</em>}</pre>
            )}
          </div>
        );
      })}
    </div>
  );
}

function AiResponseCard({ output }: { output: AiOutput }) {
  const content = output.content ?? '';
  const usage = output.usage ?? {};
  const toolCalls = output.tool_calls ?? [];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div className="kicker" style={{ color: 'var(--brand)' }}>AI Response</div>

      <div>
        <div className="kicker" style={{ marginBottom: 4 }}>Content</div>
        {content ? (
          looksLikeJson(content) ? (
            <CodeBlock language="json" code={content} />
          ) : (
            <pre className="snip" style={{ whiteSpace: 'pre-wrap' }}>{content}</pre>
          )
        ) : (
          <div className="hint">(no content)</div>
        )}
      </div>

      {toolCalls.length > 0 && (
        <div>
          <div className="kicker" style={{ marginBottom: 4 }}>Tool Calls ({toolCalls.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {toolCalls.map((tc, idx) => {
              const name = tc.function?.name ?? '(unnamed)';
              const args = tc.function?.arguments;
              const argsStr = typeof args === 'string' ? args : JSON.stringify(args ?? {}, null, 2);
              return (
                <div key={tc.id ?? idx} style={{ borderLeft: '2px solid var(--brand)', paddingLeft: 10 }}>
                  <div className="mono" style={{ fontSize: 12, marginBottom: 4 }}><b>{name}</b></div>
                  <CodeBlock language="json" code={argsStr} />
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', fontSize: 11 }}>
        {output.model && <span className="tag tag-violet">{output.model}</span>}
        {usage.total_tokens != null && (
          <span className="tag tag-info">
            {usage.prompt_tokens ?? 0}→{usage.completion_tokens ?? 0} ({usage.total_tokens} tok)
          </span>
        )}
        {usage.cost_usd != null && <span className="tag">${usage.cost_usd.toFixed(6)}</span>}
        {usage.latency_ms != null && <span className="tag">{usage.latency_ms}ms</span>}
        {output.finish_reason && <span className="tag">{output.finish_reason}</span>}
      </div>

      <RawToggle value={output} />
    </div>
  );
}

function AgentConversationCard({ output }: { output: AgentOutput }) {
  const messages = output.messages ?? [];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div className="kicker" style={{ color: 'var(--brand)' }}>Agent Conversation</div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', fontSize: 11 }}>
        {output.status && <span className="tag tag-ok">{output.status}</span>}
        {output.iterations != null && <span className="tag">{output.iterations} iter</span>}
        {output.tool_calls_count != null && <span className="tag tag-info">{output.tool_calls_count} tool calls</span>}
        {output.tokens_used != null && <span className="tag">{output.tokens_used} tok</span>}
      </div>

      {output.output && (
        <div>
          <div className="kicker" style={{ marginBottom: 4 }}>Final Output</div>
          {looksLikeJson(output.output) ? (
            <CodeBlock language="json" code={output.output} />
          ) : (
            <pre className="snip" style={{ whiteSpace: 'pre-wrap' }}>{output.output}</pre>
          )}
        </div>
      )}

      {messages.length > 0 && (
        <div>
          <div className="kicker" style={{ marginBottom: 4 }}>Messages ({messages.length})</div>
          <MessageThread messages={messages} />
        </div>
      )}

      <RawToggle value={output} />
    </div>
  );
}

function AiInputCard({ input }: { input: AiInput }) {
  const messages = input.messages ?? [];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div className="kicker">AI Request</div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', fontSize: 11 }}>
        {input.model && <span className="tag tag-violet">{input.model}</span>}
        {input.temperature != null && <span className="tag">temp {input.temperature}</span>}
        {input.max_tokens != null && <span className="tag">max {input.max_tokens} tok</span>}
        {Array.isArray(input.tools) && input.tools.length > 0 && (
          <span className="tag tag-info">{input.tools.length} tools</span>
        )}
      </div>

      {messages.length > 0 && (
        <div>
          <div className="kicker" style={{ marginBottom: 4 }}>Messages ({messages.length})</div>
          <MessageThread messages={messages} />
        </div>
      )}

      <RawToggle value={input} />
    </div>
  );
}

function InputBlock({ step }: { step: Step }) {
  if (!step.input) return null;
  if (isAiInput(step.input)) {
    return <AiInputCard input={step.input} />;
  }
  return (
    <div>
      <div className="kicker">Input</div>
      <CodeBlock language="json" code={JSON.stringify(step.input, null, 2)} />
    </div>
  );
}

function OutputBlock({ step }: { step: Step }) {
  if (!step.output) return null;
  if (isAiOutput(step.output)) {
    return <AiResponseCard output={step.output as AiOutput} />;
  }
  if (isAgentOutput(step.output)) {
    return <AgentConversationCard output={step.output as AgentOutput} />;
  }
  return (
    <div>
      <div className="kicker">Output</div>
      <CodeBlock language="json" code={JSON.stringify(step.output, null, 2)} />
    </div>
  );
}

function StepInspector({ step, mode }: { step: Step; mode: StepRender }) {
  const errorJson = step.error ? JSON.stringify(step.error, null, 2) : '';
  const outputJson = step.output ? JSON.stringify(step.output, null, 2) : '';

  if (mode === 'terminal') {
    return (
      <div>
        <div className="kicker" style={{ marginBottom: 8 }}>$ stdout</div>
        <pre className="snip" style={{ background: '#000' }}>
          {outputJson || (errorJson ? `! ERROR\n${errorJson}` : '<no output>')}
        </pre>
      </div>
    );
  }

  if (mode === 'thread') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {step.input && (
          <div>
            <div className="kicker" style={{ marginBottom: 6 }}>→ Input</div>
            <InputBlock step={step} />
          </div>
        )}
        {step.output && (
          <div>
            <div className="kicker" style={{ color: 'var(--brand)', marginBottom: 6 }}>← Output</div>
            <OutputBlock step={step} />
          </div>
        )}
        {step.error && (
          <div>
            <div className="kicker" style={{ color: 'var(--danger)' }}>! Error</div>
            <CodeBlock language="json" code={errorJson} />
          </div>
        )}
      </div>
    );
  }

  // notebook + ide: input | output side-by-side, collapses to single column when narrow
  const hasInput = !!step.input;
  const hasOutput = !!step.output;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div className="meta-grid" style={{ paddingBottom: 12, borderBottom: '1px solid var(--line)' }}>
        <div><label>Type</label><span className="v">{step.step_type}</span></div>
        <div><label>Status</label><span className="v">{step.status}</span></div>
        <div><label>Attempt</label><span className="v">{step.attempt}/{step.max_attempts}</span></div>
        <div><label>Duration</label><span className="v">{fmtDuration(step.started_at, step.ended_at)}</span></div>
      </div>
      {(hasInput || hasOutput) && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: hasInput && hasOutput ? 'repeat(auto-fit, minmax(320px, 1fr))' : '1fr',
            gap: 14,
            alignItems: 'start',
          }}
        >
          {hasInput && <InputBlock step={step} />}
          {hasOutput && <OutputBlock step={step} />}
        </div>
      )}
      {step.error && (
        <div>
          <div className="kicker" style={{ color: 'var(--danger)' }}>Error</div>
          <CodeBlock language="json" code={errorJson} />
        </div>
      )}
    </div>
  );
}
