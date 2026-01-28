import Providers from '@/components/layout/providers';
import { Toaster } from '@/components/ui/sonner';
import { cookies } from 'next/headers';
import KBar from '@/components/kbar';
import AppSidebar from '@/components/layout/app-sidebar';
import Header from '@/components/layout/header';
import PageContainer from '@/components/layout/page-container';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';

export default async function DashboardLayout({
  children
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const activeThemeValue = cookieStore.get('active_theme')?.value;
  const sidebarOpen = cookieStore.get('sidebar_state')?.value !== 'false';

  return (
    <Providers activeThemeValue={activeThemeValue as string}>
      <KBar>
        <SidebarProvider defaultOpen={sidebarOpen}>
          <AppSidebar />
          <SidebarInset>
            <Header />
            <PageContainer scrollable>
              {children}
            </PageContainer>
          </SidebarInset>
        </SidebarProvider>
      </KBar>
      <Toaster />
    </Providers>
  );
}
