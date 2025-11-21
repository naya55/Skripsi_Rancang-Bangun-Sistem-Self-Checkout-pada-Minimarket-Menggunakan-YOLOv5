'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSocket } from '@/hooks/useSocket';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import DraggableWindow from '@/components/ui/draggable-window';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { History, Trash2, Calendar, DollarSign, ShoppingBag, AlertTriangle, Trash } from 'lucide-react';
import { Transaction } from '@/lib/types';

export default function HistoryModal() {
  const socket = useSocket();
  const [open, setOpen] = useState(false);
  
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [transactionToDelete, setTransactionToDelete] = useState<Transaction | null>(null);
  const [deleteAllDialogOpen, setDeleteAllDialogOpen] = useState(false);
  const [dateRange, setDateRange] = useState({
    start: '',
    end: ''
  });

  const getTransactionHistory = useCallback(() => {
    if (socket?.getTransactionHistory) {
      socket.getTransactionHistory();
    }
  }, [socket]);

  const setDefaultDates = useCallback(() => {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    const formatDate = (date: Date) => {
      return date.toISOString().split('T')[0];
    };
    
    setDateRange({
      start: formatDate(thirtyDaysAgo),
      end: formatDate(today)
    });
  }, []);

  useEffect(() => {
    if (open) {
      // Only call once when modal opens, with a slight delay to prevent rapid calls
      const timer = setTimeout(() => {
        getTransactionHistory();
        setDefaultDates();
      }, 100);
      
      return () => clearTimeout(timer);
    }
  }, [open, getTransactionHistory, setDefaultDates, socket]);

  const handleDateFilter = () => {
    if (dateRange.start && dateRange.end) {
      // Emit filter by date range
    } else {
      getTransactionHistory();
    }
  };

  const handleDeleteClick = (transaction: Transaction) => {
    setTransactionToDelete(transaction);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = () => {
    if (transactionToDelete) {
      socket.deleteTransaction(transactionToDelete.id);
      setSelectedTransaction(null);
      setTransactionToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  const handleCancelDelete = () => {
    setTransactionToDelete(null);
    setDeleteDialogOpen(false);
  };

  const handleDeleteAllHistory = () => {
    socket.deleteAllTransactions();
    setDeleteAllDialogOpen(false);
  };

  const totalRevenue = socket.transactions.reduce((sum, t) => sum + t.total, 0);

  return (
    <>
      <Button 
        variant="outline" 
        className="flex items-center gap-2"
        onClick={() => setOpen(true)}
      >
        <History className="h-4 w-4" />
        Riwayat
      </Button>
      
      <DraggableWindow
        title="Riwayat Transaksi"
        icon={<History className="h-5 w-5" />}
        isOpen={open}
        onClose={() => setOpen(false)}
        defaultPosition={{ x: 100, y: 100 }}
        defaultSize={{ width: '900px', height: '700px' }}
        minWidth="600px"
        minHeight="400px"
      >

        <div className="space-y-6">
          <Card>
            <CardContent className="pt-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <Label>Tanggal Mulai</Label>
                  <Input
                    type="date"
                    value={dateRange.start}
                    onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>Tanggal Akhir</Label>
                  <Input
                    type="date"
                    value={dateRange.end}
                    onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                  />
                </div>
                <div className="flex items-end">
                  <Button onClick={handleDateFilter} className="w-full">
                    Filter
                  </Button>
                </div>
                <div className="flex items-end">
                  <Button 
                    onClick={() => getTransactionHistory()} 
                    variant="outline" 
                    className="w-full"
                  >
                    Reset
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-4 text-center">
                <ShoppingBag className="h-8 w-8 text-blue-500 dark:text-blue-400 mx-auto mb-2" />
                <div className="text-2xl font-bold">{socket.transactions.length}</div>
                <div className="text-sm text-muted-foreground">Total Transaksi</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 text-center">
                <DollarSign className="h-8 w-8 text-green-500 dark:text-green-400 mx-auto mb-2" />
                <div className="text-2xl font-bold">Rp {totalRevenue.toLocaleString()}</div>
                <div className="text-sm text-muted-foreground">Total Pendapatan</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 text-center">
                <Calendar className="h-8 w-8 text-purple-500 dark:text-purple-400 mx-auto mb-2" />
                <div className="text-2xl font-bold">
                  Rp {socket.transactions.length > 0 ? Math.round(totalRevenue / socket.transactions.length).toLocaleString() : 0}
                </div>
                <div className="text-sm text-muted-foreground">Avg. Transaction</div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm">Transaksi Terbaru</CardTitle>
                {socket.transactions.length > 0 && (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setDeleteAllDialogOpen(true)}
                    className="flex items-center gap-2"
                  >
                    <Trash className="h-4 w-4" />
                    Hapus Semua
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {socket.transactions.length === 0 ? (
                    <div className="text-center py-8">
                      <History className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
                      <p className="text-muted-foreground">Tidak ada transaksi ditemukan</p>
                    </div>
                  ) : (
                    socket.transactions.map((transaction) => (
                      <div
                        key={transaction.id}
                        className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted cursor-pointer transition-colors"
                        onClick={() => setSelectedTransaction(transaction)}
                      >
                        <div>
                          <p className="font-medium">
                            {transaction.formatted_date || 'N/A'}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {transaction.items?.length || 0} item
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium text-green-600 dark:text-green-400">
                            Rp {transaction.total.toLocaleString()}
                          </p>
                          <Badge variant="outline" className="text-xs">
                            View Details
                          </Badge>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {selectedTransaction && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center justify-between">
                    Transaction Details
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteClick(selectedTransaction)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Transaction ID</p>
                    <p className="font-mono text-xs">{selectedTransaction.id}</p>
                  </div>
                  
                  <div>
                    <p className="text-sm text-muted-foreground">Date & Time</p>
                    <p className="font-medium">{selectedTransaction.formatted_date || 'N/A'}</p>
                  </div>

                  <Separator />

                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Items Purchased</p>
                    <div className="space-y-2">
                      {selectedTransaction.items?.map((item, index) => (
                        <div key={index} className="flex justify-between text-sm">
                          <span className="capitalize">{item.name} × {item.quantity}</span>
                          <span>Rp {item.subtotal.toLocaleString()}</span>
                        </div>
                      )) || (
                        <p className="text-muted-foreground text-sm">No items recorded</p>
                      )}
                    </div>
                  </div>

                  <Separator />

                  <div className="flex justify-between items-center text-lg font-bold">
                    <span>Total:</span>
                    <span className="text-green-600 dark:text-green-400">
                      Rp {selectedTransaction.total.toLocaleString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </DraggableWindow>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500 dark:text-red-400" />
              Hapus Transaksi
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2">
                <span>Apakah Anda yakin ingin menghapus transaksi ini?</span>
                {transactionToDelete && (
                  <div className="bg-muted p-3 rounded-md mt-3">
                    <div className="text-sm font-medium">Detail Transaksi:</div>
                    <div className="text-sm text-muted-foreground mt-1">
                      Tanggal: {transactionToDelete.formatted_date || 'N/A'}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Total: Rp {transactionToDelete.total.toLocaleString()}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Item: {transactionToDelete.items?.length || 0}
                    </div>
                  </div>
                )}
                <div className="text-sm text-red-600 dark:text-red-400 font-medium mt-3">
                  Tindakan ini tidak dapat dibatalkan.
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancelDelete}>
              Batal
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-red-500 hover:bg-red-600 text-white"
            >
              Hapus Transaksi
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={deleteAllDialogOpen} onOpenChange={setDeleteAllDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Hapus Semua Riwayat Transaksi</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2">
                <span>Apakah Anda yakin ingin menghapus semua {socket.transactions.length} transaksi?</span>
                <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 p-3 rounded-md mt-3">
                  <div className="text-sm font-medium text-red-600 dark:text-red-400">Tindakan ini tidak dapat dibatalkan!</div>
                  <div className="text-sm text-red-500 dark:text-red-400 mt-1">Semua riwayat transaksi akan dihapus secara permanen.</div>
                  <div className="text-sm text-red-500 dark:text-red-400">Total pendapatan yang akan dihapus: Rp {totalRevenue.toLocaleString()}</div>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Batal</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteAllHistory}
              className="bg-red-600 hover:bg-red-700"
            >
              Hapus Semua Riwayat
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}