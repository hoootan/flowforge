'use client';

import { useEffect, useState } from 'react';
import { api, type Stats, type Run, type Function as FunctionType } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Activity, Box, Zap, Clock, CheckCircle, XCircle, Play } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';

function StatCard({
  title,
  value,
  description,
  icon: Icon,
  loading
}: {
  title: string;
  value: string | number;
  description?: string;
  icon: React.ComponentType<{ className?: string }>;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
        <CardTitle className='text-sm font-medium'>{title}</CardTitle>
        <Icon className='h-4 w-4 text-muted-foreground' />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className='h-8 w-20' />
        ) : (
          <>
            <div className='text-2xl font-bold'>{value}</div>
            {description && (
              <p className='text-xs text-muted-foreground'>{description}</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function RecentRuns({ runs, loading }: { runs: Run[]; loading: boolean }) {
  const statusIcons = {
    completed: <CheckCircle className='h-4 w-4 text-green-500' />,
    failed: <XCircle className='h-4 w-4 text-red-500' />,
    running: <Play className='h-4 w-4 text-blue-500' />,
    pending: <Clock className='h-4 w-4 text-yellow-500' />,
    paused: <Clock className='h-4 w-4 text-orange-500' />,
    cancelled: <XCircle className='h-4 w-4 text-gray-500' />
  };

  return (
    <Card className='col-span-full lg:col-span-2'>
      <CardHeader>
        <CardTitle>Recent Runs</CardTitle>
        <CardDescription>Latest workflow executions</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className='space-y-4'>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className='flex items-center gap-4'>
                <Skeleton className='h-8 w-8 rounded-full' />
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
          <div className='space-y-4'>
            {runs.slice(0, 5).map((run) => (
              <Link
                key={run.id}
                href={`/runs/${run.id}`}
                className='flex items-center gap-4 rounded-lg p-2 transition-colors hover:bg-muted/50'
              >
                <div className='flex h-8 w-8 items-center justify-center rounded-full bg-muted'>
                  {statusIcons[run.status]}
                </div>
                <div className='flex-1 min-w-0'>
                  <p className='truncate text-sm font-medium'>{run.function_id}</p>
                  <p className='text-xs text-muted-foreground'>
                    {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                  </p>
                </div>
                <Badge variant={run.status === 'completed' ? 'default' : run.status === 'failed' ? 'destructive' : 'secondary'}>
                  {run.status}
                </Badge>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ActiveFunctions({ functions, loading }: { functions: FunctionType[]; loading: boolean }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Functions</CardTitle>
        <CardDescription>Registered workflow functions</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className='space-y-3'>
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className='h-12 w-full' />
            ))}
          </div>
        ) : functions.length === 0 ? (
          <p className='text-sm text-muted-foreground'>No functions registered</p>
        ) : (
          <div className='space-y-3'>
            {functions.filter(f => f.is_active).slice(0, 5).map((fn) => (
              <Link
                key={fn.id}
                href='/functions'
                className='flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50'
              >
                <div>
                  <p className='text-sm font-medium'>{fn.name}</p>
                  <p className='text-xs text-muted-foreground'>
                    {fn.trigger_type}: {fn.trigger_value}
                  </p>
                </div>
                <Badge variant='outline'>{fn.trigger_type}</Badge>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [functions, setFunctions] = useState<FunctionType[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsData, runsData, functionsData] = await Promise.all([
          api.getStats(),
          api.getRuns({ page_size: 5 }),
          api.getFunctions()
        ]);
        setStats(statsData);
        setRuns(runsData.runs);
        setFunctions(functionsData.functions);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className='space-y-6'>
      <div>
        <h1 className='text-3xl font-bold tracking-tight'>Overview</h1>
        <p className='text-muted-foreground'>
          Monitor your FlowForge workflows and activity
        </p>
      </div>

      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
        <StatCard
          title='Total Runs'
          value={stats?.runs.total ?? 0}
          description={`${stats?.runs.running ?? 0} currently running`}
          icon={Activity}
          loading={loading}
        />
        <StatCard
          title='Completed'
          value={stats?.runs.completed ?? 0}
          description='Successfully finished'
          icon={CheckCircle}
          loading={loading}
        />
        <StatCard
          title='Failed'
          value={stats?.runs.failed ?? 0}
          description='Runs that errored'
          icon={XCircle}
          loading={loading}
        />
        <StatCard
          title='Active Functions'
          value={stats?.functions.active ?? 0}
          description={`${stats?.functions.total ?? 0} total registered`}
          icon={Box}
          loading={loading}
        />
      </div>

      <div className='grid gap-4 lg:grid-cols-3'>
        <RecentRuns runs={runs} loading={loading} />
        <ActiveFunctions functions={functions} loading={loading} />
      </div>
    </div>
  );
}
