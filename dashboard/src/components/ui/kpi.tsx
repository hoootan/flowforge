'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { Sparkline } from './sparkline';

type KpiTone = 'accent' | 'violet' | 'warn' | 'info' | 'danger' | 'teal';

export interface KpiProps {
  label: string;
  value: React.ReactNode;
  delta?: { value: string; direction: 'up' | 'down' | 'flat' };
  icon?: React.ReactNode;
  tone?: KpiTone;
  spark?: number[];
  className?: string;
}

export function Kpi({ label, value, delta, icon, tone = 'accent', spark, className }: KpiProps) {
  return (
    <div className={cn('kpi', className)}>
      <div className="kpi-label">
        {icon && <span className={cn('kpi-icon', tone !== 'accent' && tone)}>{icon}</span>}
        {label}
      </div>
      <div className="kpi-value">{value}</div>
      {delta && (
        <div className={cn('kpi-delta', delta.direction === 'down' && 'is-down')}>
          {delta.direction === 'up' ? '↑' : delta.direction === 'down' ? '↓' : '·'} {delta.value}
        </div>
      )}
      {spark && spark.length > 1 && (
        <Sparkline data={spark} className="kpi-spark" direction={delta?.direction === 'down' ? 'down' : 'up'} />
      )}
    </div>
  );
}
