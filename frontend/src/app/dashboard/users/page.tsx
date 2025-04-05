'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/providers/auth-provider';
import { api } from '@/lib/api';
import { Trash2, Edit, UserPlus, Search, X } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';

// Define validation schemas with Zod
const userFormSchema = z.object({
  email: z.string().email({
    message: 'Enter a valid email',
  }),
  full_name: z.string().min(2, {
    message: 'The name must be at least 2 characters',
  }),
  password: z.string().min(8, {
    message: 'The password must be at least 8 characters',
  }).optional().or(z.literal('')),
  role: z.enum(['user', 'admin', 'superadmin']),
  is_active: z.boolean().default(true),
});

type UserFormValues = z.infer<typeof userFormSchema>;

export default function UsersPage() {
  const { session } = useAuth();
  const [users, setUsers] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [userRole, setUserRole] = useState<string>('user');

  const form = useForm<UserFormValues>({
    resolver: zodResolver(userFormSchema),
    defaultValues: {
      email: '',
      full_name: '',
      password: '',
      role: 'user',
      is_active: true,
    },
  });

  // Obtener el rol del usuario actual
  useEffect(() => {
    if (session?.user) {
      const user = session.user as any;
      setUserRole(user.role || 'user');
    }
  }, [session]);

  // Función para cargar usuarios
  const loadUsers = async () => {
    try {
      setIsLoading(true);
      const response = await api.users.getAll(page, pageSize, search || undefined);
      const data = response as any;
      
      setUsers(data.items || []);
      setTotalPages(data.pages || 1);
    } catch (error: any) {
      console.error('Error al cargar usuarios:', error);
      setErrorMessage(error.response?.data?.detail || 'Error al cargar usuarios');
    } finally {
      setIsLoading(false);
    }
  };

  // Cargar usuarios al iniciar o cuando cambian los parámetros
  useEffect(() => {
    if (session) {
      loadUsers();
    }
  }, [session, page, search]);

  // Abrir diálogo para crear o editar usuario
  const openEditDialog = (user?: any) => {
    if (user) {
      form.reset({
        email: user.email,
        full_name: user.full_name,
        password: '',
        role: user.role,
        is_active: user.is_active,
      });
      setSelectedUser(user);
    } else {
      form.reset({
        email: '',
        full_name: '',
        password: '',
        role: 'user',
        is_active: true,
      });
      setSelectedUser(null);
    }
    setIsEditDialogOpen(true);
  };

  // Guardar usuario (crear o actualizar)
  const handleSubmit = async (data: UserFormValues) => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      
      // Si no se proporciona contraseña en edición, eliminarla del objeto
      if (selectedUser && (!data.password || data.password.trim() === '')) {
        delete data.password;
      }
      
      if (selectedUser) {
        // Actualizar usuario existente
        await api.users.update(selectedUser.id, data);
        setSuccessMessage('Usuario actualizado correctamente');
      } else {
        // Crear nuevo usuario
        await api.users.create(data as any);
        setSuccessMessage('Usuario creado correctamente');
      }
      
      setIsEditDialogOpen(false);
      loadUsers();
    } catch (error: any) {
      console.error('Error al guardar usuario:', error);
      setErrorMessage(error.response?.data?.detail || 'Error al guardar usuario');
    } finally {
      setIsLoading(false);
    }
  };

  // Eliminar usuario
  const handleDelete = async (userId: string) => {
    if (!confirm('¿Estás seguro de eliminar este usuario?')) {
      return;
    }
    
    try {
      setIsLoading(true);
      await api.users.delete(userId);
      setSuccessMessage('Usuario eliminado correctamente');
      loadUsers();
    } catch (error: any) {
      console.error('Error al eliminar usuario:', error);
      setErrorMessage(error.response?.data?.detail || 'Error al eliminar usuario');
    } finally {
      setIsLoading(false);
    }
  };

  // Verificar si el usuario actual puede editar a otro usuario
  const canEditUser = (targetUser: any) => {
    if (userRole === 'superadmin') return true;
    if (userRole === 'admin' && targetUser.role !== 'superadmin') return true;
    return false;
  };

  // Verificar si se puede cambiar el rol de un usuario
  const canChangeRole = (targetUser: any, newRole: string) => {
    if (userRole === 'superadmin') return true;
    if (userRole === 'admin' && newRole !== 'superadmin' && targetUser.role !== 'superadmin') return true;
    return false;
  };

  return (
    <div className="p-6 w-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">User management</h1>
          <p className="text-muted-foreground">Manage the system users</p>
        </div>
        {(userRole === 'admin' || userRole === 'superadmin') && (
          <Button onClick={() => openEditDialog()} className="flex items-center gap-2">
            <UserPlus className="h-4 w-4" />
            <span>New User</span>
          </Button>
        )}
      </div>

      {errorMessage && (
        <div className="mb-4 p-4 rounded-md bg-red-50 border border-red-200 text-red-700">
          {errorMessage}
          <button 
            className="float-right text-red-700" 
            onClick={() => setErrorMessage(null)}
            aria-label="Cerrar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {successMessage && (
        <div className="mb-4 p-4 rounded-md bg-green-50 border border-green-200 text-green-700">
          {successMessage}
          <button 
            className="float-right text-green-700" 
            onClick={() => setSuccessMessage(null)}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <Card className="mb-6">
        <CardHeader className="pb-3">
          <CardTitle>User list</CardTitle>
          <CardDescription>
            {users.length} users in total
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex justify-between mb-4">
            <div className="relative w-72">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name or email"
                className="pl-8"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                      {isLoading ? 'Loading users...' : 'No users found'}
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>{user.full_name}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          user.role === 'superadmin' 
                            ? 'bg-purple-100 text-purple-800'
                            : user.role === 'admin'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {user.role || 'user'}
                        </span>
                      </TableCell>
                      <TableCell>
                        {user.is_active ? (
                          <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                            Active
                          </span>
                        ) : (
                          <span className="px-2 py-1 rounded-full text-xs bg-red-100 text-red-800">
                            Inactive
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          {canEditUser(user) && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => openEditDialog(user)}
                                className="h-8 w-8 p-0"
                              >
                                <Edit className="h-4 w-4" />
                                <span className="sr-only">Edit</span>
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => handleDelete(user.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                                <span className="sr-only">Delete</span>
                              </Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {totalPages > 1 && (
            <div className="flex justify-center mt-4">
              <div className="flex gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <div className="flex items-center gap-1 mx-2">
                  <span>Page {page} of {totalPages}</span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{selectedUser ? 'Edit User' : 'Create User'}</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4 pt-4">
              <FormField
                control={form.control}
                name="full_name"
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
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{selectedUser ? 'New password (optional)' : 'Password'}</FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Role</FormLabel>
                    <Select
                      disabled={selectedUser && !canChangeRole(selectedUser, field.value)}
                      onValueChange={field.onChange}
                      value={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Seleccionar rol" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="user">User</SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                        {userRole === 'superadmin' && (
                          <SelectItem value="superadmin">Super Admin</SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3">
                    <div className="space-y-0.5">
                      <FormLabel>Active user</FormLabel>
                    </div>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
              
              <Separator />
              
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsEditDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isLoading}>
                  {isLoading ? 'Saving...' : 'Save'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
