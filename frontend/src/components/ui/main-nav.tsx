import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileText, BarChart2, MessageSquare, Settings, Users, Zap } from 'lucide-react';

export function MainNav() {
  const pathname = usePathname();

  const navItems = [
    {
      name: 'Documents',
      href: '/dashboard/documents',
      icon: FileText,
      active: pathname?.startsWith('/dashboard/documents'),
    },
    {
      name: 'Pipelines',
      href: '/dashboard/pipelines',
      icon: Zap,
      active: pathname?.startsWith('/dashboard/pipelines'),
    },
    {
      name: 'Analytics',
      href: '/dashboard/analytics',
      icon: BarChart2,
      active: pathname?.startsWith('/dashboard/analytics'),
    },
    {
      name: 'Messages',
      href: '/dashboard/messages',
      icon: MessageSquare,
      active: pathname?.startsWith('/dashboard/messages'),
    },
    {
      name: 'Users',
      href: '/dashboard/users',
      icon: Users,
      active: pathname?.startsWith('/dashboard/users'),
    },
    {
      name: 'Settings',
      href: '/dashboard/settings',
      icon: Settings,
      active: pathname?.startsWith('/dashboard/settings'),
    },
  ];

  return (
    <nav className="flex items-center space-x-4 lg:space-x-6">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <Link
            key={item.name}
            href={item.href}
            className={`flex items-center text-sm font-medium transition-colors hover:text-primary ${
              item.active
                ? 'text-primary'
                : 'text-muted-foreground'
            }`}
          >
            <Icon className="mr-2 h-4 w-4" />
            {item.name}
          </Link>
        );
      })}
    </nav>
  );
}
