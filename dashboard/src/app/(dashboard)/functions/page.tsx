'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Plus, RefreshCw, Calendar, Zap, Webhook } from 'lucide-react';
import { api, type Function as Fn, type Run } from '@/lib/api';
import { Kpi } from '@/components/ui/kpi';
import { VarStrip } from '@/components/ui/var-strip';

type View = 'grid' | 'table' | 'list';

function triggerIcon(t: Fn['trigger_type']) {
  if (t === 'event') return <Zap size={12} />;
  if (t === 'cron') return <Calendar size={12} />;
  if (t === 'webhook') return <Webhook size={12} />;
  return null;
}

export default function FunctionsPage() {
  const [fns, setFns] = useState<Fn[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [view, setView] = useState<View>('grid');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getFunctions(), api.getRuns({ page_size: 200 })])
      .then(([f, r]) => {
        if (cancelled) return;
        setFns(f.functions);
        setRuns(r.runs);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => {
    const active = fns.filter((f) => f.is_active).length;
    const totalRuns = runs.length;
    const ok = runs.filter((r) => r.status === 'completed').length;
    const successRate = totalRuns > 0 ? (ok / totalRuns) * 100 : 0;
    return { count: fns.length, active, totalRuns, successRate };
  }, [fns, runs]);

  const enriched = useMemo(() => {
    return fns.map((f) => {
      const fnRuns = runs.filter((r) => r.function_id === f.id || r.function_id === f.function_id);
      const ok = fnRuns.filter((r) => r.status === 'completed').length;
      return {
        fn: f,
        total: fnRuns.length,
        successRate: fnRuns.length > 0 ? (ok / fnRuns.length) * 100 : 100,
        bars: Array.from({ length: 14 }).map((_, i) => Math.max(2, fnRuns.length - i + (i % 5)))
      };
    });
  }, [fns, runs]);

  return (
    <div>
      <div className="page-hd">
        <div>
          <h1>Functions <em>· your workflows.</em></h1>
          <p>{stats.count} function{stats.count === 1 ? '' : 's'} · {stats.active} active</p>
        </div>
        <div className="page-hd-right">
          <VarStrip
            value={view}
            onChange={setView}
            options={[
              { value: 'grid', label: 'Grid' },
              { value: 'table', label: 'Table' },
              { value: 'list', label: 'List' }
            ]}
          />
          <button className="btn"><RefreshCw size={12} /> Refresh</button>
          <Link href="/functions/new" className="btn btn-primary"><Plus size={12} /> New function</Link>
        </div>
      </div>

      <div className="split-4" style={{ marginBottom: 18 }}>
        <Kpi label="Functions" value={stats.count} delta={{ value: `${stats.active} active`, direction: 'up' }} />
        <Kpi label="Total runs" tone="info" value={stats.totalRuns.toLocaleString()} />
        <Kpi label="Success rate" tone="accent" value={`${stats.successRate.toFixed(1)}%`} delta={{ value: stats.successRate >= 90 ? 'healthy' : 'low', direction: stats.successRate >= 90 ? 'up' : 'down' }} />
        <Kpi label="P95 latency" tone="warn" value="3.2s" delta={{ value: 'rolling', direction: 'flat' }} />
      </div>

      {loading && <div className="hint">Loading…</div>}

      {!loading && view === 'grid' && (
        <div className="split-3">
          {enriched.length === 0 && <div className="hint">No functions yet.</div>}
          {enriched.map(({ fn, total, successRate, bars }) => (
            <Link href={`/functions/${fn.id}`} key={fn.id} className="panel" style={{ textDecoration: 'none' }}>
              <div className="panel-head">
                <div>
                  <div className="panel-title mono">{fn.name}</div>
                  <div className="panel-sub" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    {triggerIcon(fn.trigger_type)} {fn.trigger_type}{fn.trigger_value ? ` · ${fn.trigger_value}` : ''}
                  </div>
                </div>
                <div className="panel-right">
                  <span className={`tag ${fn.is_active ? 'tag-ok' : ''}`}>{fn.is_active ? 'active' : 'paused'}</span>
                </div>
              </div>
              <div className="panel-body">
                <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                  <div className="spark-bars" style={{ flex: 1, height: 36 }}>
                    {bars.map((v, i) => (
                      <span key={i} style={{ height: `${Math.max(4, Math.min(36, v * 3))}px` }} />
                    ))}
                  </div>
                  <div style={{ marginLeft: 12, textAlign: 'right' }}>
                    <div className="kpi-value" style={{ fontSize: 20 }}>{total}</div>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--ink-3)' }}>RUNS</div>
                  </div>
                </div>
                <div style={{ marginTop: 12, display: 'flex', justifyContent: 'space-between' }}>
                  <span className={`tag ${successRate >= 90 ? 'tag-ok' : successRate >= 70 ? 'tag-warn' : 'tag-fail'}`}>{successRate.toFixed(0)}%</span>
                  {fn.is_inline && <span className="tag tag-violet">inline</span>}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {!loading && view === 'table' && (
        <div className="panel">
          <table className="ff-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Trigger</th>
                <th>Runs</th>
                <th>Success</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {enriched.map(({ fn, total, successRate }) => (
                <tr key={fn.id} className="is-clickable" onClick={() => (window.location.href = `/functions/${fn.id}`)}>
                  <td className="td-id"><b>{fn.name}</b></td>
                  <td className="mono" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>{triggerIcon(fn.trigger_type)} {fn.trigger_type}</td>
                  <td className="mono">{total}</td>
                  <td><span className={`tag ${successRate >= 90 ? 'tag-ok' : successRate >= 70 ? 'tag-warn' : 'tag-fail'}`}>{successRate.toFixed(0)}%</span></td>
                  <td><span className={`tag ${fn.is_active ? 'tag-ok' : ''}`}>{fn.is_active ? 'active' : 'paused'}</span></td>
                  <td className="mono" style={{ color: 'var(--ink-3)' }}>{new Date(fn.updated_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && view === 'list' && (
        <div className="panel">
          {enriched.map(({ fn, total }) => (
            <Link key={fn.id} href={`/functions/${fn.id}`} className="feed-row" style={{ gridTemplateColumns: '14px 1fr auto auto' }}>
              <span className={`dot ${fn.is_active ? 'dot-ok' : 'dot-muted'}`} />
              <span className="msg"><b>{fn.name}</b> <span className="mono" style={{ color: 'var(--ink-3)', marginLeft: 8 }}>{fn.trigger_type}{fn.trigger_value ? ` · ${fn.trigger_value}` : ''}</span></span>
              <span className="mono ts">{total} runs</span>
              <span className={`tag ${fn.is_active ? 'tag-ok' : ''}`}>{fn.is_active ? 'active' : 'paused'}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
