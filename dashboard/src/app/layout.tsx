import { fontVariables } from '@/lib/font';
import { cn } from '@/lib/utils';
import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? 'https://flowforge.hiolo.dev'
  ),
  title: 'FlowForge Dashboard',
  description: 'Monitor and manage your durable AI workflows — every run, every step, in real time.',
  openGraph: {
    title: 'FlowForge Dashboard',
    description: 'Monitor and manage your durable AI workflows — every run, every step, in real time.',
    type: 'website',
    siteName: 'FlowForge'
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FlowForge Dashboard',
    description: 'Monitor and manage your durable AI workflows — every run, every step, in real time.'
  }
};

export const viewport: Viewport = {
  themeColor: '#07080B'
};

const PRE_HYDRATION_SCRIPT = `
  (function () {
    try {
      var raw = localStorage.getItem('ff.shell');
      var s = raw ? (JSON.parse(raw).state || {}) : {};
      var theme = s.theme === 'light' ? 'light' : 'dark';
      var density = ['tight','comfortable','spacious'].indexOf(s.density) >= 0 ? s.density : 'tight';
      var sidebar = s.sidebar === 'compact' ? 'compact' : 'full';
      document.documentElement.setAttribute('data-theme', theme);
      document.body && document.body.setAttribute('data-density', density);
      document.body && document.body.setAttribute('data-sidebar', sidebar);
    } catch (e) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  })();
`;

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: PRE_HYDRATION_SCRIPT }} />
      </head>
      <body
        data-density="tight"
        data-sidebar="full"
        className={cn('min-h-screen antialiased', fontVariables)}
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
