'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Package, ShoppingCart, Settings, ArrowLeft, Eye, EyeOff } from 'lucide-react';

type ViewMode = 'select' | 'admin-login' | 'admin-register';

export default function HomePage() {
  const router = useRouter();
  const { login, register, loading, error, clearError } = useAuth();
  const [mode, setMode] = useState<ViewMode>('select');
  
  const [loginForm, setLoginForm] = useState({
    email: '',
    password: ''
  });
  
  const [registerForm, setRegisterForm] = useState({
    email: '',
    password: '',
    displayName: ''
  });

  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);


  const handleUserAccess = () => {
    router.push('/user');
  };

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    
    const success = await login(loginForm.email, loginForm.password);
    
    if (success) {
      router.push('/admin-page');
    }
  };

  const handleAdminRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    
    const success = await register(registerForm.email, registerForm.password, registerForm.displayName);
    
    if (success) {
      router.push('/admin-page');
    }
  };

  const resetForms = () => {
    setLoginForm({ email: '', password: '' });
    setRegisterForm({ email: '', password: '', displayName: '' });
    setShowLoginPassword(false);
    setShowRegisterPassword(false);
    clearError();
  };

  const goBack = () => {
    setMode('select');
    resetForms();
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="bg-card shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              {mode !== 'select' && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={goBack}
                  className="mr-3"
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              )}
              <Package className="h-8 w-8 text-primary mr-3" />
              <div>
                <h1 className="text-xl font-bold text-foreground">Sistem Self-Checkout</h1>
                <p className="text-sm text-muted-foreground">
                  {mode === 'select' && 'Pilih cara akses sistem'}
                  {mode === 'admin-login' && 'Login Admin'}
                  {mode === 'admin-register' && 'Register Admin'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-md mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-md">
            <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
          </div>
        )}

        {mode === 'select' && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-foreground mb-2">Selamat Datang</h2>
              <p className="text-muted-foreground">Pilih cara Anda mengakses sistem</p>
            </div>

            <div className="grid gap-4">
              <Card 
                className="cursor-pointer hover:shadow-md transition-shadow border-2 hover:border-primary/20"
                onClick={() => setMode('admin-login')}
              >
                <CardContent className="p-6 text-center">
                  <Settings className="h-12 w-12 mx-auto mb-4 text-primary" />
                  <h3 className="text-lg font-semibold mb-2">Admin</h3>
                  <p className="text-sm text-muted-foreground">
                    Kelola sistem dan produk
                  </p>
                </CardContent>
              </Card>

              <Card 
                className="cursor-pointer hover:shadow-md transition-shadow border-2 hover:border-primary/20"
                onClick={handleUserAccess}
              >
                <CardContent className="p-6 text-center">
                  <ShoppingCart className="h-12 w-12 mx-auto mb-4 text-primary" />
                  <h3 className="text-lg font-semibold mb-2">User</h3>
                  <p className="text-sm text-muted-foreground">
                    Langsung mulai belanja
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {mode === 'admin-login' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-center">Admin Login</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <form onSubmit={handleAdminLogin} className="space-y-4">
                <div>
                  <Label htmlFor="login-email">Email</Label>
                  <Input
                    id="login-email"
                    type="email"
                    value={loginForm.email}
                    onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                    placeholder="admin@example.com"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="login-password">Password</Label>
                  <div className="relative">
                    <Input
                      id="login-password"
                      type={showLoginPassword ? "text" : "password"}
                      value={loginForm.password}
                      onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                      placeholder="••••••••"
                      required
                      className="pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                      onClick={() => setShowLoginPassword(!showLoginPassword)}
                    >
                      {showLoginPassword ? (
                        <EyeOff className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <Eye className="h-4 w-4 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Memuat...' : 'Login'}
                </Button>
              </form>
              
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">
                  Belum punya akun admin?
                </p>
                <Button 
                  variant="outline" 
                  onClick={() => setMode('admin-register')}
                  className="w-full"
                >
                  Register Admin
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {mode === 'admin-register' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-center">Register Admin</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <form onSubmit={handleAdminRegister} className="space-y-4">
                <div>
                  <Label htmlFor="register-name">Nama Lengkap</Label>
                  <Input
                    id="register-name"
                    type="text"
                    value={registerForm.displayName}
                    onChange={(e) => setRegisterForm({ ...registerForm, displayName: e.target.value })}
                    placeholder="John Doe"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="register-email">Email</Label>
                  <Input
                    id="register-email"
                    type="email"
                    value={registerForm.email}
                    onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                    placeholder="admin@example.com"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="register-password">Password</Label>
                  <div className="relative">
                    <Input
                      id="register-password"
                      type={showRegisterPassword ? "text" : "password"}
                      value={registerForm.password}
                      onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                      placeholder="••••••••"
                      required
                      minLength={6}
                      className="pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                      onClick={() => setShowRegisterPassword(!showRegisterPassword)}
                    >
                      {showRegisterPassword ? (
                        <EyeOff className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <Eye className="h-4 w-4 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Minimal 6 karakter
                  </p>
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Memuat...' : 'Register'}
                </Button>
              </form>
              
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">
                  Sudah punya akun admin?
                </p>
                <Button 
                  variant="outline" 
                  onClick={() => setMode('admin-login')}
                  className="w-full"
                >
                  Login Admin
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}