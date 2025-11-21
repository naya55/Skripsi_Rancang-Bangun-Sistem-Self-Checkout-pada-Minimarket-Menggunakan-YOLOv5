'use client';

import { useState } from 'react';
import { useSocket } from '@/hooks/useSocket';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ShoppingCart, Trash2, CreditCard, Package } from 'lucide-react';
import CheckoutModal from '@/components/checkout/CheckoutModal';

export default function CartSidebar() {
  const socket = useSocket();
  const [showCheckout, setShowCheckout] = useState(false);

  const cartItems = Object.entries(socket.cart);
  const isEmpty = cartItems.length === 0;

  const handleRemoveItem = (productName: string) => {
    socket.removeItem(productName);
  };

  const handleCheckout = () => {
    setShowCheckout(true);
  };

  const handleClearCart = () => {
    socket.clearCart();
  };

  return (
    <>
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShoppingCart className="h-5 w-5" />
              Keranjang Belanja
            </div>
            <Badge variant="outline">{cartItems.length} item</Badge>
          </CardTitle>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {isEmpty ? (
            <div className="text-center py-8">
              <Package className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-muted-foreground">Keranjang Anda kosong</p>
              <p className="text-sm text-muted-foreground/70">Mulai pemindaian untuk menambah item</p>
            </div>
          ) : (
            <>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {cartItems.map(([productName, details]) => {
                  const subtotal = details.price * details.quantity;
                  return (
                    <div key={productName} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                      <div className="flex-1">
                        <p className="font-medium capitalize">{productName}</p>
                        <p className="text-sm text-muted-foreground">
                          Rp {details.price.toLocaleString()} × {details.quantity}
                        </p>
                        <p className="text-sm font-medium text-primary">
                          Rp {subtotal.toLocaleString()}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRemoveItem(productName)}
                        className="text-red-500 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  );
                })}
              </div>

              <Separator />

              <div className="space-y-3">
                <div className="flex justify-between items-center text-lg font-bold">
                  <span>Total:</span>
                  <span className="text-primary">Rp {socket.total.toLocaleString()}</span>
                </div>

                <Button
                  onClick={handleCheckout}
                  disabled={isEmpty || socket.total <= 0}
                  className="w-full"
                  size="lg"
                >
                  <CreditCard className="h-4 w-4 mr-2" />
                  Checkout
                </Button>

                <Button
                  onClick={handleClearCart}
                  variant="outline"
                  className="w-full"
                  disabled={isEmpty}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Kosongkan Keranjang
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <CheckoutModal 
        open={showCheckout} 
        onOpenChange={setShowCheckout}
      />
    </>
  );
}