'use client';

import { useState, useEffect } from 'react';
import { useSocket } from '@/hooks/useSocket';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Camera, Gamepad2, Power, Loader2 } from 'lucide-react';
import { useSettings } from '@/contexts/SettingsContext';
import VideoPlayer from './VideoPlayer';

export default function ScannerView() {
  const socket = useSocket();
  const { config, hasConfig } = useSettings();
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);



  const handleCameraToggle = () => {
    // Block camera toggle if Model Tab is active
    if (socket.isModelTabActive) {
      socket.showNotification('Cannot toggle camera while Model Tab is active');
      return;
    }
    
    const newOverlayState = !socket.showCameraOverlay;
    // Toggle camera overlay (not actual camera hardware)
    socket.toggleCameraOverlay(newOverlayState);
    
    // Auto-start scanning when camera is enabled (overlay hidden)
    if (!newOverlayState && socket.yoloInitialized && hasConfig && config) {
      socket.startScanning(config.detection);
    }
    // Auto-stop scanning when camera is disabled (overlay shown)
    if (newOverlayState && socket.isScanning) {
      socket.stopScanning();
    }
  };


  const handleInitializeYolo = () => {
    socket.initializeYolo();
  };

  if (!isClient) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            Live Detection Feed
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="w-full h-96 bg-muted rounded-lg border flex items-center justify-center">
            <div className="text-muted-foreground">Loading camera feed...</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            Real-time Video Stream
          </CardTitle>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant={socket.isConnected ? "default" : "destructive"}>
              {socket.isConnected ? "Connected" : "Disconnected"}
            </Badge>
            
            
            {socket.yoloInitializing && (
              <Badge variant="outline" className="animate-pulse">
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                YOLO Loading...
              </Badge>
            )}
            
            {socket.yoloInitialized && (
              <Badge variant="default">
                YOLO Ready
              </Badge>
            )}
            
            {socket.isScanning && (
              <Badge variant="secondary" className="animate-pulse">
                Scanning...
              </Badge>
            )}

            {!hasConfig && (
              <Badge variant="destructive">
                No Firebase Config
              </Badge>
            )}
            
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col space-y-4 p-4">
        <div className="relative w-full">
          <VideoPlayer
            isConnected={socket.isConnected}
            isScanning={socket.isScanning}
            showCameraOverlay={socket.showCameraOverlay}
            cameraOverlayMessage={socket.cameraOverlayMessage}
            isModelTabActive={socket.isModelTabActive}
          />
          
          {socket.isSimulationMode && (
            <div className="absolute top-2 left-2">
              <Badge variant="outline" className="bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-200 border-orange-300 dark:border-orange-700">
                <Gamepad2 className="h-3 w-3 mr-1" />
                Simulation Mode
              </Badge>
            </div>
          )}
          
          {socket.isConnected && (
            <div className="absolute top-2 right-2">
              <Badge variant="outline" className="bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 border-green-300 dark:border-green-700">
                VIDEO Live
              </Badge>
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-3 mt-4">
          <Button
            onClick={handleCameraToggle}
            disabled={!socket.isConnected || socket.yoloInitializing || socket.isModelTabActive}
            variant={socket.showCameraOverlay ? "default" : "destructive"}
            className="flex items-center gap-2"
          >
            <Power className="h-4 w-4" />
            {socket.isModelTabActive ? "Model Tab Active" : (socket.showCameraOverlay ? "Hidupkan Kamera" : "Matikan Kamera")}
          </Button>
          
          {!socket.yoloInitialized && !socket.yoloInitializing && (
            <Button
              onClick={handleInitializeYolo}
              disabled={!socket.isConnected}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Loader2 className="h-4 w-4" />
              Inisialisasi YOLO
            </Button>
          )}
          
          
        </div>


      </CardContent>
    </Card>
  );
}