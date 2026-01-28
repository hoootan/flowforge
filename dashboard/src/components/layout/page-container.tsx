import React from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';

export default function PageContainer({
  children,
  scrollable = true
}: {
  children: React.ReactNode;
  scrollable?: boolean;
}) {
  return scrollable ? (
    <ScrollArea className='h-[calc(100dvh-56px)]'>
      <div className='flex min-h-[calc(100dvh-56px-32px)] flex-col gap-4 p-4 pb-8 md:px-6'>
        {children}
      </div>
    </ScrollArea>
  ) : (
    <div className='flex h-[calc(100dvh-56px)] flex-col gap-4 overflow-auto p-4 pb-8 md:px-6'>
      {children}
    </div>
  );
}
