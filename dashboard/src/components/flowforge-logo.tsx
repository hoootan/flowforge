import * as React from 'react';
import { cn } from '@/lib/utils';

type Props = React.SVGProps<SVGSVGElement> & {
  className?: string;
};

export function FlowForgeLogo({ className, ...props }: Props) {
  return (
    <svg
      viewBox='0 0 24 24'
      xmlns='http://www.w3.org/2000/svg'
      aria-hidden='true'
      className={cn('size-4', className)}
      {...props}
    >
      <path
        d='M 3 3 L 21 3 L 21 7 L 13 7 L 13 11 L 19 11 L 19 15 L 13 15 L 13 21 L 9 21 L 9 7 L 3 7 Z'
        fill='currentColor'
      />
    </svg>
  );
}
