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

function StepInspector({ step, mode }: { step: Step; mode: StepRender }) {
  const inputJson = step.input ? JSON.stringify(step.input, null, 2) : '';
  const outputJson = step.output ? JSON.stringify(step.output, null, 2) : '';
  const errorJson = step.error ? JSON.stringify(step.error, null, 2) : '';

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
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {step.input && (
          <div>
            <div className="kicker">→ Input</div>
            <CodeBlock language="json" code={inputJson} />
          </div>
        )}
        {step.output && (
          <div>
            <div className="kicker" style={{ color: 'var(--brand)' }}>← Output</div>
            <CodeBlock language="json" code={outputJson} />
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

  // notebook + ide
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div className="meta-grid" style={{ paddingBottom: 12, borderBottom: '1px solid var(--line)' }}>
        <div><label>Type</label><span className="v">{step.step_type}</span></div>
        <div><label>Status</label><span className="v">{step.status}</span></div>
        <div><label>Attempt</label><span className="v">{step.attempt}/{step.max_attempts}</span></div>
        <div><label>Duration</label><span className="v">{fmtDuration(step.started_at, step.ended_at)}</span></div>
      </div>
      {step.input && (
        <div>
          <div className="kicker">Input</div>
          <CodeBlock language="json" code={inputJson} />
        </div>
      )}
      {step.output && (
        <div>
          <div className="kicker">Output</div>
          <CodeBlock language="json" code={outputJson} />
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
