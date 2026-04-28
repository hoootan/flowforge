'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow } from 'date-fns';
import { RefreshCw, Search } from 'lucide-react';
import { api, type Run } from '@/lib/api';
import { VarStrip } from '@/components/ui/var-strip';

type View = 'table' | 'cards' | 'graph';
type StatusFilter = 'all' | 'completed' | 'failed' | 'running' | 'pending' | 'cancelled';

function statusTag(s: string) {
  if (s === 'completed') return 'tag tag-ok';
  if (s === 'failed') return 'tag tag-fail';
  if (s === 'running') return 'tag tag-running';
  if (s === 'pending' || s === 'paused') return 'tag tag-warn';
  return 'tag';
}

function statusDot(s: string) {
  if (s === 'completed') return 'dot-ok';
  if (s === 'failed') return 'dot-fail';
  if (s === 'running') return 'dot-run';
  if (s === 'pending' || s === 'paused') return 'dot-warn';
  return 'dot-muted';
}

function fmtDuration(r: Run): string {
  if (!r.started_at) return '—';
  const start = new Date(r.started_at).getTime();
  const end = r.ended_at ? new Date(r.ended_at).getTime() : Date.now();
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`;
}

export default function RunsPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<View>('table');
  const [status, setStatus] = useState<StatusFilter>('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    let cancelled = false;
    const fetch = async () => {
      try {
        const r = await api.getRuns({ page_size: 200, status: status === 'all' ? undefined : status });
        if (!cancelled) setRuns(r.runs);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetch();
    const id = setInterval(fetch, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [status]);

  const filtered = useMemo(() => {
    if (!search) return runs;
    const q = search.toLowerCase();
    return runs.filter((r) => r.id.toLowerCase().includes(q) || r.function_id?.toLowerCase().includes(q));
  }, [runs, search]);

  const counts = useMemo(() => {
    const c = { all: runs.length, completed: 0, failed: 0, running: 0, pending: 0, cancelled: 0 };
    for (const r of runs) {
      if (r.status in c) (c as Record<string, number>)[r.status]++;
    }
    return c;
  }, [runs]);

  return (
    <div>
      <div className="page-hd">
        <div>
          <h1>Runs <em>· every execution.</em></h1>
          <p>{filtered.length} run{filtered.length === 1 ? '' : 's'}{search ? ` matching "${search}"` : ''}</p>
        </div>
        <div className="page-hd-right">
          <VarStrip
            value={view}
            onChange={setView}
            options={[
              { value: 'table', label: 'Table' },
              { value: 'cards', label: 'Cards' },
              { value: 'graph', label: 'Graph' }
            ]}
          />
          <button className="btn" onClick={() => router.refresh()}>
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
        {/* Filter rail */}
        <aside style={{ width: 180, flex: 'none' }}>
          <div className="panel">
            <div className="panel-head">
              <div className="panel-title" style={{ fontSize: 12 }}>Status</div>
            </div>
            <div style={{ padding: 6 }}>
              {(['all', 'completed', 'failed', 'running', 'pending', 'cancelled'] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  className={`ff-side-link${status === s ? ' is-active' : ''}`}
                  onClick={() => setStatus(s)}
                  style={{ width: '100%', textTransform: 'capitalize' }}
                >
                  <span className={`dot ${s === 'all' ? 'dot-muted' : statusDot(s)}`} />
                  <span className="ff-side-link-text">{s}</span>
                  <span className="ff-side-link-badge">{counts[s] ?? 0}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="panel" style={{ marginTop: 12 }}>
            <div className="panel-head">
              <div className="panel-title" style={{ fontSize: 12 }}>Search</div>
            </div>
            <div className="panel-body" style={{ padding: 10 }}>
              <div style={{ position: 'relative' }}>
                <Search size={12} style={{ position: 'absolute', left: 8, top: 10, color: 'var(--ink-3)' }} />
                <input
                  className="field-input mono"
                  placeholder="run id, function…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{ paddingLeft: 26 }}
                />
              </div>
            </div>
          </div>
        </aside>

        {/* Main */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {view === 'table' && (
            <div className="panel">
              <table className="ff-table">
                <thead>
                  <tr>
                    <th style={{ width: 8 }}></th>
                    <th>Run ID</th>
                    <th>Function</th>
                    <th>Status</th>
                    <th>Trigger</th>
                    <th>Duration</th>
                    <th>Started</th>
                  </tr>
                </thead>
                <tbody>
                  {loading && (
                    <tr><td colSpan={7} className="hint" style={{ padding: 14 }}>Loading…</td></tr>
                  )}
                  {!loading && filtered.length === 0 && (
                    <tr><td colSpan={7} className="hint" style={{ padding: 14 }}>No runs found.</td></tr>
                  )}
                  {filtered.map((r) => (
                    <tr key={r.id} className="is-clickable" onClick={() => router.push(`/runs/${r.id}`)}>
                      <td><span className={`dot ${statusDot(r.status)}`} /></td>
                      <td className="td-id"><b>{r.id.slice(0, 8)}</b><span style={{ color: 'var(--ink-4)' }}>{r.id.slice(8, 14)}…</span></td>
                      <td className="mono">{r.function_id}</td>
                      <td><span className={statusTag(r.status)}>{r.status}</span></td>
                      <td className="mono" style={{ color: 'var(--ink-3)' }}>{r.event_id ? 'event' : 'manual'}</td>
                      <td className="mono">{fmtDuration(r)}</td>
                      <td className="mono" style={{ color: 'var(--ink-3)' }}>
                        {formatDistanceToNow(new Date(r.created_at), { addSuffix: true })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {view === 'cards' && (
            <div className="split-3">
              {loading && <div className="hint">Loading…</div>}
              {!loading && filtered.length === 0 && <div className="hint">No runs.</div>}
              {filtered.map((r) => (
                <Link key={r.id} href={`/runs/${r.id}`} className="panel" style={{ textDecoration: 'none' }}>
                  <div className="panel-body">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className={`dot ${statusDot(r.status)}`} />
                      <span className={statusTag(r.status)}>{r.status}</span>
                      <span className="mono" style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--ink-3)' }}>
                        {fmtDuration(r)}
                      </span>
                    </div>
                    <div className="mono" style={{ marginTop: 12, fontSize: 13, color: 'var(--ink-1)' }}>
                      {r.function_id}
                    </div>
                    <div className="mono" style={{ marginTop: 4, fontSize: 11, color: 'var(--ink-3)' }}>
                      #{r.id.slice(0, 12)}
                    </div>
                    <div className="mono" style={{ marginTop: 10, fontSize: 10.5, color: 'var(--ink-3)' }}>
                      {formatDistanceToNow(new Date(r.created_at), { addSuffix: true })}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {view === 'graph' && (
            <div className="panel">
              <div className="panel-head">
                <div className="panel-title">Graph view</div>
                <div className="panel-sub">Run volume by hour</div>
              </div>
              <div className="panel-body">
                <GraphView runs={filtered} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function GraphView({ runs }: { runs: Run[] }) {
  const buckets = useMemo(() => {
    const out: { ts: string; ok: number; fail: number; run: number }[] = [];
    const now = Date.now();
    for (let h = 23; h >= 0; h--) {
      const slotStart = now - (h + 1) * 3_600_000;
      const slotEnd = now - h * 3_600_000;
      const inSlot = runs.filter((r) => {
        const t = new Date(r.created_at).getTime();
        return t >= slotStart && t < slotEnd;
      });
      out.push({
        ts: new Date(slotEnd).getHours() + 'h',
        ok: inSlot.filter((r) => r.status === 'completed').length,
        fail: inSlot.filter((r) => r.status === 'failed').length,
        run: inSlot.filter((r) => r.status === 'running').length
      });
    }
    return out;
  }, [runs]);
  const max = Math.max(1, ...buckets.map((b) => b.ok + b.fail + b.run));
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 200, paddingTop: 16 }}>
      {buckets.map((b, i) => {
        const total = b.ok + b.fail + b.run;
        const h = (total / max) * 180;
        return (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
            <div style={{ height: h, width: '100%', background: 'var(--bg-3)', borderRadius: 2, position: 'relative', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
              {b.fail > 0 && <div style={{ background: 'var(--danger)', height: `${(b.fail / total) * 100}%` }} />}
              {b.run > 0 && <div style={{ background: 'var(--info)', height: `${(b.run / total) * 100}%` }} />}
              {b.ok > 0 && <div style={{ background: 'var(--accent)', height: `${(b.ok / total) * 100}%` }} />}
            </div>
            <span className="mono" style={{ fontSize: 9, color: 'var(--ink-3)' }}>{b.ts}</span>
          </div>
        );
      })}
    </div>
  );
}
