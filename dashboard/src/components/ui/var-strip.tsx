'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface VarStripOption<T extends string> {
  value: T;
  label: string;
}

interface VarStripProps<T extends string> {
  label?: string;
  options: VarStripOption<T>[];
  value: T;
  onChange: (v: T) => void;
  className?: string;
}

export function VarStrip<T extends string>({ label, options, value, onChange, className }: VarStripProps<T>) {
  return (
    <div className={cn('var-strip', className)} role="tablist">
      {label && <span className="var-strip-label">{label}</span>}
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="tab"
          aria-selected={value === opt.value}
          className={value === opt.value ? 'is-on' : ''}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
