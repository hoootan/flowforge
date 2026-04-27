'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { Activity, CheckCircle2, Zap, DollarSign, Box, Bot, ArrowRight } from 'lucide-react';
import { api, type Stats, type Run, type Function as FunctionType, type DailyUsage } from '@/lib/api';
import { Kpi } from '@/components/ui/kpi';
import { VarStrip } from '@/components/ui/var-strip';
import { Heatmap } from '@/components/ui/heatmap';
import { LoadBar } from '@/components/ui/load-bar';
import { SectionLabel } from '@/components/ui/section-label';

type TimeRange = '24h' | '7d' | '30d';

function statusDot(status: string) {
  if (status === 'completed') return 'dot-ok';
  if (status === 'failed') return 'dot-fail';
  if (status === 'running' || status === 'pending') return 'dot-run';
  if (status === 'cancelled') return 'dot-muted';
  return 'dot-warn';
}

function statusTag(status: string) {
  if (status === 'completed') return 'tag tag-ok';
  if (status === 'failed') return 'tag tag-fail';
  if (status === 'running') return 'tag tag-running';
  if (status === 'pending' || status === 'paused') return 'tag tag-warn';
  if (status === 'cancelled') return 'tag';
  return 'tag';
}

/** Bucket runs into 7×48 heatmap (last 7 days × half-hour slots). */
function buildHeatmap(runs: Run[]): { data: number[][]; failures: boolean[][] } {
  const data: number[][] = Array.from({ length: 7 }, () => Array(48).fill(0));
  const failures: boolean[][] = Array.from({ length: 7 }, () => Array(48).fill(false));
  const now = Date.now();
  for (const r of runs) {
    const t = new Date(r.created_at).getTime();
    const ageHours = (now - t) / 3_600_000;
    if (ageHours > 24 * 7 || ageHours < 0) continue;
    const dayBack = Math.floor(ageHours / 24);
    const dayIdx = 6 - dayBack;
    const date = new Date(t);
    const halfHour = date.getHours() * 2 + (date.getMinutes() >= 30 ? 1 : 0);
    if (dayIdx >= 0 && dayIdx < 7) {
      data[dayIdx][halfHour] += 1;
      if (r.status === 'failed') failures[dayIdx][halfHour] = true;
    }
  }
  // Normalize to 0..1
  const max = Math.max(1, ...data.flat());
  return { data: data.map((row) => row.map((v) => v / max)), failures };
}

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [allRuns, setAllRuns] = useState<Run[]>([]);
  const [functions, setFunctions] = useState<FunctionType[]>([]);
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState<TimeRange>('24h');

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      try {
        const days = range === '24h' ? 1 : range === '7d' ? 7 : 30;
        const [statsData, runsData, recentRuns, fns, usage] = await Promise.all([
          api.getStats(),
          api.getRuns({ page_size: 200 }),
          api.getRuns({ page_size: 12 }),
          api.getFunctions(),
          api.getDailyUsage(days).catch(() => [] as DailyUsage[])
        ]);
        if (cancelled) return;
        setStats(statsData);
        setAllRuns(runsData.runs);
        setRuns(recentRuns.runs);
        setFunctions(fns.functions);
        setDailyUsage(usage);
      } catch (e) {
        console.error('overview fetch failed', e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    const id = setInterval(fetchData, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [range]);

  const heatmap = useMemo(() => buildHeatmap(allRuns), [allRuns]);
  const sparkData = dailyUsage.map((d) => d.requests);
  const successRate =
    stats && stats.runs.total > 0 ? (stats.runs.completed / stats.runs.total) * 100 : 0;
  const totalCost = useMemo(() => dailyUsage.reduce((s, d) => s + (d.cost_usd ?? 0), 0), [dailyUsage]);
  const totalAi = useMemo(() => dailyUsage.reduce((s, d) => s + (d.requests ?? 0), 0), [dailyUsage]);

  const topFunctions = useMemo(() => {
    return [...functions]
      .filter((f) => f.is_active)
      .slice(0, 6)
      .map((f) => {
        const fnRuns = allRuns.filter((r) => r.function_id === f.id);
        const total = fnRuns.length;
        const ok = fnRuns.filter((r) => r.status === 'completed').length;
        return {
          id: f.id,
          name: f.name,
          total,
          successRate: total > 0 ? (ok / total) * 100 : 100,
          spark: Array.from({ length: 14 }).map((_, i) =>
            Math.max(0, fnRuns.length - i + (i % 3))
          )
        };
      })
      .sort((a, b) => b.total - a.total);
  }, [functions, allRuns]);

  const fleet = [
    { name: 'worker.api.eu-1', concurrency: 8, load: 0.6, status: 'OK' as const },
    { name: 'worker.api.eu-2', concurrency: 8, load: 0.85, status: 'BUSY' as const },
    { name: 'worker.eu.gpu',   concurrency: 4, load: 0.4, status: 'OK' as const },
    { name: 'worker.us.cpu',   concurrency: 6, load: 0.25, status: 'IDLE' as const }
  ];

  return (
    <div>
      <div className="page-hd">
        <div>
          <h1>Overview <em>· today.</em></h1>
          <p>Monitor your FlowForge workflows and activity</p>
        </div>
        <div className="page-hd-right">
          <VarStrip
            label="Range"
            value={range}
            onChange={setRange}
            options={[
              { value: '24h', label: '24h' },
              { value: '7d', label: '7d' },
              { value: '30d', label: '30d' }
            ]}
          />
          <button className="btn">Export</button>
        </div>
      </div>

      {/* KPI grid */}
      <div className="split-4" style={{ marginBottom: 18 }}>
        <Kpi
          label="Total runs"
          icon={<Activity size={14} />}
          tone="info"
          value={(stats?.runs.total ?? 0).toLocaleString()}
          delta={{
            value: `${stats?.runs.running ?? 0} running`,
            direction: (stats?.runs.running ?? 0) > 0 ? 'up' : 'flat'
          }}
          spark={sparkData.length > 1 ? sparkData : undefined}
        />
        <Kpi
          label="Success rate"
          icon={<CheckCircle2 size={14} />}
          tone="accent"
          value={`${successRate.toFixed(1)}%`}
          delta={{
            value: successRate >= 90 ? 'healthy' : 'needs attention',
            direction: successRate >= 90 ? 'up' : 'down'
          }}
        />
        <Kpi
          label="AI calls"
          icon={<Zap size={14} />}
          tone="violet"
          value={totalAi.toLocaleString()}
          delta={{ value: `${range}`, direction: 'up' }}
          spark={sparkData.length > 1 ? sparkData : undefined}
        />
        <Kpi
          label="Cost"
          icon={<DollarSign size={14} />}
          tone="warn"
          value={`$${totalCost.toFixed(2)}`}
          delta={{ value: `${range}`, direction: 'flat' }}
        />
      </div>

      {/* Activity heatmap + recent feed */}
      <div className="split-2" style={{ marginBottom: 18 }}>
        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="panel-title">Activity</div>
              <div className="panel-sub">Runs density · last 7d × 30min</div>
            </div>
            <div className="panel-right">
              <span className="tag tag-ok">OK</span>
              <span className="tag tag-fail">FAIL</span>
            </div>
          </div>
          <Heatmap data={heatmap.data} failures={heatmap.failures} />
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="panel-title">Recent activity</div>
              <div className="panel-sub">Live · last {runs.length}</div>
            </div>
            <div className="panel-right">
              <Link href="/runs" className="btn btn-sm">
                View all <ArrowRight size={12} />
              </Link>
            </div>
          </div>
          <div style={{ maxHeight: 195, overflowY: 'auto' }}>
            {loading && <div style={{ padding: 14 }} className="hint">Loading…</div>}
            {!loading && runs.length === 0 && (
              <div style={{ padding: 14 }} className="hint">No recent runs.</div>
            )}
            {runs.map((r) => (
              <Link href={`/runs/${r.id}`} key={r.id} className="feed-row">
                <span className="ts">{formatDistanceToNow(new Date(r.created_at), { addSuffix: false })}</span>
                <span className={`dot ${statusDot(r.status)}`} />
                <span className="msg">
                  <b>{r.function_id}</b>
                </span>
                <span className={statusTag(r.status)}>{r.status}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Fleet + Top functions */}
      <div className="split-2-wide">
        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="panel-title">Top functions</div>
              <div className="panel-sub">Most active · {range}</div>
            </div>
            <div className="panel-right">
              <Link href="/functions" className="btn btn-sm">
                <Box size={12} /> View all
              </Link>
            </div>
          </div>
          <table className="ff-table">
            <thead>
              <tr>
                <th>Function</th>
                <th>Runs</th>
                <th>Success</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              {topFunctions.length === 0 && (
                <tr><td colSpan={4} style={{ padding: 14 }} className="hint">No functions yet.</td></tr>
              )}
              {topFunctions.map((f) => (
                <tr key={f.id} className="is-clickable" onClick={() => (window.location.href = `/functions/${f.id}`)}>
                  <td className="td-id"><b>{f.name}</b></td>
                  <td className="mono">{f.total}</td>
                  <td>
                    <span className={`tag ${f.successRate >= 90 ? 'tag-ok' : f.successRate >= 70 ? 'tag-warn' : 'tag-fail'}`}>
                      {f.successRate.toFixed(0)}%
                    </span>
                  </td>
                  <td>
                    <div className="spark-bars">
                      {f.spark.slice(0, 14).map((v, i) => (
                        <span key={i} style={{ height: `${Math.max(4, Math.min(28, v * 4))}px` }} />
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="panel-title">Fleet</div>
              <div className="panel-sub">Workers & agents</div>
            </div>
            <div className="panel-right">
              <Link href="/agents" className="btn btn-sm">
                <Bot size={12} /> Agents
              </Link>
            </div>
          </div>
          <div className="panel-body" style={{ padding: 0 }}>
            <SectionLabel>Workers</SectionLabel>
            {fleet.map((w) => (
              <div key={w.name} className="feed-row" style={{ gridTemplateColumns: '1fr 80px 60px auto' }}>
                <span className="msg" style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{w.name}</span>
                <LoadBar value={w.load} warn={w.load > 0.8} />
                <span className="ts">{Math.round(w.load * w.concurrency)}/{w.concurrency}</span>
                <span className={`tag ${w.status === 'OK' ? 'tag-ok' : w.status === 'BUSY' ? 'tag-warn' : ''}`}>{w.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
