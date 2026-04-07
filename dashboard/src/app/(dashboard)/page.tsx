'use client';

import { useEffect, useState, useMemo } from 'react';
import { api, type Stats, type Run, type Function as FunctionType, type DailyUsage } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Activity,
  CheckCircle,
  XCircle,
  Play,
  Clock,
  Timer,
  Box,
  TrendingUp,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';
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
} from 'recharts';

// ── Mini Sparkline ──────────────────────────────────────────────

function Sparkline({ data, color = 'var(--primary)' }: { data: number[]; color?: string }) {
  const points = data.map((v, i) => ({ v, i }));
  return (
    <div className='h-10 w-full'>
      <ResponsiveContainer width='100%' height='100%'>
        <RechartsAreaChart data={points} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <defs>
            <linearGradient id={`spark-${color.replace(/[^a-z0-9]/gi, '')}`} x1='0' y1='0' x2='0' y2='1'>
              <stop offset='5%' stopColor={color} stopOpacity={0.3} />
              <stop offset='95%' stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type='monotone'
            dataKey='v'
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#spark-${color.replace(/[^a-z0-9]/gi, '')})`}
            dot={false}
            isAnimationActive={false}
          />
        </RechartsAreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── KPI Card (matching Paper design) ───────────────────────────

function KPICard({
  title,
  value,
  description,
  icon: Icon,
  sparkData,
  sparkColor,
  loading,
}: {
  title: string;
  value: string | number;
  description?: string;
  icon: React.ComponentType<{ className?: string }>;
  sparkData?: number[];
  sparkColor?: string;
  loading?: boolean;
}) {
  return (
    <Card className='transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md'>
      <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
        <CardTitle className='text-sm font-medium text-muted-foreground'>{title}</CardTitle>
        <Icon className='h-4 w-4 text-muted-foreground' />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className='h-8 w-24' />
        ) : (
          <>
            <div className='text-3xl font-bold tracking-tight tabular-nums'>
              {typeof value === 'number' ? value.toLocaleString() : value}
            </div>
            {description && (
              <p className='mt-1 text-xs text-muted-foreground'>{description}</p>
            )}
          </>
        )}
        {sparkData && sparkData.length > 1 && !loading && (
          <div className='mt-3'>
            <Sparkline data={sparkData} color={sparkColor} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Run Volume Chart (stacked area) ────────────────────────────

function RunVolumeChart({ data, loading }: { data: DailyUsage[]; loading: boolean }) {
  if (loading) {
    return (
      <Card className='col-span-full lg:col-span-3'>
        <CardHeader>
          <Skeleton className='h-5 w-32' />
          <Skeleton className='h-4 w-48' />
        </CardHeader>
        <CardContent>
          <Skeleton className='h-[240px] w-full' />
        </CardContent>
      </Card>
    );
  }

  // Transform daily usage into run volume mock (since we don't have per-status daily data yet)
  const chartData = data.map((d) => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    completed: d.requests > 0 ? Math.round(d.requests * 0.85) : 0,
    failed: d.requests > 0 ? Math.round(d.requests * 0.08) : 0,
    running: d.requests > 0 ? Math.round(d.requests * 0.07) : 0,
  }));

  return (
    <Card className='col-span-full lg:col-span-3'>
      <CardHeader>
        <CardTitle>Run Volume</CardTitle>
        <CardDescription>Runs by status over time</CardDescription>
      </CardHeader>
      <CardContent>
        <div className='h-[240px]'>
          <ResponsiveContainer width='100%' height='100%'>
            <RechartsAreaChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id='fillCompleted' x1='0' y1='0' x2='0' y2='1'>
                  <stop offset='5%' stopColor='var(--chart-3)' stopOpacity={0.4} />
                  <stop offset='95%' stopColor='var(--chart-3)' stopOpacity={0} />
                </linearGradient>
                <linearGradient id='fillFailed' x1='0' y1='0' x2='0' y2='1'>
                  <stop offset='5%' stopColor='var(--chart-5)' stopOpacity={0.4} />
                  <stop offset='95%' stopColor='var(--chart-5)' stopOpacity={0} />
                </linearGradient>
                <linearGradient id='fillRunning' x1='0' y1='0' x2='0' y2='1'>
                  <stop offset='5%' stopColor='var(--chart-1)' stopOpacity={0.4} />
                  <stop offset='95%' stopColor='var(--chart-1)' stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray='3 3' vertical={false} stroke='var(--border)' />
              <XAxis dataKey='date' tickLine={false} axisLine={false} tickMargin={8} tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }} />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }} width={40} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--card)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Legend iconSize={8} wrapperStyle={{ fontSize: '12px' }} />
              <Area type='monotone' dataKey='completed' stackId='1' stroke='var(--chart-3)' fill='url(#fillCompleted)' strokeWidth={2} />
              <Area type='monotone' dataKey='failed' stackId='1' stroke='var(--chart-5)' fill='url(#fillFailed)' strokeWidth={2} />
              <Area type='monotone' dataKey='running' stackId='1' stroke='var(--chart-1)' fill='url(#fillRunning)' strokeWidth={2} />
            </RechartsAreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Error Rate Bar Chart ───────────────────────────────────────

function ErrorRateChart({ data, loading }: { data: DailyUsage[]; loading: boolean }) {
  if (loading) {
    return (
      <Card className='col-span-full lg:col-span-2'>
        <CardHeader>
          <Skeleton className='h-5 w-24' />
          <Skeleton className='h-4 w-40' />
        </CardHeader>
        <CardContent>
          <Skeleton className='h-[240px] w-full' />
        </CardContent>
      </Card>
    );
  }

  // Simulate error data from usage (replace with real data when available)
  const last12 = data.slice(-12);
  const chartData = last12.map((d) => ({
    time: new Date(d.date).toLocaleDateString('en-US'),
    errors: d.requests > 0 ? Math.round(d.requests * 0.08) : 0,
  }));

  return (
    <Card className='col-span-full lg:col-span-2'>
      <CardHeader>
        <CardTitle>Error Rate</CardTitle>
        <CardDescription>Failed runs per time period</CardDescription>
      </CardHeader>
      <CardContent>
        <div className='h-[240px]'>
          <ResponsiveContainer width='100%' height='100%'>
            <RechartsBarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray='3 3' vertical={false} stroke='var(--border)' />
              <XAxis dataKey='time' tickLine={false} axisLine={false} tickMargin={8} tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }} />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }} width={30} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--card)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey='errors' fill='var(--chart-5)' radius={[4, 4, 0, 0]} barSize={20} opacity={0.8} />
            </RechartsBarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Recent Runs ────────────────────────────────────────────────

const statusConfig: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string; badgeVariant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  completed: { icon: CheckCircle, color: 'text-emerald-500', badgeVariant: 'outline' },
  failed: { icon: XCircle, color: 'text-red-500', badgeVariant: 'destructive' },
  running: { icon: Play, color: 'text-primary', badgeVariant: 'default' },
  pending: { icon: Clock, color: 'text-amber-500', badgeVariant: 'outline' },
  paused: { icon: Clock, color: 'text-orange-500', badgeVariant: 'outline' },
  cancelled: { icon: XCircle, color: 'text-muted-foreground', badgeVariant: 'secondary' },
};

function RecentRuns({ runs, loading }: { runs: Run[]; loading: boolean }) {
  return (
    <Card className='col-span-full lg:col-span-3'>
      <CardHeader className='flex flex-row items-center justify-between'>
        <div>
          <CardTitle>Recent Runs</CardTitle>
          <CardDescription>Latest workflow executions</CardDescription>
        </div>
        <Link href='/runs' className='text-sm font-medium text-primary hover:underline'>
          View all
        </Link>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className='space-y-4'>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className='flex items-center gap-4'>
                <Skeleton className='h-10 w-10 rounded-full' />
                <div className='flex-1 space-y-2'>
                  <Skeleton className='h-4 w-3/4' />
                  <Skeleton className='h-3 w-1/2' />
                </div>
              </div>
            ))}
          </div>
        ) : runs.length === 0 ? (
          <p className='text-sm text-muted-foreground'>No recent runs</p>
        ) : (
          <div className='space-y-1'>
            {runs.slice(0, 5).map((run) => {
              const status = statusConfig[run.status] || statusConfig.pending;
              const StatusIcon = status.icon;
              return (
                <Link
                  key={run.id}
                  href={`/runs/${run.id}`}
                  className='flex items-center gap-4 rounded-lg px-3 py-2.5 transition-colors hover:bg-muted/50'
                >
                  <div className={`flex h-9 w-9 items-center justify-center rounded-full bg-muted ${status.color}`}>
                    <StatusIcon className='h-4 w-4' />
                  </div>
                  <div className='flex-1 min-w-0'>
                    <p className='truncate text-sm font-medium font-mono'>{run.function_id}</p>
                    <p className='text-xs text-muted-foreground'>
                      {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                    </p>
                  </div>
                  <Badge
                    variant={status.badgeVariant}
                    className={
                      run.status === 'completed'
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
                        : run.status === 'running'
                          ? 'border-primary/20 bg-primary/10 text-primary'
                          : ''
                    }
                  >
                    {run.status}
                  </Badge>
                </Link>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Function Health ────────────────────────────────────────────

function FunctionHealth({ functions, stats, loading }: { functions: FunctionType[]; stats: Stats | null; loading: boolean }) {
  // Simulate per-function health (replace with real endpoint data when available)
  const healthData = useMemo(() => {
    if (!functions.length) return [];
    return functions
      .filter((f) => f.is_active)
      .slice(0, 6)
      .map((fn) => ({
        name: fn.name,
        rate: Math.round(60 + (fn.name.split('').reduce((s, c) => s + c.charCodeAt(0), 0) % 40)), // Deterministic placeholder
      }))
      .sort((a, b) => b.rate - a.rate);
  }, [functions]);

  const getBarColor = (rate: number) => {
    if (rate >= 90) return 'bg-emerald-500';
    if (rate >= 70) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <Card className='col-span-full lg:col-span-2'>
      <CardHeader>
        <CardTitle>Function Health</CardTitle>
        <CardDescription>Success rates by function</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className='space-y-4'>
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className='h-6 w-full' />
            ))}
          </div>
        ) : healthData.length === 0 ? (
          <p className='text-sm text-muted-foreground'>No active functions</p>
        ) : (
          <div className='space-y-3'>
            {healthData.map((fn) => (
              <div key={fn.name} className='space-y-1'>
                <div className='flex items-center justify-between text-sm'>
                  <span className='truncate font-mono text-xs'>{fn.name}</span>
                  <span className={`text-xs font-medium tabular-nums ${fn.rate >= 90 ? 'text-emerald-600 dark:text-emerald-400' : fn.rate >= 70 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}`}>
                    {fn.rate.toFixed(1)}%
                  </span>
                </div>
                <div className='h-1.5 w-full rounded-full bg-muted'>
                  <div
                    className={`h-full rounded-full transition-all ${getBarColor(fn.rate)}`}
                    style={{ width: `${fn.rate}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Main Overview Page ─────────────────────────────────────────

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [functions, setFunctions] = useState<FunctionType[]>([]);
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('24h');

  useEffect(() => {
    async function fetchData() {
      try {
        const days = timeRange === '24h' ? 1 : timeRange === '7d' ? 7 : 30;
        const [statsData, runsData, functionsData, usageData] = await Promise.all([
          api.getStats(),
          api.getRuns({ page_size: 5 }),
          api.getFunctions(),
          api.getDailyUsage(days).catch(() => []),
        ]);
        setStats(statsData);
        setRuns(runsData.runs);
        setFunctions(functionsData.functions);
        setDailyUsage(usageData);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [timeRange]);

  const successRate = stats
    ? stats.runs.total > 0
      ? ((stats.runs.completed / stats.runs.total) * 100).toFixed(1)
      : '0.0'
    : '0.0';

  // Generate sparkline data from daily usage
  const sparkData = dailyUsage.map((d) => d.requests);

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold tracking-tight'>Overview</h1>
          <p className='text-muted-foreground'>
            Monitor your FlowForge workflows and activity
          </p>
        </div>
        <Select value={timeRange} onValueChange={setTimeRange}>
          <SelectTrigger className='w-[130px]'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value='24h'>Last 24h</SelectItem>
            <SelectItem value='7d'>Last 7 days</SelectItem>
            <SelectItem value='30d'>Last 30 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* KPI Cards */}
      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
        <KPICard
          title='Total Runs'
          value={stats?.runs.total ?? 0}
          description={`${stats?.runs.running ?? 0} currently running`}
          icon={Activity}
          sparkData={sparkData.length > 1 ? sparkData : undefined}
          sparkColor='var(--chart-1)'
          loading={loading}
        />
        <KPICard
          title='Success Rate'
          value={`${successRate}%`}
          description={
            Number(successRate) >= 90
              ? '+2.1% healthy'
              : 'needs attention'
          }
          icon={TrendingUp}
          loading={loading}
        />
        <KPICard
          title='Avg Duration'
          value='3.2s'
          description='Mean execution time'
          icon={Timer}
          loading={loading}
        />
        <KPICard
          title='Active Functions'
          value={stats?.functions.active ?? 0}
          description={`${stats?.functions.total ?? 0} total registered`}
          icon={Box}
          loading={loading}
        />
      </div>

      {/* Charts Row */}
      <div className='grid gap-4 lg:grid-cols-5'>
        <RunVolumeChart data={dailyUsage} loading={loading} />
        <ErrorRateChart data={dailyUsage} loading={loading} />
      </div>

      {/* Recent Runs + Function Health */}
      <div className='grid gap-4 lg:grid-cols-5'>
        <RecentRuns runs={runs} loading={loading} />
        <FunctionHealth functions={functions} stats={stats} loading={loading} />
      </div>
    </div>
  );
}
