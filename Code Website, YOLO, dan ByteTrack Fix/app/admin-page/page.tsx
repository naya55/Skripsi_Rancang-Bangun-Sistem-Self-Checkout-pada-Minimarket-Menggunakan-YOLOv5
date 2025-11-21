'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import ProductModal from '@/components/admin/ProductModal';
import HistoryModal from '@/components/history/HistoryModal';
import { Package, LogOut, ShoppingBag, History } from 'lucide-react';

export default function AdminPage() {
  const { user, loading, logout, isLoggingOut } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
  };

  if (loading || isLoggingOut) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Package className="h-12 w-12 text-primary mx-auto mb-4 animate-spin" />
          <p className="text-muted-foreground">
            {isLoggingOut ? 'Keluar dari sistem...' : 'Memuat halaman admin...'}
          </p>
        </div>
      </div>
    );
  }

  if (!loading && !isLoggingOut && (!user || user.role !== 'admin')) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Akses Ditolak</h2>
          <p className="text-muted-foreground mb-4">Silakan login sebagai admin terlebih dahulu.</p>
          <Button 
            onClick={() => router.push('/')}
            className="bg-blue-500 text-white hover:bg-blue-600"
          >
            Kembali ke Login
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="bg-card shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Package className="h-8 w-8 text-primary mr-3" />
              <div>
                <h1 className="text-xl font-bold text-foreground">Admin Dashboard</h1>
                <p className="text-sm text-muted-foreground">
                  Selamat datang, {user?.displayName || user?.email}
                </p>
              </div>
            </div>
            
            <Button 
              variant="outline" 
              onClick={handleLogout}
              className="flex items-center gap-2"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-foreground mb-2">
            Dashboard Admin
          </h2>
          <p className="text-muted-foreground">
            Kelola produk dan riwayat transaksi sistem self-checkout
          </p>
        </div>

        {/* Main Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Product Management Card */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader className="pb-4">
              <div className="flex items-center space-x-3">
                <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <ShoppingBag className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">Manajemen Produk</CardTitle>
                  <CardDescription>Kelola produk dan inventori toko</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ProductModal />
            </CardContent>
          </Card>

          {/* Transaction History Card */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader className="pb-4">
              <div className="flex items-center space-x-3">
                <div className="p-3 bg-green-100 dark:bg-green-900 rounded-lg">
                  <History className="h-8 w-8 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">Riwayat Transaksi</CardTitle>
                  <CardDescription>Lihat dan kelola riwayat transaksi</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <HistoryModal />
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}