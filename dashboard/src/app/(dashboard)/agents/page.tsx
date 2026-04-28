'use client';

import { useEffect, useMemo, useState } from 'react';
import { Bot, Plus, RefreshCw } from 'lucide-react';
import { api, type AgentType } from '@/lib/api';
import { CodeBlock } from '@/components/ui/code-block';
import { SectionLabel } from '@/components/ui/section-label';

const STATUS_DOT: Record<string, string> = {
  online: 'dot-ok',
  idle: 'dot-warn',
  busy: 'dot-run',
  offline: 'dot-muted'
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentType[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AgentType | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetch = async () => {
      try {
        const r = await api.getAgents();
        if (!cancelled) {
          setAgents(r.agents);
          setSelected((prev) => prev ?? r.agents[0] ?? null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetch();
    const id = setInterval(fetch, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: agents.length, online: 0, idle: 0, busy: 0, offline: 0 };
    for (const a of agents) c[a.status] = (c[a.status] ?? 0) + 1;
    return c;
  }, [agents]);

  return (
    <div>
      <div className="page-hd">
        <div>
          <h1>Agents <em>· your AI team.</em></h1>
          <p>{agents.length} agent{agents.length === 1 ? '' : 's'} · {counts.online ?? 0} online</p>
        </div>
        <div className="page-hd-right">
          <button className="btn"><RefreshCw size={12} /> Refresh</button>
          <button className="btn btn-primary"><Plus size={12} /> New agent</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16, alignItems: 'start' }}>
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">Roster</div>
            <div className="panel-sub mono">{agents.length}</div>
          </div>
          <div>
            {loading && <div className="hint" style={{ margin: 12 }}>Loading…</div>}
            {!loading && agents.length === 0 && <div className="hint" style={{ margin: 12 }}>No agents yet.</div>}
            {agents.map((a) => {
              const initials = a.name.split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();
              const active = selected?.id === a.id;
              return (
                <button
                  key={a.id}
                  type="button"
                  className={`feed-row${active ? ' is-active' : ''}`}
                  onClick={() => setSelected(a)}
                  style={{
                    width: '100%', textAlign: 'left',
                    gridTemplateColumns: '28px 1fr auto',
                    background: active ? 'var(--accent-wash)' : undefined,
                    cursor: 'pointer', border: 0
                  }}
                >
                  <span className="ff-side-foot-av" style={{ width: 26, height: 26 }}>{initials}</span>
                  <span className="msg">
                    <b>{a.name}</b>
                    <div className="mono" style={{ fontSize: 10.5, color: 'var(--ink-3)' }}>{a.model ?? '—'}</div>
                  </span>
                  <span className={`dot ${STATUS_DOT[a.status]}`} />
                </button>
              );
            })}
          </div>
        </div>

        {selected ? (
          <div className="panel">
            <div className="panel-head">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className="ff-side-foot-av" style={{ width: 36, height: 36, fontSize: 14 }}>
                  {selected.name.split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase()}
                </span>
                <div>
                  <div className="panel-title" style={{ fontSize: 16 }}>{selected.name}</div>
                  <div className="panel-sub" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span className={`dot ${STATUS_DOT[selected.status]}`} /> {selected.status}{selected.model ? ` · ${selected.model}` : ''}
                  </div>
                </div>
              </div>
              <div className="panel-right">
                <span className={`tag ${selected.is_active ? 'tag-ok' : ''}`}>{selected.is_active ? 'active' : 'paused'}</span>
              </div>
            </div>
            <div className="panel-body">
              {selected.description && <p style={{ color: 'var(--ink-2)', marginTop: 0 }}>{selected.description}</p>}

              <div style={{ marginTop: 16 }}>
                <SectionLabel>System prompt</SectionLabel>
                {selected.system_prompt ? (
                  <CodeBlock code={selected.system_prompt} />
                ) : (
                  <div className="hint">No system prompt set.</div>
                )}
              </div>

              {selected.enabled_skills?.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <SectionLabel>Skills</SectionLabel>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {selected.enabled_skills.map((sk) => (
                      <span key={sk} className="tag tag-violet">{sk}</span>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ marginTop: 16 }}>
                <SectionLabel>Configuration</SectionLabel>
                <CodeBlock language="json" code={JSON.stringify(selected.config ?? {}, null, 2)} />
              </div>
            </div>
          </div>
        ) : (
          <div className="panel">
            <div className="panel-body">
              <div className="hint">Select an agent on the left.</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
