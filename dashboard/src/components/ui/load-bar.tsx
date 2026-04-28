'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface LoadBarProps {
  /** 0..1 */
  value: number;
  warn?: boolean;
  className?: string;
}

export function LoadBar({ value, warn, className }: LoadBarProps) {
  const filled = Math.round(Math.max(0, Math.min(1, value)) * 8);
  return (
    <span className={cn('load-bar', warn && 'warn', filled === 8 && 'full', className)}>
      {Array.from({ length: 8 }).map((_, i) => (
        <span key={i} className={i < filled ? 'on' : ''} />
      ))}
    </span>
  );
}
