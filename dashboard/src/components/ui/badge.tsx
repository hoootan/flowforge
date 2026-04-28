import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

/**
 * Badge variants — mapped to FlowForge mockup .tag classes.
 */
const badgeVariants = cva('tag', {
  variants: {
    variant: {
      default: 'tag-info',
      secondary: '',
      destructive: 'tag-fail',
      outline: '',
      success: 'tag-ok',
      warning: 'tag-warn',
      info: 'tag-info',
      violet: 'tag-violet',
      teal: 'tag-teal',
      running: 'tag-running'
    }
  },
  defaultVariants: { variant: 'default' }
});

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<'span'> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : 'span';
  return (
    <Comp data-slot='badge' className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
