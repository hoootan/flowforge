'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface HeatmapProps {
  /** 2D array: 7 rows (days) × 48 cols (half-hours). Values 0-1. */
  data: number[][];
  /** Same shape as data — boolean for failure cells. */
  failures?: boolean[][];
  rowLabels?: string[];
  className?: string;
}

const DEFAULT_LABELS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

function intensity(v: number): string {
  if (v <= 0) return '';
  if (v < 0.25) return 'l1';
  if (v < 0.5) return 'l2';
  if (v < 0.75) return 'l3';
  return 'l4';
}

export function Heatmap({ data, failures, rowLabels = DEFAULT_LABELS, className }: HeatmapProps) {
  return (
    <div className={cn('heatmap-wrap', className)}>
      <div className="heatmap">
        {data.map((row, r) => (
          <div className="heatmap-row" key={r}>
            <span className="lbl">{rowLabels[r] ?? ''}</span>
            {row.map((v, c) => {
              const fail = failures?.[r]?.[c];
              return <span key={c} className={cn('heatmap-cell', fail ? 'lf' : intensity(v))} />;
            })}
          </div>
        ))}
      </div>
      <div className="heatmap-axis">
        <span></span>
        <span>00</span>
        <span>06</span>
        <span>12</span>
        <span>18</span>
        <span>24</span>
      </div>
    </div>
  );
}
