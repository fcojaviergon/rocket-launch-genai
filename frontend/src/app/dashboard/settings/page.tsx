'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { useAuth } from '@/providers/auth-provider';
import { api } from '@/lib/api';

// Define validation schemas with Zod
const profileFormSchema = z.object({
  fullName: z.string().min(2, {
    message: 'The name must be at least 2 characters',
  }),
  email: z.string().email({
    message: 'Enter a valid email',
  }),
});

const passwordFormSchema = z.object({
  currentPassword: z.string().min(1, {
    message: 'The current password is required',
  }),
  newPassword: z.string().min(8, {
    message: 'The new password must be at least 8 characters',
  }),
  confirmPassword: z.string().min(8, {
    message: 'Confirm the new password',
  }),
}).refine((data) => data.newPassword === data.confirmPassword, {
  path: ['confirmPassword'],
  message: 'The passwords do not match',
});

type ProfileFormValues = z.infer<typeof profileFormSchema>;
type PasswordFormValues = z.infer<typeof passwordFormSchema>;

export default function SettingsPage() {
  const { session } = useAuth();
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [loadingPassword, setLoadingPassword] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [userData, setUserData] = useState<any>(null);
  
  // Profile form
  const profileForm = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      fullName: '',
      email: '',
    },
  });

  // Password form
  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordFormSchema),
    defaultValues: {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    },
  });

  // Load user data
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const response = await api.users.getMe();
        const data = response as any;
        setUserData(data);
        
        profileForm.reset({
          fullName: data.full_name || '',
          email: data.email || '',
        });
      } catch (error) {
        console.error('Error loading user data:', error);
      }
    };

    if (session) {
      fetchUserData();
    }
  }, [session, profileForm]);

  // Update profile
  const onProfileSubmit = async (data: ProfileFormValues) => {
    setLoadingProfile(true);
    setSuccessMessage(null);
    setErrorMessage(null);
    
    try {
      await api.users.updateMe({
        full_name: data.fullName,
        email: data.email,
      });
      
      setSuccessMessage('Profile updated correctly');
      
      // Reload the page to update the data in the session
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } catch (error: any) {
      console.error('Error updating profile:', error);
      setErrorMessage(error.response?.data?.detail || 'Error updating profile');
    } finally {
      setLoadingProfile(false);
    }
  };

  // Update password
  const onPasswordSubmit = async (data: PasswordFormValues) => {
    setLoadingPassword(true);
    setSuccessMessage(null);
    setErrorMessage(null);
    
    try {
      await api.users.updateMyPassword({
        current_password: data.currentPassword,
        new_password: data.newPassword,
      });
      
      setSuccessMessage('Password updated correctly');
      passwordForm.reset();
    } catch (error: any) {
      console.error('Error updating password:', error);
      setErrorMessage(error.response?.data?.detail || 'Error updating password');
    } finally {
      setLoadingPassword(false);
    }
  };

  return (
    <div className="p-6 w-full">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and preferences</p>
      </div>

      {successMessage && (
        <div className="mb-4 p-4 rounded-md bg-green-50 border border-green-200 text-green-700">
          {successMessage}
        </div>
      )}

      {errorMessage && (
        <div className="mb-4 p-4 rounded-md bg-red-50 border border-red-200 text-red-700">
          {errorMessage}
        </div>
      )}

      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="account">Security</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>
        
        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile information</CardTitle>
              <CardDescription>Update your personal information</CardDescription>
            </CardHeader>
            <Form {...profileForm}>
              <form onSubmit={profileForm.handleSubmit(onProfileSubmit)}>
                <CardContent className="space-y-4">
                  <FormField
                    control={profileForm.control}
                    name="fullName"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Full name</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={profileForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Email</FormLabel>
                        <FormControl>
                          <Input {...field} type="email" />
                        </FormControl>
                        <FormDescription>
                          This email will be used to log in and receive notifications.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
                <CardFooter>
                  <Button type="submit" disabled={loadingProfile}>
                    {loadingProfile ? 'Saving...' : 'Save changes'}
                  </Button>
                </CardFooter>
              </form>
            </Form>
          </Card>
        </TabsContent>
        
        <TabsContent value="account">
          <Card>
            <CardHeader>
              <CardTitle>Account security</CardTitle>
              <CardDescription>Update your password and security configuration</CardDescription>
            </CardHeader>
            <Form {...passwordForm}>
              <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)}>
                <CardContent className="space-y-4">
                  <FormField
                    control={passwordForm.control}
                    name="currentPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Current password</FormLabel>
                        <FormControl>
                          <Input type="password" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                      control={passwordForm.control}
                      name="newPassword"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>New password</FormLabel>
                          <FormControl>
                            <Input type="password" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={passwordForm.control}
                      name="confirmPassword"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Confirm password</FormLabel>
                          <FormControl>
                            <Input type="password" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </CardContent>
                <CardFooter>
                  <Button type="submit" disabled={loadingPassword}>
                    {loadingPassword ? 'Updating...' : 'Update password'}
                  </Button>
                </CardFooter>
              </form>
            </Form>
          </Card>
        </TabsContent>
        
        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification preferences</CardTitle>
              <CardDescription>Configure how you want to receive notifications</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <h3 className="text-lg font-medium">Email notifications</h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">System updates</p>
                    <p className="text-sm text-muted-foreground">Receive notifications about important changes</p>
                  </div>
                  <Switch id="system-updates" defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">New features</p>
                    <p className="text-sm text-muted-foreground">Receive notifications about new features and improvements</p>
                  </div>
                  <Switch id="new-features" defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Monthly newsletter</p>
                    <p className="text-sm text-muted-foreground">Monthly summary of activity and tips</p>
                  </div>
                  <Switch id="monthly-newsletter" />
                </div>
              </div>
              
              <Separator className="my-4" />
              
              <div className="space-y-4">
                <h3 className="text-lg font-medium">Application notifications</h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">New messages</p>
                    <p className="text-sm text-muted-foreground">When you receive a new message</p>
                  </div>
                  <Switch id="new-messages" defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Document processing</p>
                    <p className="text-sm text-muted-foreground">When a document is processed</p>
                  </div>
                  <Switch id="document-processing" defaultChecked />
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button>
                Save preferences
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
