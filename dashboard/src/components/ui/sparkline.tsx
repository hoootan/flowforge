'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  direction?: 'up' | 'down';
  className?: string;
}

export function Sparkline({ data, width = 80, height = 28, direction = 'up', className }: SparklineProps) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const points = data
    .map((v, i) => `${(i * step).toFixed(1)},${(height - ((v - min) / range) * height).toFixed(1)}`)
    .join(' ');
  return (
    <svg className={cn('kpi-spark', className)} width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline points={points} className={cn('sparkline', direction)} />
    </svg>
  );
}
