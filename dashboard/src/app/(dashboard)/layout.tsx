export const dynamic = 'force-dynamic';

import { Toaster } from '@/components/ui/sonner';
import KBar from '@/components/kbar';
import AppSidebar from '@/components/layout/app-sidebar';
import Header from '@/components/layout/header';
import NoProvidersBanner from '@/components/layout/no-providers-banner';
import { ShellEffects } from '@/components/layout/shell-effects';

export default async function DashboardLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <KBar>
      <ShellEffects />
      <div className="ff-app">
        <AppSidebar />
        <div className="ff-main">
          <Header />
          <NoProvidersBanner />
          <main className="ff-content">{children}</main>
        </div>
      </div>
      <Toaster />
    </KBar>
  );
}
