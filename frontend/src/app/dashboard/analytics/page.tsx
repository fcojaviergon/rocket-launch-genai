'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { BarChart, LineChart, PieChart, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
import { useEffect, useState } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';

// Define interfaces for the data
interface AnalyticsData {
  monthly?: {
    users?: Record<string, number>;
    documents?: Record<string, number>;
    executions?: Record<string, number>;
  };
  weekly?: {
    users?: number[];
    executions?: number[];
  };
  document_types?: {
    counts?: Record<string, number>;
    percentages?: Record<string, number>;
  };
  popular_queries?: Array<{
    query: string;
    count: number;
  }>;
}

// Component to show skeleton during loading
function SkeletonCard() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-8 w-1/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-[200px] w-full" />
    </div>
  );
}

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Get real data from the API
  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const response = await api.stats.getAnalytics();
      
      // The data comes directly in the response, not inside a data object
      console.log('Analytics data received:', response);
      
      // Apply typing for logs
      const typedResponse = response as unknown as AnalyticsData;
      console.log('Weekly users:', typedResponse?.weekly?.users);
      console.log('Monthly users:', typedResponse?.monthly?.users);
      console.log('Document types:', typedResponse?.document_types);
      console.log('Popular queries:', typedResponse?.popular_queries);
      
      // Initialize empty arrays if they don't exist
      if (!typedResponse.weekly) {
        typedResponse.weekly = { users: [0,0,0,0,0,0,0], executions: [0,0,0,0,0,0,0] };
      }
      
      if (!typedResponse.weekly.users) {
        typedResponse.weekly.users = [0,0,0,0,0,0,0];
      }
      
      if (!typedResponse.weekly.executions) {
        typedResponse.weekly.executions = [0,0,0,0,0,0,0];
      }
      
      setAnalyticsData(typedResponse);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error('Error al obtener datos analíticos:', err);
      setError('No se pudieron cargar los datos analíticos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Load data initially
    fetchAnalytics();

    // Configure automatic refresh every 30 seconds
    const intervalId = setInterval(() => {
      console.log('Refreshing analytics data...');
      fetchAnalytics();
    }, 30000);

    // Clean up interval when unmounting
    return () => clearInterval(intervalId);
  }, []);

  // Function to process monthly data from the backend
  const processMonthlyData = (data: Record<string, number>) => {
    const months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    const sortedData = Object.entries(data || {})
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, value]) => {
        const month = parseInt(key.split('-')[1], 10) - 1; // Extract the month (0-11)
        return { month: months[month], value };
      });
    
    console.log('Monthly data processed:', sortedData);
    return sortedData;
  };

  // Process data for graphs (only if data is available)
  const userMonthlyData = analyticsData?.monthly?.users ? 
    processMonthlyData(analyticsData.monthly.users) : [];
  
  const docTypeData = analyticsData?.document_types?.percentages ? 
    Object.entries(analyticsData.document_types.percentages).map(([type, percentage]) => ({
      label: type,
      value: percentage as number,
      color: getColorForDocType(type)
    })) : [];
  
  const weeklyActivityData = [
    { day: 'Lun', users: 0, queries: 0 },
    { day: 'Mar', users: 0, queries: 0 },
    { day: 'Mié', users: 0, queries: 0 },
    { day: 'Jue', users: 0, queries: 0 },
    { day: 'Vie', users: 0, queries: 0 },
    { day: 'Sáb', users: 0, queries: 0 },
    { day: 'Dom', users: 0, queries: 0 },
  ];
  
  // Calculate maximum values for scaling graphs
  const maxWeeklyUser = analyticsData?.weekly?.users ? 
    Math.max(...analyticsData.weekly.users, 1) : 1; // Avoid division by zero
  
  const maxWeeklyExecution = analyticsData?.weekly?.executions ?
    Math.max(...analyticsData.weekly.executions, 1) : 1;
  
  const maxMonthlyUser = userMonthlyData.length > 0 ?
    Math.max(...userMonthlyData.map(item => item.value), 1) : 1;

  // Function to calculate relative height (maximum 200px)
  const calculateBarHeight = (value: number, maxValue: number): number => {
    const MAX_HEIGHT = 200;
    // Ensure a minimum visible value for small but greater than zero values
    return value === 0 ? 0 : Math.max(20, (value / maxValue) * MAX_HEIGHT);
  };

  // Function to assign color based on document type
  function getColorForDocType(type: string): string {
    const colorMap: Record<string, string> = {
      'pdf': 'bg-blue-500',
      'docx': 'bg-green-500',
      'txt': 'bg-orange-500',
      'csv': 'bg-purple-500',
      'xlsx': 'bg-yellow-500',
      'image': 'bg-rose-500',
      'none': 'bg-gray-500'  // Color para documentos sin tipo
    };
    
    // If type is null or "None", use "none"
    const normalizedType = (type && type.toLowerCase() !== 'none') ? type.toLowerCase() : 'none';
    return colorMap[normalizedType] || 'bg-gray-500';
  }

  // Calculation of the total for the pie chart
  const pieTotal = docTypeData.reduce((sum, item) => sum + item.value, 0);

  // Helper function to sum an array of numbers
  const sumValues = (values: number[]): number => {
    return values.reduce((a, b) => a + b, 0);
  };

  if (error) {
    return (
      <div className="p-6 w-full">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">Visualize the performance of your platform</p>
        </div>
        <div className="p-4 bg-red-50 text-red-700 rounded-md">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 w-full">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">Visualize the performance of your platform</p>
        </div>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              Updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <Button 
            variant="outline" 
            size="sm" 
            className="gap-1"
            onClick={fetchAnalytics}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Update
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="mb-6">
        <TabsList className="mb-4">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <BarChart className="h-4 w-4" />
            <span>General</span>
          </TabsTrigger>
          <TabsTrigger value="users" className="flex items-center gap-2">
            <LineChart className="h-4 w-4" />
            <span>Users</span>
          </TabsTrigger>
          <TabsTrigger value="content" className="flex items-center gap-2">
            <PieChart className="h-4 w-4" />
            <span>Content</span>
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle>Active users</CardTitle>
                <CardDescription>Total of active users in the last month</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <SkeletonCard />
                ) : (
                  <>
                    <div className="text-3xl font-bold">
                      {analyticsData?.monthly?.users ? 
                        sumValues(Object.values(analyticsData.monthly.users)) : 
                        0}
                    </div>
                    <div className="mt-4 h-[200px] flex items-end gap-2">
                      {analyticsData?.weekly?.users && analyticsData.weekly.users.some(val => val > 0) ? (
                        weeklyActivityData.map((item, i) => (
                          <div key={i} className="flex-1 flex flex-col items-center">
                            <div 
                              className="w-full bg-primary rounded-t-sm" 
                              style={{ height: `${calculateBarHeight(analyticsData?.weekly?.users?.[i] || 0, maxWeeklyUser)}px` }}
                            />
                            <span className="text-xs text-muted-foreground mt-1">{item.day}</span>
                          </div>
                        ))
                      ) : (
                        <div className="w-full flex items-center justify-center text-muted-foreground text-sm py-8">
                          <div className="text-center">
                            <div className="mb-2">No data of recent activity</div>
                            <div className="text-xs">Received data: {JSON.stringify(analyticsData?.weekly?.users || [])}</div>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle>Queries</CardTitle>
                <CardDescription>Total of queries made</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <SkeletonCard />
                ) : (
                  <>
                    <div className="text-3xl font-bold">
                      {analyticsData?.monthly?.executions ? 
                        sumValues(Object.values(analyticsData.monthly.executions)) : 
                        0}
                    </div>
                    <div className="mt-4 h-[200px] flex items-end gap-2">
                      {analyticsData?.weekly?.executions && analyticsData.weekly.executions.some(val => val > 0) ? (
                        weeklyActivityData.map((item, i) => (
                          <div key={i} className="flex-1 flex flex-col items-center">
                            <div 
                              className="w-full bg-green-500 rounded-t-sm" 
                              style={{ height: `${calculateBarHeight(analyticsData?.weekly?.executions?.[i] || 0, maxWeeklyExecution)}px` }}
                            />
                            <span className="text-xs text-muted-foreground mt-1">{item.day}</span>
                          </div>
                        ))
                      ) : (
                        <div className="w-full flex items-center justify-center text-muted-foreground text-sm py-8">
                          <div className="text-center">
                            <div className="mb-2">No data of recent queries</div>
                            <div className="text-xs">Received data: {JSON.stringify(analyticsData?.weekly?.executions || [])}</div>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle>Usage distribution</CardTitle>
                <CardDescription>Distribution by document type</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <SkeletonCard />
                ) : docTypeData.length > 0 ? (
                  <>
                    <div className="flex justify-center mb-4">
                      <div className="relative h-[180px] w-[180px] rounded-full">
                        {docTypeData.map((item, index) => {
                          const startAngle = docTypeData
                            .slice(0, index)
                            .reduce((sum, i) => sum + (i.value / pieTotal) * 360, 0);
                          const endAngle = startAngle + (item.value / pieTotal) * 360;
                          
                          return (
                            <div
                              key={index}
                              className={`absolute inset-0 ${item.color}`}
                              style={{
                                clipPath: `path('M90,90 L90,0 A90,90 0 ${
                                  endAngle - startAngle > 180 ? 1 : 0
                                },1 ${
                                  90 + 90 * Math.cos((endAngle * Math.PI) / 180)
                                },${
                                  90 + 90 * Math.sin((endAngle * Math.PI) / 180)
                                } Z')`,
                                transform: `rotate(${startAngle}deg)`,
                              }}
                            />
                          );
                        })}
                        <div className="absolute inset-[15%] bg-card rounded-full flex items-center justify-center">
                          <span className="font-bold">100%</span>
                        </div>
                      </div>
                    </div>
                    <div className="space-y-2">
                      {docTypeData.map((item, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <div className={`h-3 w-3 rounded-full ${item.color}`} />
                          <span className="text-sm">{item.label}</span>
                          <span className="text-sm text-muted-foreground ml-auto">{item.value}%</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="h-[220px] flex items-center justify-center text-muted-foreground">
                    No data of distribution available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        <TabsContent value="users">
          <Card>
            <CardHeader>
              <CardTitle>User growth</CardTitle>
              <CardDescription>New users registered by month</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="h-[300px] flex items-center justify-center">
                  <Skeleton className="h-[280px] w-full" />
                </div>
              ) : userMonthlyData.length > 0 ? (
                <div className="h-[300px] flex items-end gap-2">
                  {userMonthlyData.map((item, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-2">
                      <div 
                        className="w-full bg-primary/80 rounded-t-sm" 
                        style={{ height: `${calculateBarHeight(item.value, maxMonthlyUser)}px` }}
                      />
                      <span className="text-xs text-muted-foreground">
                        {item.month}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground flex-col">
                  <div>No data of users available</div>
                  <div className="text-xs mt-2">Monthly data: {JSON.stringify(analyticsData?.monthly?.users || {})}</div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="content">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Processed documents</CardTitle>
                <CardDescription>Total of processed documents by type</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <SkeletonCard />
                ) : (
                  <div className="space-y-4">
                    {Object.entries(analyticsData?.document_types?.counts || {}).length > 0 ? (
                      Object.entries(analyticsData?.document_types?.counts || {}).map(([type, count], i) => (
                        <div key={i} className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{type === 'None' ? 'Without type' : type}</span>
                            <span className="text-sm text-muted-foreground">{count} documents</span>
                          </div>
                          <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-primary rounded-full" 
                              style={{ width: `${analyticsData?.document_types?.percentages?.[type] || 0}%` }}
                            />
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center text-muted-foreground py-8">
                        No data of documents available
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle>Popular queries</CardTitle>
                <CardDescription>Most frequent queries</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <SkeletonCard />
                ) : (
                  <div className="space-y-4">
                    {(analyticsData?.popular_queries && analyticsData.popular_queries.length > 0) ? (
                      analyticsData.popular_queries.map((item, i) => (
                        <div key={i} className="flex items-center justify-between pb-3 border-b last:border-0">
                          <div>
                            <p className="font-medium">{item.query}</p>
                            <p className="text-sm text-muted-foreground">{item.count} veces</p>
                          </div>
                          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                            {i + 1}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center text-muted-foreground py-4">
                        <div>No popular queries registered</div>
                        <div className="text-xs mt-2">Received data: {JSON.stringify(analyticsData?.popular_queries || [])}</div>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}