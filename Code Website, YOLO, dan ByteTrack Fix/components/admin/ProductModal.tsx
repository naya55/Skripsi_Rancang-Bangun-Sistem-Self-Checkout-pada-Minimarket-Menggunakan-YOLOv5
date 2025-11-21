'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSocket } from '@/hooks/useSocket';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import DraggableWindow from '@/components/ui/draggable-window';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Package, Plus, Edit2, Trash2, AlertTriangle, Tag, RefreshCw } from 'lucide-react';
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

export default function ProductModal() {
  const socket = useSocket();
  const [open, setOpen] = useState(false);
  
  const [newProduct, setNewProduct] = useState({ name: '', price: '' });
  const [editProduct, setEditProduct] = useState<{ name: string; price: string } | null>(null);
  const [showDeleteAllDialog, setShowDeleteAllDialog] = useState(false);
  const [showDeleteSingleDialog, setShowDeleteSingleDialog] = useState<{ name: string; price: number } | null>(null);
  const [isLoadingLabels, setIsLoadingLabels] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDeletingAll, setIsDeletingAll] = useState(false);

  const getProducts = useCallback(() => {
    if (socket?.getProducts) {
      socket.getProducts();
    }
  }, [socket]);

  useEffect(() => {
    if (open) {
      // Add delay to prevent rapid calls
      const timer = setTimeout(() => {
        getProducts();
        // Fetch model labels if YOLO is initialized
        if (socket.yoloInitialized && socket.getModelLabels) {
          setIsLoadingLabels(true);
          socket.getModelLabels();
          // Labels will be available via socket.modelLabels
          setTimeout(() => setIsLoadingLabels(false), 1000);
        }
      }, 100);
      
      return () => clearTimeout(timer);
    }
  }, [open, getProducts, socket]);

  const handleAddProduct = () => {
    if (newProduct.name && newProduct.price) {
      socket.addProduct(newProduct.name, parseInt(newProduct.price));
      setNewProduct({ name: '', price: '' });
    }
  };

  const handleUpdateProduct = () => {
    if (editProduct?.name && editProduct.price) {
      socket.updateProduct(editProduct.name, parseInt(editProduct.price));
      setEditProduct(null);
    }
  };

  const handleDeleteProduct = async (name: string, price: number) => {
    setShowDeleteSingleDialog({ name, price });
  };

  const confirmDeleteProduct = async () => {
    if (!showDeleteSingleDialog) return;
    
    setIsDeleting(true);
    try {
      socket.deleteProduct(showDeleteSingleDialog.name);
      // Wait a bit for the operation to complete
      await new Promise(resolve => setTimeout(resolve, 1000));
    } finally {
      setIsDeleting(false);
      setShowDeleteSingleDialog(null);
    }
  };

  const handleDeleteAllProducts = async () => {
    setIsDeletingAll(true);
    try {
      socket.deleteAllProducts();
      // Wait a bit for the operation to complete
      await new Promise(resolve => setTimeout(resolve, 1500));
    } finally {
      setIsDeletingAll(false);
      setShowDeleteAllDialog(false);
    }
  };

  const productEntries = Object.entries(socket.products);

  return (
    <>
      <Button 
        variant="outline" 
        className="flex items-center gap-2"
        onClick={() => setOpen(true)}
      >
        <Package className="h-4 w-4" />
        Produk
      </Button>
      
      <DraggableWindow
        title="Manajemen Produk"
        icon={<Package className="h-5 w-5" />}
        isOpen={open}
        onClose={() => setOpen(false)}
        defaultPosition={{ x: 100, y: 100 }}
        defaultSize={{ width: '800px', height: '600px' }}
        minWidth="500px"
        minHeight="400px"
      >

        <Tabs defaultValue="list" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="list">Daftar Produk</TabsTrigger>
            <TabsTrigger value="add">Tambah Produk</TabsTrigger>
          </TabsList>

          <TabsContent value="list" className="space-y-4">
            <div className="flex justify-between items-center mb-4">
              <div>
                <Badge variant="secondary">{productEntries.length} produk</Badge>
              </div>
              {productEntries.length > 0 && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setShowDeleteAllDialog(true)}
                  className="flex items-center gap-2"
                  disabled={isDeletingAll}
                >
                  {isDeletingAll ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <AlertTriangle className="h-4 w-4" />
                  )}
                  {isDeletingAll ? 'Menghapus...' : 'Hapus Semua Produk'}
                </Button>
              )}
            </div>

            {editProduct && (
              <Card className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/20">
                <CardHeader>
                  <CardTitle className="text-sm">Edit Produk</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Nama Produk</Label>
                      <Input
                        value={editProduct.name}
                        disabled
                        className="bg-gray-100 dark:bg-gray-800"
                      />
                    </div>
                    <div>
                      <Label>Harga (Rp)</Label>
                      <Input
                        type="number"
                        value={editProduct.price}
                        onChange={(e) => setEditProduct({ ...editProduct, price: e.target.value })}
                        placeholder="Masukkan harga baru"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleUpdateProduct} size="sm">
                      Simpan Perubahan
                    </Button>
                    <Button 
                      onClick={() => setEditProduct(null)} 
                      variant="outline" 
                      size="sm"
                    >
                      Batal
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="grid gap-3">
              {productEntries.length === 0 ? (
                <Card>
                  <CardContent className="text-center py-8">
                    <Package className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-500 dark:text-gray-400">Tidak ada produk ditemukan</p>
                    <p className="text-sm text-gray-400 dark:text-gray-500">Tambahkan produk pertama untuk memulai</p>
                  </CardContent>
                </Card>
              ) : (
                productEntries.map(([name, price]) => (
                  <Card key={name}>
                    <CardContent className="flex items-center justify-between p-4">
                      <div>
                        <h3 className="font-medium capitalize">{name}</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-300">Rp {price.toLocaleString()}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{price}</Badge>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setEditProduct({ name, price: price.toString() })}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteProduct(name, price)}
                          className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                          disabled={isDeleting}
                        >
                          {isDeleting ? (
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-red-500 border-t-transparent" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          <TabsContent value="add" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Plus className="h-4 w-4" />
                  Tambah Produk Baru
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Show model info and status */}
                <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-950/20 rounded-md border border-blue-200 dark:border-blue-800">
                  <div className="flex items-center gap-2">
                    <Tag className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                        Model Labels
                      </span>
                      {socket.currentModel && (
                        <span className="text-xs text-blue-600 dark:text-blue-400 font-mono">
                          {socket.currentModel}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {!socket.yoloInitialized ? (
                      <Badge variant="destructive">YOLO Not Initialized</Badge>
                    ) : isLoadingLabels ? (
                      <Badge variant="secondary">Loading...</Badge>
                    ) : socket.modelLabels.length > 0 ? (
                      <Badge variant="secondary">{socket.modelLabels.length} classes available</Badge>
                    ) : (
                      <Badge variant="outline">No labels found</Badge>
                    )}
                    {socket.yoloInitialized && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setIsLoadingLabels(true);
                          // Reload backend config first to ensure model is synced
                          if (socket.reloadConfig) {
                            socket.reloadConfig();
                          }
                          // Then get fresh model labels
                          socket.getModelLabels?.();
                          setTimeout(() => setIsLoadingLabels(false), 3000);
                        }}
                        className="text-xs flex items-center gap-1"
                        disabled={isLoadingLabels}
                      >
                        <RefreshCw className={`h-3 w-3 ${isLoadingLabels ? 'animate-spin' : ''}`} />
                        {isLoadingLabels ? 'Memuat...' : 'Muat Ulang'}
                      </Button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Product Name</Label>
                    {!socket.yoloInitialized ? (
                      <div className="space-y-2">
                        <Input
                          value={newProduct.name}
                          onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                          placeholder="Initialize YOLO first"
                          disabled
                        />
                        <p className="text-xs text-amber-600 dark:text-amber-400">
                          ⚠️ Please initialize YOLO model first to see available product classes
                        </p>
                      </div>
                    ) : socket.modelLabels.length === 0 ? (
                      <div className="space-y-2">
                        <Input
                          value={newProduct.name}
                          onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                          placeholder="No model labels available"
                          disabled
                        />
                        <p className="text-xs text-red-600 dark:text-red-400">
                          ❌ No model labels found. Check if model is loaded correctly.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <Select value={newProduct.name} onValueChange={(value) => setNewProduct({ ...newProduct, name: value })}>
                          <SelectTrigger>
                            <SelectValue placeholder="Pilih produk dari model YOLO" />
                          </SelectTrigger>
                          <SelectContent>
                            {socket.modelLabels.map((label, index) => (
                              <SelectItem key={index} value={label}>
                                <div className="flex items-center gap-2">
                                  <Badge variant="outline" className="text-xs">
                                    {index}
                                  </Badge>
                                  <span className="capitalize">{label}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <p className="text-xs text-green-600 dark:text-green-400">
                          ✅ Pilih produk yang sesuai dengan label di model YOLO
                        </p>
                      </div>
                    )}
                  </div>
                  <div>
                    <Label>Price (Rp)</Label>
                    <Input
                      type="number"
                      value={newProduct.price}
                      onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })}
                      placeholder="Masukkan harga"
                    />
                  </div>
                </div>
                <Button 
                  onClick={handleAddProduct}
                  className="w-full"
                  disabled={!newProduct.name || !newProduct.price}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Tambah Produk
                </Button>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </DraggableWindow>

      {/* Single Product Delete Confirmation */}
      <AlertDialog open={!!showDeleteSingleDialog} onOpenChange={(open) => !open && setShowDeleteSingleDialog(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-red-600 dark:text-red-400" />
              Hapus Produk
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3">
                <p>Apakah Anda yakin ingin menghapus produk ini?</p>
                {showDeleteSingleDialog && (
                  <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-3">
                      <Package className="h-8 w-8 text-gray-400 dark:text-gray-500" />
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-gray-100 capitalize">
                          {showDeleteSingleDialog.name}
                        </h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Rp {showDeleteSingleDialog.price.toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
                <div className="bg-amber-50 dark:bg-amber-950/20 p-3 rounded-md border border-amber-200 dark:border-amber-800">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                    <span className="text-sm font-medium text-amber-800 dark:text-amber-200">
                      Produk akan dihapus secara permanen
                    </span>
                  </div>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Batal</AlertDialogCancel>
            <AlertDialogAction 
              onClick={confirmDeleteProduct}
              disabled={isDeleting}
              className="bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800 disabled:opacity-50"
            >
              {isDeleting ? (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Menghapus...
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Trash2 className="h-4 w-4" />
                  Hapus Produk
                </div>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete All Products Confirmation */}
      <AlertDialog open={showDeleteAllDialog} onOpenChange={(open) => !isDeletingAll && setShowDeleteAllDialog(open)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
              Hapus Semua Produk
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3">
                <p>Apakah Anda yakin ingin menghapus semua <strong>{productEntries.length} produk</strong>?</p>
                
                {/* Preview affected products */}
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-700 max-h-32 overflow-y-auto">
                  <div className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">Produk yang akan dihapus:</div>
                  <div className="space-y-1">
                    {productEntries.slice(0, 5).map(([name, price]) => (
                      <div key={name} className="flex justify-between text-sm">
                        <span className="capitalize text-gray-700 dark:text-gray-300">{name}</span>
                        <span className="text-gray-500 dark:text-gray-400">Rp {price.toLocaleString()}</span>
                      </div>
                    ))}
                    {productEntries.length > 5 && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 italic">
                        +{productEntries.length - 5} produk lainnya...
                      </div>
                    )}
                  </div>
                </div>

                <div className="bg-red-50 dark:bg-red-950/20 p-3 rounded-md border border-red-200 dark:border-red-800">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5" />
                    <div>
                      <div className="text-sm font-medium text-red-600 dark:text-red-400">Tindakan ini tidak dapat dibatalkan!</div>
                      <div className="text-sm text-red-500 dark:text-red-400 mt-1">Semua data produk akan dihapus secara permanen dari sistem.</div>
                    </div>
                  </div>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeletingAll}>Batal</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteAllProducts}
              disabled={isDeletingAll}
              className="bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800 disabled:opacity-50"
            >
              {isDeletingAll ? (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Menghapus Semua...
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Trash2 className="h-4 w-4" />
                  Hapus Semua ({productEntries.length})
                </div>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}