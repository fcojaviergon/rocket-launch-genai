import { Inter as FontSans } from 'next/font/google';
import { Providers } from '@/providers/providers';
import './globals.css';
import { Toaster } from '@/components/ui/toaster'
import { cn } from '@/lib/utils';
import { ThemeProvider } from '@/components/theme-provider';
import { validateEnv } from '@/lib/utils/env';

// Validate environment variables during build/runtime
if (process.env.NODE_ENV === 'production') {
  try {
    validateEnv();
  } catch (error) {
    console.error('Environment validation failed:', error);
    // In production, we continue even with errors to prevent breaking the app
    // But we log errors prominently
  }
}

export const fontSans = FontSans({
  subsets: ['latin'],
  variable: '--font-sans',
});

export const metadata = {
  title: 'Rocket Launch GenAI Platform',
  description: 'Modular platform for quickly building AI applications',
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={cn(
        'min-h-screen bg-background font-sans antialiased',
        'selection:bg-primary/20 selection:text-primary',
        fontSans.variable
      )}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <div className="relative flex min-h-screen flex-col">
            <Providers>
              <div className="flex-1">{children}</div>
            </Providers>
          </div>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
