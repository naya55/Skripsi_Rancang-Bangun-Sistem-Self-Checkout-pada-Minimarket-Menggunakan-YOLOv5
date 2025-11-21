'use client';

import { useEffect } from 'react';
import { useSettings } from '@/contexts/SettingsContext';
import { useSocket } from './useSocket';

/**
 * Hook untuk sinkronisasi settings dari Firebase dengan socket state
 * Auto-apply loaded settings ke socket saat settings berubah
 */
export function useSettingsSync() {
  const { config, isLoading } = useSettings();
  const socket = useSocket();

  // Apply settings to socket when config changes
  useEffect(() => {
    if (!isLoading && socket.isConnected) {
        
      // Apply simulation setting
      if (config.simulation.enabled !== socket.isSimulationMode) {
          socket.toggleSimulation(config.simulation.enabled);
      }

      // Apply detection config (if socket has these functions)
      if (socket.updateConfig) {
        socket.updateConfig('detection', config.detection);
        socket.updateConfig('visual', config.visual);
        socket.updateConfig('advanced', config.advanced);
      }

      }
  }, [config, isLoading, socket.isConnected, socket.isSimulationMode]);

  return {
    config,
    isLoading,
    isSocketConnected: socket.isConnected
  };
}