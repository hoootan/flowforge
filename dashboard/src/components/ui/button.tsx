import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

/**
 * Button variants — mapped to FlowForge mockup classes (.btn, .btn-primary, .btn-danger, .btn-ghost).
 * Tailwind classes provide focus rings + disabled/svg sizing only.
 */
const buttonVariants = cva(
  "btn inline-flex items-center justify-center gap-2 whitespace-nowrap disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-3.5 shrink-0 [&_svg]:shrink-0 outline-none aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
  {
    variants: {
      variant: {
        default: 'btn-primary',
        destructive: 'btn-danger',
        outline: '',
        secondary: '',
        ghost: 'btn-ghost',
        link: 'btn-ghost underline-offset-4 hover:underline'
      },
      size: {
        default: '',
        sm: 'btn-sm',
        lg: 'btn-lg',
        xs: 'btn-xs',
        icon: 'btn-icon'
      }
    },
    defaultVariants: {
      variant: 'default',
      size: 'default'
    }
  }
);

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot : 'button';

  return (
    <Comp
      data-slot='button'
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
