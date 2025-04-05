'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getSession } from 'next-auth/react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowUp, ArrowDown, Users, Calendar, FileText, BarChart as BarChartIcon } from 'lucide-react';
import { api } from '@/lib/api';

interface User {
  id: string;
  email: string;
  full_name?: string;
  name?: string;
}

interface StatsCardProps {
  title: string;
  value: string;
  description: string;
  icon: React.ReactNode;
  trend: 'up' | 'down' | 'neutral';
  trendValue: string;
}

interface DashboardStats {
  users: {
    total: number;
    new_week: number;
    change: number;
  };
  documents: {
    total: number;
    new_week: number;
    change: number;
  };
  executions: {
    total: number;
    new_week: number;
    change: number;
  };
  recent_activity: {
    id: string;
    document_name: string;
    document_type: string;
    status: string;
    time_ago: string;
  }[];
  monthly_stats: Record<string, number>;
}

interface BarChartProps {
  data: Record<string, number>;
}

function MonthlyBarChart({ data }: BarChartProps) {
  const entries = Object.entries(data);
  const maxValue = Math.max(...Object.values(data));

  return (
    <div className="w-full h-[250px] flex flex-col">
      <div className="flex-1 flex items-end gap-2">
        {entries.map(([label, value], index) => {
          const height = maxValue > 0 ? (value / maxValue) * 100 : 0;
          return (
            <div
              key={index}
              className="group flex-1 flex flex-col items-center justify-end"
            >
              <div className="w-full relative flex flex-col justify-end">
                <div
                  className="w-full bg-primary group-hover:bg-primary/80 transition-colors duration-200 rounded-t-sm"
                  style={{
                    height: `${height}%`,
                    minHeight: value > 0 ? '4px' : '0'
                  }}
                />
              </div>
              <div className="mt-2 text-center">
                <span className="text-xs text-muted-foreground">{label}</span>
                <span className="block text-sm font-medium">{value}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatsCard({ title, value, description, icon, trend, trendValue }: StatsCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-2xl font-bold">{value}</div>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
          <div className="rounded-full bg-muted p-2">{icon}</div>
        </div>
        <div className="mt-4 flex items-center text-sm">
          {trend === 'up' && <ArrowUp className="mr-1 h-4 w-4 text-green-500" />}
          {trend === 'down' && <ArrowDown className="mr-1 h-4 w-4 text-red-500" />}
          <span className={trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : ''}>
            {trendValue}
          </span>
          <span className="text-muted-foreground ml-1">from last week</span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkSession = async () => {
      const session = await getSession();
      if (!session) {
        router.push('/login');
        return;
      }
      setUser(session.user as User);
    };

    const loadStats = async (retryCount = 0) => {
      try {
        const response = await api.stats.getDashboard();
        setStats(response as DashboardStats);
        setLoading(false);
      } catch (error: any) {
        console.error('Error loading statistics:', error);
        
        // Handle authentication errors - consider any 401 or session error as auth failure
        if (error.status === 401 || error.isAuthError || error.message?.includes('auth') || error.message?.includes('token')) {
          if (retryCount < 1) {
            console.log(`Auth error, attempting refresh (attempt ${retryCount + 1})...`);
            
            // Attempt to refresh the session once
            try {
              const refreshedSession = await fetch('/api/auth/session', { 
                method: 'GET', 
                cache: 'no-store'
              }).then(res => res.json());
              
              // If refresh appeared to work, retry loading stats
              if (refreshedSession?.accessToken) {
                setTimeout(() => loadStats(retryCount + 1), 500);
                return;
              } else {
                // Refresh failed - redirect to login
                console.log('Session refresh failed, redirecting to login');
                router.push('/login?error=session_expired');
              }
            } catch (refreshError) {
              console.error('Error refreshing session:', refreshError);
              router.push('/login?error=refresh_failed');
            }
          } else {
            // We already tried refreshing, redirect to login
            console.log('Authentication failed after retry, redirecting to login');
            router.push('/login?error=auth_failed');
          }
        } else {
          // Not an auth error, just handle gracefully
          setLoading(false);
        }
      }
    };

    checkSession();
    loadStats();
  }, [router]);

  if (loading) {
    return (
      <div className="p-6 w-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="p-6 w-full">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Welcome,</span>
          <span className="font-medium">{user?.name || user?.full_name || 'User'}</span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        <StatsCard
          title="Users"
          value={stats?.users.total.toLocaleString() || '0'}
          description={`${stats?.users.new_week || 0} new this week`}
          icon={<Users className="h-5 w-5" />}
          trend={(stats?.users.change || 0) >= 0 ? 'up' : 'down'}
          trendValue={`${(stats?.users.change || 0) >= 0 ? '+' : ''}${stats?.users.change || 0}%`}
        />
        <StatsCard
          title="Documents"
          value={stats?.documents.total.toLocaleString() || '0'}
          description={`${stats?.documents.new_week || 0} new this week`}
          icon={<FileText className="h-5 w-5" />}
          trend={(stats?.documents.change || 0) >= 0 ? 'up' : 'down'}
          trendValue={`${(stats?.documents.change || 0) >= 0 ? '+' : ''}${stats?.documents.change || 0}%`}
        />
        <StatsCard
          title="Executions"
          value={stats?.executions.total.toLocaleString() || '0'}
          description={`${stats?.executions.new_week || 0} new this week`}
          icon={<BarChartIcon className="h-5 w-5" />}
          trend={(stats?.executions.change || 0) >= 0 ? 'up' : 'down'}
          trendValue={`${(stats?.executions.change || 0) >= 0 ? '+' : ''}${stats?.executions.change || 0}%`}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest actions performed on the platform</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats?.recent_activity.map((activity) => (
                <div key={activity.id} className="flex items-center gap-4 border-b pb-4 last:border-0">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <FileText className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">{activity.document_name}</p>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        activity.status === 'completed' ? 'bg-green-100 text-green-700' :
                        activity.status === 'failed' ? 'bg-red-100 text-red-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                        {activity.status}
                      </span>
                      <p className="text-sm text-muted-foreground">{activity.time_ago}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Monthly Performance</CardTitle>
            <CardDescription>Platform usage statistics</CardDescription>
          </CardHeader>
          <CardContent>
            {stats?.monthly_stats && Object.keys(stats.monthly_stats).length > 0 ? (
              <MonthlyBarChart data={stats.monthly_stats} />
            ) : (
              <div className="h-[250px] flex items-center justify-center">
                <p className="text-muted-foreground">No data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>User Information</CardTitle>
          <CardDescription>Account information</CardDescription>
        </CardHeader>
        <CardContent>
          {user ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">ID</p>
                <p className="font-medium">{user.id}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Email</p>
                <p className="font-medium">{user.email}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Name</p>
                <p className="font-medium">{user.name || user.full_name || '-'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Role</p>
                <p className="font-medium">User</p>
              </div>
            </div>
          ) : (
            <p>Authenticated user</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
