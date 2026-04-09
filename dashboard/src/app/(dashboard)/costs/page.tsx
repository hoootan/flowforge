'use client';

import { useEffect, useState } from 'react';
import { api, type CostDashboardData, type UsageByProvider, type UsageByModel, type DailyUsage } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DollarSign, Zap, Clock, TrendingUp } from 'lucide-react';
import {
  Area,
  AreaChart as RechartsAreaChart,
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
  PieChart,
  Pie,
} from 'recharts';

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'];

function formatCost(usd: number): string {
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  if (usd < 1) return `$${usd.toFixed(3)}`;
  return `$${usd.toFixed(2)}`;
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return String(tokens);
}

export default function CostsPage() {
  const [data, setData] = useState<CostDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState('30');

  const fetchData = async () => {
    setLoading(true);
    const result = await api.getCostDashboard(Number(days));
    setData(result);
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, [days]);

  const summary = data?.summary?.summary;
  const providers = data?.by_provider?.providers || [];
  const models = data?.by_model?.models || [];
  const daily = data?.daily?.daily || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Cost Dashboard</h2>
          <p className="text-muted-foreground">
            Token usage, costs, and performance across agents and models
          </p>
        </div>
        <Select value={days} onValueChange={setDays}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-8 w-20" /> : (
              <div className="text-2xl font-bold">{formatCost(summary?.total_cost_usd || 0)}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tokens</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-8 w-20" /> : (
              <div className="text-2xl font-bold">{formatTokens(summary?.total_tokens || 0)}</div>
            )}
            {!loading && summary && (
              <p className="text-xs text-muted-foreground mt-1">
                {formatTokens(summary.prompt_tokens)} in / {formatTokens(summary.completion_tokens)} out
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Requests</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-8 w-20" /> : (
              <div className="text-2xl font-bold">{summary?.total_requests?.toLocaleString() || 0}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Latency</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-8 w-20" /> : (
              <div className="text-2xl font-bold">{(summary?.avg_latency_ms || 0).toFixed(0)}ms</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Charts row */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Daily cost trend */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Daily Cost</CardTitle>
            <CardDescription>Cost over time</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-[250px]" /> : (
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsAreaChart data={daily}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
                    <Tooltip formatter={(v: number) => formatCost(v)} />
                    <defs>
                      <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area
                      type="monotone"
                      dataKey="cost_usd"
                      stroke="#6366f1"
                      strokeWidth={2}
                      fill="url(#costGrad)"
                      name="Cost"
                    />
                  </RechartsAreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cost by provider */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cost by Provider</CardTitle>
            <CardDescription>Spend distribution</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-[250px]" /> : providers.length === 0 ? (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground text-sm">
                No usage data yet
              </div>
            ) : (
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={providers}
                      dataKey="cost_usd"
                      nameKey="provider"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ provider, cost_usd }: any) => `${provider}: ${formatCost(cost_usd)}`}
                    >
                      {providers.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number) => formatCost(v)} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Cost by model table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cost by Model</CardTitle>
          <CardDescription>Detailed breakdown per model</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? <Skeleton className="h-[200px]" /> : models.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">No usage data</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="text-left py-2 font-medium">Model</th>
                    <th className="text-left py-2 font-medium">Provider</th>
                    <th className="text-right py-2 font-medium">Requests</th>
                    <th className="text-right py-2 font-medium">Tokens</th>
                    <th className="text-right py-2 font-medium">Cost</th>
                    <th className="text-right py-2 font-medium">Avg Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="py-2 font-mono text-xs">{m.model}</td>
                      <td className="py-2">{m.provider}</td>
                      <td className="py-2 text-right">{m.requests.toLocaleString()}</td>
                      <td className="py-2 text-right">{formatTokens(m.total_tokens)}</td>
                      <td className="py-2 text-right font-medium">{formatCost(m.cost_usd)}</td>
                      <td className="py-2 text-right">{m.avg_latency_ms.toFixed(0)}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
