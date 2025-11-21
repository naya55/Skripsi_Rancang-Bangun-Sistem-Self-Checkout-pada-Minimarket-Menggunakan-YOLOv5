'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSocket } from '@/hooks/useSocket';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import DraggableWindow from '@/components/ui/draggable-window';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Settings, Target, Eye, Gamepad2, Save, RotateCcw, Cpu, RefreshCw, Camera } from 'lucide-react';
import { DEFAULT_CONFIG } from '@/lib/constants';
import { AppConfig } from '@/lib/types';
import { useSettings } from '@/contexts/SettingsContext';

interface ConfigWindowProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export default function ConfigWindow({ isOpen, onClose }: ConfigWindowProps = {}) {
  const socket = useSocket();
  const { config, saveConfig, isLoading, loadConfig, hasConfig } = useSettings();
  const [internalOpen, setInternalOpen] = useState(false);
  const [pendingConfig, setPendingConfig] = useState<AppConfig>(DEFAULT_CONFIG);
  const [hasChanges, setHasChanges] = useState(false);
  const [availableModels, setAvailableModels] = useState<unknown[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [isReloading, setIsReloading] = useState(false);
  const [availableCameras, setAvailableCameras] = useState<unknown[]>([]);
  const [isLoadingCameras, setIsLoadingCameras] = useState(false);
  const [isSwitchingCamera, setIsSwitchingCamera] = useState(false);
  const [isInitializingCamera, setIsInitializingCamera] = useState(false);
  const [isRestoringCamera, setIsRestoringCamera] = useState(false);
  const [isClosingModal, setIsClosingModal] = useState(false);
  const [pendingTabChange, setPendingTabChange] = useState<string | null>(null);
  const [initializationTimeout, setInitializationTimeout] = useState<NodeJS.Timeout | null>(null);
  
  // SIMPLIFIED: No complex model tab state needed
  const [previousCameraId, setPreviousCameraId] = useState<number>(0);
  const [selectedCameraId, setSelectedCameraId] = useState<number>(0);
  const [activeTab, setActiveTab] = useState('detection');

  // Use external props if provided, otherwise use internal state
  const open = isOpen !== undefined ? isOpen : internalOpen;
  const handleClose = onClose || (() => setInternalOpen(false));

  const loadAvailableModels = useCallback(async () => {
    setIsLoadingModels(true);
    
    // Try multiple URLs to debug routing
    const urls = [
      '/api/models',
      'http://127.0.0.1:5002/api/models',
      'http://localhost:5002/api/models'
    ];
    
    for (const url of urls) {
      try {
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          
          setIsLoadingModels(false);
          if (data.success) {
            setAvailableModels(data.models);
            return; // Success, exit function
          }
        }
      } catch (error) {
        console.error(`Error with ${url}:`, error);
      }
    }
    
    // Use socket for model loading
    if (socket.socket && socket.socket.connected) {
      socket.socket.emit('get_available_models');
      // Keep loading state for socket response
    } else {
      setIsLoadingModels(false);
      setAvailableModels([]);
      console.error('All methods failed');
    }
  }, [socket.socket]);

  const loadAvailableCameras = useCallback(async () => {
    setIsLoadingCameras(true);
    
    if (socket.socket && socket.socket.connected) {
      socket.socket.emit('get_available_cameras');
    } else {
      setIsLoadingCameras(false);
      setAvailableCameras([]);
      console.error('Socket not connected for camera detection');
    }
  }, [socket.socket]);

  // Load models and cameras
  const loadModelsAndCameras = useCallback(() => {
    loadAvailableModels();
    loadAvailableCameras();
  }, [loadAvailableModels, loadAvailableCameras]);

  // SIMPLIFIED CAMERA CONTROL: Kill camera when opening configuration
  useEffect(() => {
    if (open && config) {
      // Store current camera ID before killing camera
      const currentCameraId = config.advanced?.cameraId || 0;
      setPreviousCameraId(currentCameraId);
      setSelectedCameraId(currentCameraId);
      
      // KILL CAMERA IMMEDIATELY - no matter what state
      console.log('🔴 Configuration opened - KILLING CAMERA');
      if (socket.socket) {
        socket.socket.emit('kill_camera_for_config');
      }
      
      setPendingConfig(config);
      setHasChanges(false);
      
      // Load available models and cameras when window opens
      loadModelsAndCameras();
    } else if (open && !config) {
      // Store default camera ID
      setPreviousCameraId(0);
      setSelectedCameraId(0);
      
      // KILL CAMERA IMMEDIATELY - no matter what state
      console.log('🔴 Configuration opened - KILLING CAMERA');
      if (socket.socket) {
        socket.socket.emit('kill_camera_for_config');
      }
      
      setPendingConfig(DEFAULT_CONFIG);
      setHasChanges(false);
    }
  }, [open, config, loadModelsAndCameras]);

  // Socket event handlers for models
  useEffect(() => {
    if (!socket.socket) {
      return;
    }

    const handleAvailableModels = (data: { success: boolean; models?: unknown[]; error?: string }) => {
      setIsLoadingModels(false);
      if (data.success && data.models) {
        setAvailableModels(data.models);
      } else {
        console.error('Failed to load models:', data.error);
        setAvailableModels([]);
      }
    };

    const handleModelChanged = (data: { success: boolean; model_path?: string; error?: string }) => {
      if (data.success && data.model_path) {
        const modelName = data.model_path.split('/').pop() || data.model_path;
        socket.showNotification(`Model berhasil diubah ke: ${modelName}`);
        
        // Update config to reflect model change
        const newPendingConfig = {
          ...pendingConfig,
          advanced: { ...pendingConfig.advanced, model: data.model_path }
        };
        setPendingConfig(newPendingConfig);
        setHasChanges(true);
      } else {
        console.error('Failed to change model:', data.error);
        socket.showNotification(`Gagal mengubah model: ${data.error}`);
      }
    };

    const handleCameraSwitched = (data: { success: boolean; camera_id?: number; error?: string }) => {
      setIsSwitchingCamera(false);
      if (data.success) {
        socket.showNotification(`Kamera berhasil diubah ke Camera ${data.camera_id}`);
        
        // Update config to reflect camera change
        const newPendingConfig = {
          ...pendingConfig,
          advanced: { ...pendingConfig.advanced, cameraId: data.camera_id }
        };
        setPendingConfig(newPendingConfig);
        setHasChanges(true);
      } else {
        console.error('Failed to switch camera:', data.error);
        socket.showNotification(`Gagal mengubah kamera: ${data.error}`);
      }
    };

    const handleAvailableCameras = (data: { success: boolean; cameras?: unknown[]; error?: string }) => {
      setIsLoadingCameras(false);
      if (data.success) {
        setAvailableCameras(data.cameras);
      } else {
        console.error('Failed to load cameras:', data.error);
        setAvailableCameras([]);
      }
    };

    const handleCameraInitialized = (data: { success: boolean; camera_id?: number; error?: string }) => {
      const wasClosing = isClosingModal;
      const wasRestoring = isRestoringCamera;
      const targetTab = pendingTabChange;
      
      console.log(`🔔 Received camera_initialized event:`, {
        success: data.success,
        camera_id: data.camera_id,
        error: data.error,
        wasClosing,
        wasRestoring,
        targetTab
      });
      
      // Clear timeout if exists
      if (initializationTimeout) {
        clearTimeout(initializationTimeout);
        setInitializationTimeout(null);
      }
      
      // Clear all loading states
      setIsInitializingCamera(false);
      setIsRestoringCamera(false);
      setIsClosingModal(false);
      setPendingTabChange(null);
      
      if (data.success) {
        console.log(`✅ Camera ${data.camera_id} initialized successfully`);
        
        if (wasClosing) {
          // This was a save operation - disable camera in UI and close modal
          console.log(`🔄 Completing save operation - disabling camera and closing modal`);
          socket.showNotification(`Camera ${data.camera_id} berhasil diinisialisasi - silakan nyalakan kamera secara manual`);
          
          // Safely disable camera in main UI
          try {
            if (socket.setCameraEnabled) {
              socket.setCameraEnabled(false);
            } else {
              console.warn('setCameraEnabled function not available on socket');
            }
          } catch (error) {
            console.error('Error setting camera enabled state:', error);
          }
          
          handleClose();
        } else if (wasRestoring) {
          if (targetTab) {
            // This was a tab change restoration - change to target tab
            console.log(`🔄 Completing tab change restoration - switching to ${targetTab}`);
            socket.showNotification(`Camera ${data.camera_id} berhasil dikembalikan`);
            setActiveTab(targetTab);
          } else {
            // This was a modal close restoration - close modal
            console.log(`🔄 Completing modal close restoration`);
            socket.showNotification(`Camera ${data.camera_id} berhasil dikembalikan`);
            handleClose();
          }
        } else {
          // Normal initialization
          console.log(`🔄 Normal camera initialization completed`);
          socket.showNotification(`Camera ${data.camera_id} berhasil diinisialisasi`);
        }
      } else {
        console.error('❌ Failed to initialize camera:', data.error);
        socket.showNotification(`Gagal menginisialisasi kamera: ${data.error}`);
        
        // On error, still complete the operation
        if (wasClosing) {
          console.log(`🔄 Error during save - still closing modal`);
          handleClose();
        } else if (wasRestoring && targetTab) {
          console.log(`🔄 Error during tab change restoration - still switching to ${targetTab}`);
          setActiveTab(targetTab);
        } else if (wasRestoring) {
          console.log(`🔄 Error during modal close restoration - still closing`);
          handleClose();
        }
      }
    };

    // Test event handler
    const handleTestEvent = (data: unknown) => {
      // Test event received
    };

    socket.socket.on('available_models', handleAvailableModels);
    socket.socket.on('model_changed', handleModelChanged);
    socket.socket.on('camera_switched', handleCameraSwitched);
    socket.socket.on('available_cameras', handleAvailableCameras);
    socket.socket.on('camera_initialized', handleCameraInitialized);
    socket.socket.on('test_event', handleTestEvent);
    
    // Test if events work
    setTimeout(() => {
      socket.socket?.emit('test_event', { message: 'Frontend test' });
    }, 1000);

    return () => {
      socket.socket?.off('available_models', handleAvailableModels);
      socket.socket?.off('model_changed', handleModelChanged);
      socket.socket?.off('camera_switched', handleCameraSwitched);
      socket.socket?.off('available_cameras', handleAvailableCameras);
      socket.socket?.off('camera_initialized', handleCameraInitialized);
      socket.socket?.off('test_event', handleTestEvent);
      
      // Clean up timeout on unmount
      if (initializationTimeout) {
        clearTimeout(initializationTimeout);
      }
    };
  }, [socket, pendingConfig]);


  const updateDetectionConfig = (updates: Partial<typeof config.detection>) => {
    const newPendingConfig = { 
      ...pendingConfig, 
      detection: { ...pendingConfig.detection, ...updates } 
    };
    setPendingConfig(newPendingConfig);
    setHasChanges(true);
  };

  const updateVisualConfig = (updates: Partial<typeof config.visual>) => {
    const newPendingConfig = { 
      ...pendingConfig, 
      visual: { ...pendingConfig.visual, ...updates } 
    };
    setPendingConfig(newPendingConfig);
    setHasChanges(true);
  };

  const updateSimulationConfig = (updates: Partial<typeof config.simulation>) => {
    const newPendingConfig = { 
      ...pendingConfig, 
      simulation: { ...pendingConfig.simulation, ...updates } 
    };
    setPendingConfig(newPendingConfig);
    setHasChanges(true);
  };


  const handleModelChange = (modelPath: string) => {
    if (socket.socket) {
      socket.socket.emit('change_model', { model_path: modelPath });
    }
  };


  const handleCameraChange = (cameraId: string) => {
    const newCameraId = parseInt(cameraId);
    if (socket.socket && !isSwitchingCamera) {
      setIsSwitchingCamera(true);
      socket.socket.emit('switch_camera', { camera_id: newCameraId });
    }
  };

  const handleRefreshCameras = () => {
    setAvailableCameras([]);
    loadAvailableCameras();
  };


  const handleSaveSettings = async () => {
    try {
      console.log(`🔄 Starting save process with camera ${selectedCameraId}`);
      setIsClosingModal(true); // Start loading for modal closing
      setIsInitializingCamera(true); // Start camera initialization loading
      
      // Apply simulation config to actual socket state immediately
      socket.toggleSimulation(pendingConfig.simulation.enabled);
      
      // Update the config with selected camera
      const configWithSelectedCamera = {
        ...pendingConfig,
        advanced: {
          ...pendingConfig.advanced,
          cameraId: selectedCameraId
        }
      };
      
      console.log(`💾 Saving config to Firestore...`);
      // Save all settings to Firestore using context
      const success = await saveConfig(configWithSelectedCamera);
      
      if (success) {
        setHasChanges(false);
        socket.showNotification("Pengaturan berhasil disimpan");
        
        // Initialize camera in background (akan disable camera di UI setelah selesai)
        console.log(`🟢 Initializing camera ${selectedCameraId} in background after save - waiting for response...`);
        
        if (socket.socket) {
          socket.socket.emit('initialize_camera', { camera_id: selectedCameraId });
          
          // Set timeout untuk camera initialization (30 detik)
          const timeoutId = setTimeout(() => {
            console.warn("⏰ Camera initialization timeout");
            setIsClosingModal(false);
            setIsInitializingCamera(false);
            socket.showNotification("Timeout menginisialisasi kamera - coba lagi");
            setInitializationTimeout(null);
          }, 30000);
          
          setInitializationTimeout(timeoutId);
        } else {
          console.error("❌ Socket not available for camera initialization");
          setIsClosingModal(false);
          setIsInitializingCamera(false);
          socket.showNotification("Koneksi socket tidak tersedia");
        }
        
        // Modal akan di-close otomatis di handleCameraInitialized setelah camera init selesai
        // Camera akan di-disable di main UI juga
      } else {
        console.error("❌ Failed to save config");
        setIsClosingModal(false);
        setIsInitializingCamera(false);
        socket.showNotification("Gagal menyimpan pengaturan");
      }
    } catch (error) {
      console.error('❌ Error in save process:', error);
      setIsClosingModal(false);
      setIsInitializingCamera(false);
      socket.showNotification("Terjadi kesalahan saat menyimpan pengaturan");
    }
  };

  const handleResetChanges = () => {
    if (config) {
      setPendingConfig(config);
      setHasChanges(false);
    }
  };

  // ENHANCED CLOSE HANDLER: Restore previous camera with loading
  const handleConfigClose = () => {
    // Check if camera selection changed
    if (selectedCameraId !== previousCameraId) {
      console.log(`🟡 Configuration closed - restoring camera from ${selectedCameraId} to ${previousCameraId}`);
      setIsRestoringCamera(true);
      
      if (socket.socket) {
        socket.socket.emit('initialize_camera', { camera_id: previousCameraId });
        
        // Set timeout untuk camera restoration (30 detik)
        const timeoutId = setTimeout(() => {
          console.warn("⏰ Camera restoration timeout for modal close");
          setIsRestoringCamera(false);
          handleClose(); // Force close even if camera restoration failed
          socket.showNotification("Timeout mengembalikan kamera - modal ditutup anyway");
          setInitializationTimeout(null);
        }, 30000);
        
        setInitializationTimeout(timeoutId);
      }
      
      // Modal akan di-close otomatis di handleCameraInitialized setelah restoration selesai
    } else {
      console.log(`🟡 Configuration closed - no camera change, closing immediately`);
      handleClose();
    }
  };

  // SIMPLE CAMERA SELECTION: Just update the selected camera ID
  const handleCameraSelection = (cameraId: number) => {
    setSelectedCameraId(cameraId);
    console.log(`📹 Selected camera ${cameraId} (will be applied on save)`);
  };


  const handleReloadConfig = async () => {
    setIsReloading(true);
    try {
      // Try backend reload first
      if (socket.socket && socket.isConnected) {
        socket.reloadConfig();
      }
      
      // Then reload frontend config
      await loadConfig();
      socket.showNotification("Konfigurasi berhasil dimuat ulang dari Firebase");
    } catch (error) {
      console.error('❌ Error reloading config:', error);
      socket.showNotification("Gagal memuat ulang konfigurasi");
    } finally {
      setIsReloading(false);
    }
  };

  // Model Tab Camera Management Functions
  // ENHANCED TAB CHANGE: Handle camera restoration when leaving model tab
  const handleTabChange = (newTab: string) => {
    // If leaving model tab and camera selection changed, restore previous camera
    if (activeTab === 'model' && newTab !== 'model' && selectedCameraId !== previousCameraId) {
      console.log(`🔄 Leaving model tab - restoring camera from ${selectedCameraId} to ${previousCameraId}`);
      setIsRestoringCamera(true);
      setPendingTabChange(newTab); // Simpan tab tujuan
      setSelectedCameraId(previousCameraId); // Reset selection to original
      
      if (socket.socket) {
        socket.socket.emit('initialize_camera', { camera_id: previousCameraId });
        
        // Set timeout untuk camera restoration (30 detik)
        const timeoutId = setTimeout(() => {
          console.warn("⏰ Camera restoration timeout for tab change");
          setIsRestoringCamera(false);
          setPendingTabChange(null);
          setActiveTab(newTab); // Force tab change even if camera restoration failed
          socket.showNotification("Timeout mengembalikan kamera - tab berubah anyway");
          setInitializationTimeout(null);
        }, 30000);
        
        setInitializationTimeout(timeoutId);
      }
      
      // Tab change akan dilakukan otomatis setelah restoration selesai
      return; // Don't change tab yet, wait for camera restoration
    }
    
    setActiveTab(newTab);
  };

  // SIMPLIFIED: No complex window close handling needed

  return (
    <>
      {/* Only show button if not controlled externally */}
      {isOpen === undefined && (
        <Button 
          variant="outline" 
          size="icon"
          onClick={() => setInternalOpen(true)}
        >
          <Settings className="h-4 w-4" />
        </Button>
      )}
      
      <DraggableWindow
        title="Konfigurasi Sistem"
        icon={<Settings className="h-5 w-5" />}
        isOpen={open}
        onClose={handleConfigClose}
        defaultPosition={{ x: 50, y: 50 }}
        defaultSize={{ width: '750px', height: '680px' }}
        minWidth="600px"
        minHeight="500px"
      >
        {(isLoading || isReloading || isRestoringCamera || isClosingModal) && (
          <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="text-center">
              <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-2"></div>
              <p className="text-sm text-muted-foreground">
                {isReloading ? "Memuat ulang konfigurasi..." : 
                 isRestoringCamera ? "Mengembalikan kamera sebelumnya..." :
                 isClosingModal ? "Menginisialisasi kamera baru..." :
                 "Memuat pengaturan..."}
              </p>
            </div>
          </div>
        )}

        {/* Header with reload button */}
        <div className="flex items-center justify-between mb-4 pb-2 border-b">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {socket.isConnected ? "🟢 Terhubung ke Firebase" : "🔴 Tidak terhubung"}
            </span>
            {!hasConfig && (
              <Badge variant="destructive" className="text-xs">
                Tidak ada config dari Firebase
              </Badge>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleReloadConfig}
            disabled={isLoading || isReloading || !socket.isConnected}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isReloading ? 'animate-spin' : ''}`} />
            {isReloading ? "Memuat..." : "Muat Ulang"}
          </Button>
        </div>

        {!hasConfig && (
          <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
              <RefreshCw className="h-4 w-4" />
              <span className="text-sm font-medium">Konfigurasi tidak tersedia</span>
            </div>
            <p className="text-xs text-amber-600/80 dark:text-amber-400/80 mt-1">
              Tidak ada konfigurasi yang dimuat dari Firebase. Klik &quot;Muat Ulang&quot; untuk mencoba lagi atau simpan pengaturan baru.
            </p>
          </div>
        )}

        <Tabs value={activeTab} className="w-full" onValueChange={handleTabChange}>
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="detection" className="flex items-center gap-2">
              <Target className="h-4 w-4" />
              Detection
            </TabsTrigger>
            <TabsTrigger value="visual" className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              Visual
            </TabsTrigger>
            <TabsTrigger value="model" className="flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              Model
            </TabsTrigger>
            <TabsTrigger value="advanced" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Advanced
            </TabsTrigger>
            <TabsTrigger value="simulation" className="flex items-center gap-2">
              <Gamepad2 className="h-4 w-4" />
              Simulasi
            </TabsTrigger>
          </TabsList>

          <TabsContent value="detection" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Zona Penghitungan</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="text-sm">Mode Zona</Label>
                  <Select
                    value={pendingConfig.detection.zoneMode}
                    onValueChange={(value: 'vertical' | 'horizontal') => updateDetectionConfig({ zoneMode: value })}
                  >
                    <SelectTrigger className="mt-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vertical">Vertikal (Geser Kiri-Kanan)</SelectItem>
                      <SelectItem value="horizontal">Horizontal (Geser Atas-Bawah)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-sm">
                    {pendingConfig.detection.zoneMode === 'vertical' 
                      ? `Posisi Awal Zona (dari kiri): ${pendingConfig.detection.zoneStart}%`
                      : `Posisi Awal Zona (dari atas): ${pendingConfig.detection.zoneStart}%`
                    }
                  </Label>
                  <Slider
                    value={[pendingConfig.detection.zoneStart]}
                    onValueChange={([value]) => updateDetectionConfig({ zoneStart: value })}
                    max={90}
                    min={0}
                    step={1}
                    className="mt-2"
                  />
                </div>
                
                <div>
                  <Label className="text-sm">
                    {pendingConfig.detection.zoneMode === 'vertical' 
                      ? `Lebar Zona: ${pendingConfig.detection.zoneWidth}%`
                      : `Tinggi Zona: ${pendingConfig.detection.zoneWidth}%`
                    }
                  </Label>
                  <Slider
                    value={[pendingConfig.detection.zoneWidth]}
                    onValueChange={([value]) => updateDetectionConfig({ zoneWidth: value })}
                    max={50}
                    min={5}
                    step={1}
                    className="mt-2"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <Label>Tampilkan Zona Penghitungan</Label>
                  <Switch
                    checked={pendingConfig.detection.showZone}
                    onCheckedChange={(checked) => updateDetectionConfig({ showZone: checked })}
                  />
                </div>

                <div className="p-3 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <div className="flex items-start gap-2">
                    <Target className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
                        Mode {pendingConfig.detection.zoneMode === 'vertical' ? 'Vertikal' : 'Horizontal'}
                      </p>
                      <p className="text-xs text-blue-600/80 dark:text-blue-400/80 mt-1">
                        {pendingConfig.detection.zoneMode === 'vertical' 
                          ? 'Zona dihitung dari kiri ke kanan. Sesuaikan posisi dan lebar zona sesuai sabuk konveyor.'
                          : 'Zona dihitung dari atas ke bawah. Sesuaikan posisi dan tinggi zona sesuai sabuk konveyor.'
                        }
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Pengaturan Deteksi</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="text-sm">
                    Ambang Batas Deteksi: {Math.round(pendingConfig.detection.threshold * 100)}%
                  </Label>
                  <Slider
                    value={[pendingConfig.detection.threshold]}
                    onValueChange={([value]) => updateDetectionConfig({ threshold: value })}
                    max={1}
                    min={0.1}
                    step={0.1}
                    className="mt-2"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <Label>Penghitungan Otomatis</Label>
                  <Switch
                    checked={pendingConfig.detection.autoCount}
                    onCheckedChange={(checked) => updateDetectionConfig({ autoCount: checked })}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="visual" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Opsi Tampilan</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>Tampilkan Kotak Pembatas</Label>
                  <Switch
                    checked={pendingConfig.visual.showBoxes}
                    onCheckedChange={(checked) => updateVisualConfig({ showBoxes: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium">Tampilkan Label Produk</Label>
                    <p className="text-xs text-muted-foreground">
                      Nama produk di atas bounding box deteksi
                    </p>
                  </div>
                  <Switch
                    checked={pendingConfig.visual.showLabels}
                    onCheckedChange={(checked) => updateVisualConfig({ showLabels: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium">Tampilkan Skor Kepercayaan</Label>
                    <p className="text-xs text-muted-foreground">
                      Persentase kepercayaan deteksi produk
                    </p>
                  </div>
                  <Switch
                    checked={pendingConfig.visual.showConfidence}
                    onCheckedChange={(checked) => updateVisualConfig({ showConfidence: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium">Tampilkan Info Overlay</Label>
                    <p className="text-xs text-muted-foreground">
                      FPS, statistik deteksi, status zona, performa sistem
                    </p>
                  </div>
                  <Switch
                    checked={pendingConfig.visual.showOverlays}
                    onCheckedChange={(checked) => updateVisualConfig({ showOverlays: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium">Tampilkan Semua Deteksi</Label>
                    <p className="text-xs text-muted-foreground">
                      Tampilkan semua class vs hanya produk terdaftar
                    </p>
                  </div>
                  <Switch
                    checked={pendingConfig.visual.showAllDetections}
                    onCheckedChange={(checked) => updateVisualConfig({ showAllDetections: checked })}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Warna & Tampilan</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="text-sm">
                    Opacity Zona: {Math.round(pendingConfig.visual.zoneOpacity * 100)}%
                  </Label>
                  <Slider
                    value={[pendingConfig.visual.zoneOpacity]}
                    onValueChange={([value]) => updateVisualConfig({ zoneOpacity: value })}
                    max={1}
                    min={0.1}
                    step={0.1}
                    className="mt-2"
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="model" className="space-y-4">
            <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Camera Selection</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm font-medium">Available Cameras</Label>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleRefreshCameras}
                          disabled={isLoadingCameras || !socket.isConnected}
                          className="h-6 px-2"
                        >
                          <RefreshCw className={`h-3 w-3 ${isLoadingCameras ? 'animate-spin' : ''}`} />
                        </Button>
                      </div>
                      
                      {isLoadingCameras ? (
                        <div className="flex items-center justify-center py-8 bg-muted rounded-lg">
                          <div className="flex flex-col items-center space-y-3">
                            <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full"></div>
                            <div className="text-sm text-muted-foreground">
                              Scanning cameras...
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Please wait while we detect available cameras
                            </div>
                          </div>
                        </div>
                      ) : (
                        <Select
                          value={selectedCameraId.toString()}
                          onValueChange={(value) => setSelectedCameraId(parseInt(value))}
                          disabled={!socket.isConnected}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select a camera..." />
                          </SelectTrigger>
                          <SelectContent>
                            {availableCameras.length > 0 ? (
                              availableCameras.map((camera: any) => (
                                <SelectItem key={camera.id} value={camera.id.toString()}>
                                  <div className="flex flex-col">
                                    <span className="font-medium">{camera.name}</span>
                                    <span className="text-xs text-muted-foreground">
                                      {camera.resolution} {camera.fps && `@ ${camera.fps}fps`}
                                    </span>
                                  </div>
                                </SelectItem>
                              ))
                            ) : (
                              <SelectItem value="no-cameras" disabled>
                                No cameras detected
                              </SelectItem>
                            )}
                          </SelectContent>
                        </Select>
                      )}
                    </div>
                    
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">Current Selection</Label>
                      <div className="p-3 bg-muted rounded-lg">
                        {isLoadingCameras ? (
                          <div className="flex items-center space-x-2">
                            <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full"></div>
                            <p className="text-sm text-muted-foreground">
                              Detecting cameras...
                            </p>
                          </div>
                        ) : (
                          <p className="text-sm font-mono">
                            Camera {selectedCameraId} {selectedCameraId !== previousCameraId && '(will be applied on save)'}
                          </p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">AI Model Selection</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">Available Models</Label>
                      {isLoadingModels ? (
                        <div className="flex items-center justify-center py-4">
                          <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full"></div>
                        </div>
                      ) : (
                        <Select
                          value={pendingConfig.advanced.model || ''}
                          onValueChange={(value) => {
                            setPendingConfig({
                              ...pendingConfig,
                              advanced: { ...pendingConfig.advanced, model: value }
                            });
                            setHasChanges(true);
                          }}
                          disabled={!socket.isConnected}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select a model..." />
                          </SelectTrigger>
                          <SelectContent>
                            {availableModels.map((model: any) => (
                              <SelectItem key={model.path} value={model.path}>
                                <div className="flex flex-col">
                                  <span className="font-medium">{model.display_name}</span>
                                  <span className="text-xs text-muted-foreground">
                                    {model.filename} ({model.size})
                                  </span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <div className="flex justify-end">
                  <Button
                    onClick={handleSaveSettings}
                    disabled={!socket.isConnected}
                    className="flex items-center gap-2"
                  >
                    <Save className="h-4 w-4" />
                    Save Camera & Model Settings
                  </Button>
                </div>
              </div>
          </TabsContent>

          <TabsContent value="advanced" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">System Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Resolution</Label>
                  <Select
                    value={pendingConfig.advanced.resolution}
                    onValueChange={(value) => {
                      const newConfig = {
                        ...pendingConfig,
                        advanced: { ...pendingConfig.advanced, resolution: value }
                      };
                      setPendingConfig(newConfig);
                      setHasChanges(true);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="640x480">640x480</SelectItem>
                      <SelectItem value="1280x720">1280x720 (HD)</SelectItem>
                      <SelectItem value="1920x1080">1920x1080 (Full HD)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-medium">
                    Frame Rate: {pendingConfig.advanced.frameRate} FPS
                  </Label>
                  <Slider
                    value={[pendingConfig.advanced.frameRate]}
                    onValueChange={([value]) => {
                      const newConfig = {
                        ...pendingConfig,
                        advanced: { ...pendingConfig.advanced, frameRate: value }
                      };
                      setPendingConfig(newConfig);
                      setHasChanges(true);
                    }}
                    min={10}
                    max={60}
                    step={5}
                    className="mt-2"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-medium">Processing Speed</Label>
                  <Select
                    value={pendingConfig.advanced.processingSpeed}
                    onValueChange={(value) => {
                      const newConfig = {
                        ...pendingConfig,
                        advanced: { ...pendingConfig.advanced, processingSpeed: value }
                      };
                      setPendingConfig(newConfig);
                      setHasChanges(true);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="realtime">Real-time</SelectItem>
                      <SelectItem value="fast">Fast</SelectItem>
                      <SelectItem value="balanced">Balanced</SelectItem>
                      <SelectItem value="accurate">Accurate</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="p-3 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <div className="flex items-start gap-2">
                    <Settings className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
                        Advanced Settings
                      </p>
                      <p className="text-xs text-blue-600/80 dark:text-blue-400/80 mt-1">
                        Camera and model selection have been moved to the Model tab for better workflow management.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="simulation" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Mode Simulasi</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium">Aktifkan Mode Simulasi</Label>
                    <p className="text-xs text-muted-foreground">
                      Mode simulasi memungkinkan testing deteksi tanpa hardware kamera
                    </p>
                  </div>
                  <Switch
                    checked={pendingConfig.simulation.enabled}
                    onCheckedChange={(checked) => updateSimulationConfig({ enabled: checked })}
                    disabled={!socket.isConnected}
                  />
                </div>
                
                {pendingConfig.simulation.enabled && (
                  <div className="p-3 bg-orange-50 dark:bg-orange-950/20 border border-orange-200 dark:border-orange-800 rounded-lg">
                    <div className="flex items-center gap-2 text-orange-600 dark:text-orange-400">
                      <Gamepad2 className="h-4 w-4" />
                      <span className="text-sm font-medium">Mode Simulasi Aktif</span>
                    </div>
                    <p className="text-xs text-orange-600/80 dark:text-orange-400/80 mt-1">
                      Gunakan tombol &quot;Kontrol Simulasi&quot; di scanner untuk menambah objek virtual
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

        </Tabs>

        {/* Save/Reset Buttons */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="flex items-center gap-2">
            {hasChanges && (
              <Badge variant="secondary" className="text-xs">
                Ada perubahan yang belum disimpan
              </Badge>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleResetChanges}
              disabled={!hasChanges}
              className="flex items-center gap-2"
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </Button>
            
            <Button
              size="sm"
              onClick={handleSaveSettings}
              disabled={!hasChanges || !socket.isConnected || isLoading || isInitializingCamera || isClosingModal || isRestoringCamera}
              className="flex items-center gap-2"
            >
              {(isLoading || isInitializingCamera || isClosingModal) && (
                <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"></div>
              )}
              {!isLoading && !isInitializingCamera && !isClosingModal && <Save className="h-4 w-4" />}
              {isLoading ? "Menyimpan..." : 
               isInitializingCamera ? "Menginisialisasi Kamera..." :
               isClosingModal ? "Menutup Konfigurasi..." :
               "Simpan Pengaturan"}
            </Button>
          </div>
        </div>
      </DraggableWindow>
    </>
  );
}