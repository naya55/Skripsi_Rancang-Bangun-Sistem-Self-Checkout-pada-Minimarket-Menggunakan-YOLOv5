'use client';

import { useEffect, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { SOCKET_URL } from '@/lib/constants';
import { Cart, Product, Transaction, SimulatedObject, AppConfig } from '@/lib/types';

export function useSocket() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [cart, setCart] = useState<Cart>({});
  const [total, setTotal] = useState(0);
  const [products, setProducts] = useState<Record<string, number>>({});
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [simulatedObjects, setSimulatedObjects] = useState<Record<string, SimulatedObject>>({});
  const [isScanning, setIsScanning] = useState(false);
  const [isSimulationMode, setIsSimulationMode] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);
  const [isClient, setIsClient] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [cameraAvailable, setCameraAvailable] = useState(false);
  const [cameraLoading, setCameraLoading] = useState(false);
  const [yoloInitialized, setYoloInitialized] = useState(false);
  const [yoloInitializing, setYoloInitializing] = useState(false);
  const [modelLabels, setModelLabels] = useState<string[]>([]);
  const [currentModel, setCurrentModel] = useState<string>('');
  const [showCameraOverlay, setShowCameraOverlay] = useState(true);
  const [cameraOverlayMessage, setCameraOverlayMessage] = useState<string>('');
  const [isModelTabActive, setIsModelTabActive] = useState(false);

  const showNotification = useCallback((message: string) => {
    setNotification(message);
    setTimeout(() => setNotification(null), 3000);
  }, []);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient) return;

    const socketInstance = io(SOCKET_URL, {
      forceNew: true,
      reconnection: true,
      timeout: 20000,
      maxReconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      transports: ['websocket', 'polling'],
      upgrade: true,
      rememberUpgrade: true,
      // Increase buffer size to handle large payloads
      transportOptions: {
        polling: {
          extraHeaders: {
            'Connection': 'keep-alive'
          }
        }
      }
    });
    
    setSocket(socketInstance);

    socketInstance.on('connect', () => {
      setIsConnected(true);
    });

    socketInstance.on('disconnect', () => {
      setIsConnected(false);
    });

    socketInstance.on('cart_update', (data) => {
      setCart(data.cart);
      setTotal(data.total);
    });

    socketInstance.on('scanning_complete', (data) => {
      setCart(data.cart);
      setTotal(data.total);
      setIsScanning(false);
    });

    socketInstance.on('products_list', (data) => {
      setProducts(data);
    });

    socketInstance.on('product_added', (data) => {
      setProducts(prev => ({ ...prev, [data.name]: data.price }));
      showNotification(`Product ${data.name} added successfully`);
    });

    socketInstance.on('product_updated', (data) => {
      setProducts(prev => ({ ...prev, [data.name]: data.price }));
      showNotification(`Product ${data.name} updated successfully`);
    });

    socketInstance.on('product_deleted', (data) => {
      setProducts(prev => {
        const newProducts = { ...prev };
        delete newProducts[data.name];
        return newProducts;
      });
      showNotification(`Product ${data.name} deleted successfully`);
    });

    socketInstance.on('transaction_history', (data) => {
      setTransactions(data);
    });

    socketInstance.on('transaction_deleted', (data) => {
      if (data.success) {
        showNotification("Transaction deleted successfully");
      }
    });

    socketInstance.on('item_removed', (data) => {
      if (data.success) {
        showNotification(`Removed ${data.name} from cart`);
      }
    });

    socketInstance.on('simulation_toggled', (data) => {
      setIsSimulationMode(data.enabled);
    });

    socketInstance.on('simulated_objects_list', (data) => {
      setSimulatedObjects(data);
    });

    socketInstance.on('simulated_object_added', (data) => {
      if (data.success) {
        setSimulatedObjects(prev => ({
          ...prev,
          [data.obj_id]: {
            label: data.label,
            x: data.x,
            y: data.y,
            width: data.width,
            height: data.height,
            created_time: Date.now()
          }
        }));
        showNotification(`Added simulated ${data.label}`);
      }
    });

    socketInstance.on('simulated_object_removed', (data) => {
      if (data.success) {
        setSimulatedObjects(prev => {
          const newObjects = { ...prev };
          delete newObjects[data.obj_id];
          return newObjects;
        });
        showNotification("Simulated object removed");
      }
    });


    socketInstance.on('config_updated', () => {
      showNotification("Configuration updated successfully");
    });

    socketInstance.on('camera_status', (data) => {
      setCameraEnabled(data.enabled);
      setCameraAvailable(data.available);
      setCameraLoading(data.loading || false);
      if (data.message) {
        showNotification(data.message);
      }
    });

    socketInstance.on('yolo_status', (data) => {
      setYoloInitialized(data.initialized);
      setYoloInitializing(data.initializing);
      if (data.error) {
        showNotification(`YOLO Error: ${data.error}`);
      } else if (data.initialized && !data.initializing) {
        showNotification("YOLO model ready for detection");
        // When YOLO is ready, fetch available labels and current model info
        socketInstance.emit('get_model_labels');
        // Also get current model info if available
        if (data.model_path) {
          const modelName = data.model_path.split('/').pop() || 'unknown';
          setCurrentModel(modelName);
        }
      }
    });

    socketInstance.on('model_labels', (data) => {
      if (data.success) {
        setModelLabels(data.labels || []);
      } else {
        console.error('Failed to load model labels:', data.error);
        setModelLabels([]);
      }
    });

    socketInstance.on('model_changed', (data) => {
      if (data.success) {
        const modelName = data.model_path?.split('/').pop() || 'unknown';
        setCurrentModel(modelName);
        showNotification(`Model changed to: ${modelName}`);
        // Clear old labels first
        setModelLabels([]);
        // Refresh labels when model changes with a longer delay to ensure model is fully loaded
        setTimeout(() => {
          socketInstance.emit('get_model_labels');
        }, 2000);
      } else {
        showNotification(`Failed to change model: ${data.error}`);
      }
    });

    socketInstance.on('config_reloaded', (data) => {
      if (data.success) {
        showNotification('Configuration reloaded from Firebase');
        // Refresh model labels after config reload
        setTimeout(() => {
          socketInstance.emit('get_model_labels');
        }, 1000);
      } else {
        showNotification(`Failed to reload config: ${data.message || data.error}`);
      }
    });


    socketInstance.on('camera_overlay', (data) => {
      setShowCameraOverlay(data.show);
      setCameraOverlayMessage(data.message || '');
      if (data.show) {
        showNotification('Kamera dimatikan');
      } else {
        showNotification('Kamera dihidupkan');
      }
    });

    // Model Tab Camera Management Events
    socketInstance.on('camera_disabled_for_config', (data) => {
      if (data.success) {
        setIsModelTabActive(true);
        showNotification('Camera disabled for model configuration');
      } else {
        showNotification(`Failed to disable camera: ${data.error}`);
      }
    });

    socketInstance.on('camera_enabled_with_index', (data) => {
      if (data.success) {
        showNotification(`Camera ${data.camera_id} enabled successfully`);
      } else {
        showNotification(`Failed to enable camera: ${data.error}`);
      }
    });

    socketInstance.on('camera_restored', (data) => {
      if (data.success) {
        setIsModelTabActive(false);
        showNotification(`Camera ${data.camera_id} restored successfully`);
      } else {
        showNotification(`Failed to restore camera: ${data.error}`);
      }
    });

    return () => {
      socketInstance.disconnect();
    };
  }, [isClient, showNotification]);

  const startScanning = useCallback((config: any) => {
    setIsScanning(true);
    socket?.emit('start_scanning', config);
  }, [socket]);

  const stopScanning = useCallback(() => {
    setIsScanning(false);
    socket?.emit('stop_scanning');
  }, [socket]);

  const removeItem = useCallback((name: string) => {
    socket?.emit('remove_item', { name });
  }, [socket]);

  const clearCart = useCallback(() => {
    socket?.emit('clear_cart');
  }, [socket]);

  const checkoutComplete = useCallback(() => {
    socket?.emit('checkout_complete');
  }, [socket]);

  const getProducts = useCallback(() => {
    socket?.emit('get_products');
  }, [socket]);

  const addProduct = useCallback((name: string, price: number) => {
    socket?.emit('add_product', { name, price });
  }, [socket]);

  const updateProduct = useCallback((name: string, price: number) => {
    socket?.emit('update_product', { name, price });
  }, [socket]);

  const deleteProduct = useCallback((name: string) => {
    socket?.emit('delete_product', { name });
  }, [socket]);

  const deleteAllProducts = useCallback(() => {
    socket?.emit('delete_all_products');
  }, [socket]);

  const getTransactionHistory = useCallback(() => {
    socket?.emit('get_transaction_history');
  }, [socket]);

  const deleteTransaction = useCallback((id: string) => {
    socket?.emit('delete_transaction', { id });
  }, [socket]);

  const deleteAllTransactions = useCallback(() => {
    socket?.emit('delete_all_transactions');
  }, [socket]);

  const toggleSimulation = useCallback((enabled: boolean) => {
    socket?.emit('toggle_simulation', { enabled });
  }, [socket]);

  const addSimulatedObject = useCallback((params: any) => {
    socket?.emit('add_simulated_object', params);
  }, [socket]);

  const removeSimulatedObject = useCallback((objId: string) => {
    socket?.emit('remove_simulated_object', { obj_id: objId });
  }, [socket]);


  const moveSimulatedObject = useCallback((objId: string, direction: string, step: number = 15) => {
    socket?.emit('move_simulated_object', { obj_id: objId, direction, step });
  }, [socket]);

  const moveToZone = useCallback((objId: string) => {
    socket?.emit('preset_move_to_zone', { obj_id: objId });
  }, [socket]);

  const updateConfig = useCallback((type: string, config: any) => {
    socket?.emit(`update_${type}_config`, config);
  }, [socket]);

  const applyPreset = useCallback((preset: string) => {
    socket?.emit('apply_preset_config', preset);
  }, [socket]);

  const toggleCamera = useCallback((enabled: boolean) => {
    socket?.emit('toggle_camera', { enabled });
  }, [socket]);

  const initializeYolo = useCallback(() => {
    socket?.emit('initialize_yolo');
  }, [socket]);

  const getModelLabels = useCallback(() => {
    socket?.emit('get_model_labels');
  }, [socket]);

  const reloadConfig = useCallback(() => {
    socket?.emit('reload_config');
  }, [socket]);


  const toggleCameraOverlay = useCallback((show: boolean) => {
    toggleCamera(!show);
  }, [toggleCamera]);

  // Model Tab Camera Management Functions
  const disableCameraForModelConfig = useCallback(() => {
    socket?.emit('disable_camera_for_model_config');
  }, [socket]);

  const enableCameraWithIndex = useCallback((cameraId: number) => {
    socket?.emit('enable_camera_with_index', { camera_id: cameraId });
  }, [socket]);

  const restoreCamera = useCallback((cameraId: number) => {
    socket?.emit('restore_camera', { camera_id: cameraId });
  }, [socket]);

  return {
    socket,
    isConnected: isClient ? isConnected : false,
    cart,
    total,
    products,
    transactions,
    simulatedObjects,
    isScanning,
    isSimulationMode,
    notification,
    cameraEnabled,
    cameraAvailable,
    cameraLoading,
    yoloInitialized,
    yoloInitializing,
    modelLabels,
    currentModel,
    showCameraOverlay,
    cameraOverlayMessage,
    isModelTabActive,
    startScanning,
    stopScanning,
    removeItem,
    clearCart,
    checkoutComplete,
    getProducts,
    addProduct,
    updateProduct,
    deleteProduct,
    deleteAllProducts,
    getTransactionHistory,
    deleteTransaction,
    deleteAllTransactions,
    toggleSimulation,
    addSimulatedObject,
    removeSimulatedObject,
    moveSimulatedObject,
    moveToZone,
    updateConfig,
    applyPreset,
    showNotification,
    toggleCamera,
    initializeYolo,
    getModelLabels,
    reloadConfig,
    toggleCameraOverlay,
    disableCameraForModelConfig,
    enableCameraWithIndex,
    restoreCamera,
    setCameraEnabled
  };
}