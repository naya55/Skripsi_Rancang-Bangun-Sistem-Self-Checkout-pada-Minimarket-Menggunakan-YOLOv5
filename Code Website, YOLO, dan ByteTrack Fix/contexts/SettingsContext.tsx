'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AppConfig } from '@/lib/types';
import { loadSettings, saveSettings } from '@/lib/firestore-settings';

interface SettingsContextType {
  config: AppConfig | null;
  isLoading: boolean;
  saveConfig: (newConfig: AppConfig) => Promise<boolean>;
  loadConfig: () => Promise<void>;
  hasConfig: boolean;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

interface SettingsProviderProps {
  children: ReactNode;
}

export function SettingsProvider({ children }: SettingsProviderProps) {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Auto-load settings when provider mounts
  useEffect(() => {
    loadConfigFromFirestore();
  }, []);

  const loadConfigFromFirestore = async () => {
    setIsLoading(true);
    
    try {
      const savedConfig = await loadSettings();
      
      if (savedConfig) {
        setConfig(savedConfig);
      } else {
        setConfig(null);
      }
    } catch (error) {
      console.error('❌ Error loading settings from Firebase:', error);
      setConfig(null);
    } finally {
      setIsLoading(false);
    }
  };

  const saveConfig = async (newConfig: AppConfig): Promise<boolean> => {
    setIsLoading(true);
    
    try {
      const success = await saveSettings(newConfig);
      
      if (success) {
        setConfig(newConfig);
        return true;
      } else {
        console.error('❌ Failed to save config');
        return false;
      }
    } catch (error) {
      console.error('❌ Error saving config:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const loadConfig = async () => {
    await loadConfigFromFirestore();
  };

  const value: SettingsContextType = {
    config,
    isLoading,
    saveConfig,
    loadConfig,
    hasConfig: config !== null
  };

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}