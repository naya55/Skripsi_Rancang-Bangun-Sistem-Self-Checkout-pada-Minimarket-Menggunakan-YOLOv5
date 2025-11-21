'use client';

import { useEffect, useState } from 'react';
import { useSocket } from '@/hooks/useSocket';
import { useSettingsSync } from '@/hooks/useSettingsSync';
import { useAuth } from '@/contexts/AuthContext';
import ScannerView from '@/components/scanner/ScannerView';
import CartSidebar from '@/components/cart/CartSidebar';
import ConfigWindow from '@/components/config/ConfigWindow';
import SimulationWindow from '@/components/simulation/SimulationWindow';
import Notification from '@/components/ui/notification';
import { Button } from '@/components/ui/button';
import { Package, LogOut } from 'lucide-react';

export default function UserPage() {
  const socket = useSocket();
  useSettingsSync();
  const { logout } = useAuth();
  const [isClient, setIsClient] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const handleLogout = async () => {
    await logout();
  };

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (isClient && socket.isConnected && socket.getProducts) {
      socket.getProducts();
    }
  }, [isClient, socket]);

  if (!isClient) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Package className="h-12 w-12 text-primary mx-auto mb-4 animate-spin" />
          <p className="text-muted-foreground">Memuat Sistem Self-Checkout...</p>
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
              <div 
                className="cursor-pointer hover:text-primary/80 transition-colors mr-3" 
                onClick={() => setShowSettings(true)}
                title="Konfigurasi Sistem"
              >
                <Package className="h-8 w-8 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">Sistem Self-Checkout</h1>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <Button 
                variant="outline" 
                onClick={handleLogout}
                className="flex items-center gap-2"
                title="Keluar dari sistem"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-8rem)]">
          <div className="lg:col-span-2">
            <ScannerView />
          </div>
          <div className="lg:col-span-1">
            <CartSidebar />
          </div>
        </div>
      </main>

      <SimulationWindow />
      <Notification message={socket.notification} />
      
      <ConfigWindow 
        isOpen={showSettings} 
        onClose={() => setShowSettings(false)} 
      />
    </div>
  );
}