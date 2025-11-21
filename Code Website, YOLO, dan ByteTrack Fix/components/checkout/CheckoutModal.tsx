'use client';

import { useState, useEffect, useRef } from 'react';
import { useSocket } from '@/hooks/useSocket';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { CreditCard, CheckCircle, Loader2, Clock, XCircle } from 'lucide-react';

interface CheckoutModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface PaymentData {
  transaction_id: string;
  order_id: string;
  snap_token: string;
  payment_url: string;
  qr_code_url?: string;
  expires_at: string;
  environment: string;
}

interface CartDetails {
  price: number;
  quantity: number;
}

interface SnapResult {
  order_id: string;
  transaction_status: string;
  payment_type: string;
  gross_amount: string;
}

interface PaymentEventData {
  success?: boolean;
  error?: string;
  snap_token?: string;
  order_id?: string;
  transaction_status?: string;
  payment_url?: string;
  transaction_id?: string;
  qr_code_url?: string;
  expires_at?: string;
  environment?: string;
  payment_successful?: boolean;
  payment_failed?: boolean;
  payment_pending?: boolean;
}

type PaymentStatus = 'idle' | 'creating' | 'pending' | 'success' | 'failed' | 'expired' | 'cancelled';

// Midtrans Snap type declaration
declare global {
  interface Window {
    snap?: {
      pay: (token: string, options: {
        onSuccess: (result: SnapResult) => void;
        onPending: (result: SnapResult) => void;
        onError: (result: SnapResult) => void;
        onClose?: () => void;
      }) => void;
    };
  }
}

export default function CheckoutModal({ open, onOpenChange }: CheckoutModalProps) {
  const socket = useSocket();
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus>('idle');
  const [paymentData, setPaymentData] = useState<PaymentData | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [snapPopupOpen, setSnapPopupOpen] = useState(false);
  const snapScriptLoaded = useRef(false);
  
  // Load Midtrans Snap script
  const loadSnapScript = () => {
    return new Promise<void>((resolve, reject) => {
      if (snapScriptLoaded.current) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      const clientKey = process.env.NEXT_PUBLIC_MIDTRANS_ENVIRONMENT === 'production' 
        ? process.env.NEXT_PUBLIC_MIDTRANS_CLIENT_KEY_PRODUCTION
        : process.env.NEXT_PUBLIC_MIDTRANS_CLIENT_KEY_SANDBOX;
      
      script.src = process.env.NEXT_PUBLIC_MIDTRANS_ENVIRONMENT === 'production'
        ? 'https://app.midtrans.com/snap/snap.js'
        : 'https://app.sandbox.midtrans.com/snap/snap.js';
      
      
      script.setAttribute('data-client-key', clientKey || '');
      script.onload = () => {
        snapScriptLoaded.current = true;
        resolve();
      };
      script.onerror = (error) => {
        console.error('Failed to load Snap script:', error);
        reject(error);
      };
      
      document.head.appendChild(script);
    });
  };

  // Convert cart to items format for payment
  const getCartItems = () => {
    return Object.entries(socket.cart).map(([name, details]: [string, CartDetails]) => ({
      product_id: name.toLowerCase().replace(/\s+/g, '_'),
      name: name,
      price: details.price,
      quantity: details.quantity
    }));
  };

  // Create payment with Midtrans
  const handleCreatePayment = async () => {
    try {
      setPaymentStatus('creating');
      setErrorMessage('');
      
      const cartItems = getCartItems();
      
      if (cartItems.length === 0) {
        setErrorMessage('Keranjang kosong');
        setPaymentStatus('idle');
        return;
      }

      // Create payment via Socket.IO
      socket.socket?.emit('create_payment', {
        items: cartItems,
        total: socket.total,
        customer: {
          first_name: 'Self Checkout',
          last_name: 'Customer',
          email: 'customer@selfcheckout.com',
          phone: '+62812345678'
        }
      });
      
    } catch (error) {
      console.error('Error creating payment:', error);
      setErrorMessage('Gagal membuat pembayaran');
      setPaymentStatus('failed');
    }
  };

  // Open Snap payment page
  const handleOpenSnap = async () => {
    if (!paymentData?.snap_token) {
      return;
    }
    
    // Prevent opening if already open
    if (snapPopupOpen) {
      return;
    }
    
    try {
      await loadSnapScript();
      
      if (typeof window !== 'undefined' && window.snap) {
        setSnapPopupOpen(true);
        
        // Close modal dialog to prevent z-index conflicts
        onOpenChange(false);
        
        window.snap.pay(paymentData.snap_token, {
          onSuccess: (result: SnapResult) => {
            setSnapPopupOpen(false);
            setPaymentStatus('success');
            // Clear cart after successful payment
            setTimeout(() => {
              socket.checkoutComplete();
              resetPaymentState();
            }, 3000);
          },
          onPending: (result: SnapResult) => {
            setPaymentStatus('pending');
            // Re-open modal to show pending status
            setTimeout(() => onOpenChange(true), 500);
          },
          onError: (result: SnapResult) => {
            setSnapPopupOpen(false);
            setErrorMessage('Pembayaran gagal');
            setPaymentStatus('failed');
            // Re-open modal to show error
            setTimeout(() => onOpenChange(true), 500);
          },
          onClose: () => {
            setSnapPopupOpen(false);
            // Re-open modal when user closes popup
            setTimeout(() => onOpenChange(true), 500);
          }
        });
      } else {
        console.error('Snap script not available on window object');
        setErrorMessage('Snap script tidak tersedia');
        setPaymentStatus('failed');
      }
    } catch (error) {
      console.error('Error opening Snap:', error);
      setSnapPopupOpen(false);
      setErrorMessage('Gagal membuka halaman pembayaran');
      setPaymentStatus('failed');
    }
  };

  // Reset payment state
  const resetPaymentState = () => {
    setPaymentStatus('idle');
    setPaymentData(null);
    setErrorMessage('');
    setTimeRemaining(0);
    setSnapPopupOpen(false);
  };

  // Handle payment events from Socket.IO
  useEffect(() => {
    if (!socket.socket) return;

    const handlePaymentCreated = async (data: PaymentEventData) => {
      if (data.success && data.snap_token && data.order_id && data.transaction_id && data.payment_url && data.expires_at && data.environment) {
        const paymentData: PaymentData = {
          transaction_id: data.transaction_id,
          order_id: data.order_id,
          snap_token: data.snap_token,
          payment_url: data.payment_url,
          qr_code_url: data.qr_code_url,
          expires_at: data.expires_at,
          environment: data.environment
        };
        setPaymentData(paymentData);
        setPaymentStatus('pending');
        
        // Calculate time remaining
        const expiresAt = new Date(data.expires_at);
        const now = new Date();
        const remaining = Math.max(0, Math.floor((expiresAt.getTime() - now.getTime()) / 1000));
        setTimeRemaining(remaining);
        
        // Auto-open Snap popup with multiple retry attempts
        const tryOpenSnap = async (attempt = 1) => {
          // Wait for modal to be fully rendered
          await new Promise(resolve => setTimeout(resolve, 800));
          
          // Check if we can access the snap token
          if (data.snap_token) {
            try {
              await loadSnapScript();
              if (typeof window !== 'undefined' && window.snap) {
                setSnapPopupOpen(true);
                
                // Close modal dialog to prevent z-index conflicts
                onOpenChange(false);
                
                window.snap.pay(data.snap_token, {
                  onSuccess: (result: SnapResult) => {
                    setSnapPopupOpen(false);
                    setPaymentStatus('success');
                    setTimeout(() => {
                      socket.checkoutComplete();
                      resetPaymentState();
                    }, 3000);
                  },
                  onPending: (result: SnapResult) => {
                    setPaymentStatus('pending');
                    // Re-open modal to show pending status
                    setTimeout(() => onOpenChange(true), 500);
                  },
                  onError: (result: SnapResult) => {
                    setSnapPopupOpen(false);
                    setErrorMessage('Pembayaran gagal');
                    setPaymentStatus('failed');
                    // Re-open modal to show error
                    setTimeout(() => onOpenChange(true), 500);
                  },
                  onClose: () => {
                    setSnapPopupOpen(false);
                    // Re-open modal when user closes popup
                    setTimeout(() => onOpenChange(true), 500);
                  }
                });
              } else if (attempt < 3) {
                // Retry up to 3 times
                setTimeout(() => tryOpenSnap(attempt + 1), 1000);
              }
            } catch (error) {
              console.error('Error in auto-open:', error);
              if (attempt < 3) {
                setTimeout(() => tryOpenSnap(attempt + 1), 1000);
              }
            }
          }
        };
        
        tryOpenSnap();
      }
    };

    const handlePaymentError = (data: PaymentEventData) => {
      setErrorMessage(data.error || 'Gagal membuat pembayaran');
      setPaymentStatus('failed');
    };

    const handlePaymentStatusUpdate = (data: PaymentEventData) => {
      if (data.payment_successful) {
        setPaymentStatus('success');
        setTimeout(() => {
          socket.checkoutComplete();
          onOpenChange(false);
          resetPaymentState();
        }, 3000);
      } else if (data.payment_failed) {
        setPaymentStatus('failed');
        setErrorMessage('Pembayaran gagal atau dibatalkan');
      }
    };

    const handlePaymentCompleted = (data: PaymentEventData) => {
      setPaymentStatus('success');
      setTimeout(() => {
        socket.checkoutComplete();
        onOpenChange(false);
        resetPaymentState();
      }, 3000);
    };

    socket.socket.on('payment_created', handlePaymentCreated);
    socket.socket.on('payment_error', handlePaymentError);
    socket.socket.on('payment_status_update', handlePaymentStatusUpdate);
    socket.socket.on('payment_completed', handlePaymentCompleted);

    return () => {
      socket.socket?.off('payment_created', handlePaymentCreated);
      socket.socket?.off('payment_error', handlePaymentError);
      socket.socket?.off('payment_status_update', handlePaymentStatusUpdate);
      socket.socket?.off('payment_completed', handlePaymentCompleted);
    };
  }, [socket, onOpenChange]);

  // Countdown timer
  useEffect(() => {
    if (timeRemaining <= 0) return;

    const timer = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          setPaymentStatus('expired');
          setErrorMessage('Waktu pembayaran habis');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timeRemaining]);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      resetPaymentState();
    }
  }, [open]);

  // Format time remaining
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Success state
  if (paymentStatus === 'success') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="bg-card rounded-lg p-8 text-center space-y-4 mx-4 max-w-md w-full">
          <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
            <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
          </div>
          <h2 className="text-2xl font-bold text-foreground">Pembayaran Berhasil!</h2>
          <p className="text-muted-foreground">Terima kasih atas pembelian Anda</p>
          <p className="text-sm text-muted-foreground">
            Total: Rp {socket.total.toLocaleString()}
          </p>
          <div className="w-12 h-1 bg-green-500 rounded mx-auto animate-pulse"></div>
        </div>
      </div>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-center flex items-center justify-center gap-2">
            <CreditCard className="h-5 w-5" />
            Pembayaran Midtrans
            {paymentData?.environment === 'sandbox' && (
              <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded">
                SANDBOX
              </span>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Cart Summary */}
          <Card>
            <CardContent className="pt-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Item:</span>
                  <span>{Object.keys(socket.cart).length}</span>
                </div>
                <div className="flex justify-between text-lg font-bold text-green-600 border-t pt-2">
                  <span>Total:</span>
                  <span>Rp {socket.total.toLocaleString()}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Payment Status Content */}
          {paymentStatus === 'idle' && (
            <div className="text-center space-y-4">
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Pilih Metode Pembayaran</h3>
                <p className="text-sm text-muted-foreground">
                  Virtual Account • GoPay • QRIS • Other QRIS (semua bank & e-wallet)
                </p>
              </div>
              <Button 
                onClick={handleCreatePayment} 
                className="w-full" 
                size="lg"
                disabled={socket.total <= 0}
              >
                <CreditCard className="h-4 w-4 mr-2" />
                Bayar Sekarang
              </Button>
            </div>
          )}

          {paymentStatus === 'creating' && (
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              </div>
              <div>
                <p className="text-muted-foreground">Membuat pembayaran...</p>
                <p className="text-xs text-gray-500 mt-1">Halaman pembayaran akan terbuka otomatis</p>
              </div>
            </div>
          )}

          {paymentStatus === 'pending' && paymentData && (
            <div className="space-y-4">
              {/* Timer */}
              <div className="flex items-center justify-center gap-2 text-orange-600">
                <Clock className="h-4 w-4" />
                <span className="text-sm font-mono">
                  Sisa waktu: {formatTime(timeRemaining)}
                </span>
              </div>

              {/* Payment Info */}
              <div className="text-center space-y-4">
                <div className="flex justify-center">
                  <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                    <CreditCard className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-semibold">Halaman Pembayaran Terbuka</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Selesaikan pembayaran di halaman yang telah terbuka
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Order ID: {paymentData.order_id}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2">
                <Button 
                  onClick={handleOpenSnap} 
                  className="w-full" 
                  size="lg"
                  variant="outline"
                  disabled={snapPopupOpen}
                >
                  <CreditCard className="h-4 w-4 mr-2" />
                  {snapPopupOpen ? 'Halaman Pembayaran Aktif' : 'Buka Ulang Halaman Pembayaran'}
                </Button>
                
                <Button 
                  onClick={() => {
                    setSnapPopupOpen(false);
                    setPaymentStatus('idle');
                  }} 
                  variant="outline" 
                  className="w-full"
                  size="sm"
                >
                  Buat Pembayaran Baru
                </Button>
              </div>
            </div>
          )}

          {(paymentStatus === 'failed' || paymentStatus === 'expired') && (
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                {paymentStatus === 'expired' ? (
                  <Clock className="h-8 w-8 text-orange-600" />
                ) : (
                  <XCircle className="h-8 w-8 text-red-600" />
                )}
              </div>
              <div>
                <h3 className="font-semibold text-foreground">
                  {paymentStatus === 'expired' ? 'Waktu Pembayaran Habis' : 'Pembayaran Gagal'}
                </h3>
                {errorMessage && (
                  <p className="text-sm text-red-600 mt-1">{errorMessage}</p>
                )}
              </div>
              <Button 
                onClick={() => setPaymentStatus('idle')} 
                className="w-full"
              >
                Coba Lagi
              </Button>
            </div>
          )}

          {/* Cancel Button (always visible) */}
          <Button 
            onClick={() => onOpenChange(false)} 
            variant="outline" 
            className="w-full"
          >
            Tutup
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}