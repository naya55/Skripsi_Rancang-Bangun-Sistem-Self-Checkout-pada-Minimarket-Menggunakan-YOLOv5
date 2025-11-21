export interface Product {
  name: string;
  price: number;
}

export interface CartItem {
  price: number;
  quantity: number;
}

export interface Cart {
  [productName: string]: CartItem;
}

export interface Transaction {
  id: string;
  items: TransactionItem[];
  total: number;
  timestamp: unknown;
  formatted_date?: string;
}

export interface TransactionItem {
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
}

export interface SimulatedObject {
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  created_time: number;
}

export interface DetectionConfig {
  zoneMode: 'vertical' | 'horizontal';
  zoneStart: number;
  zoneWidth: number;
  showZone: boolean;
  threshold: number;
  autoCount: boolean;
}

export interface VisualConfig {
  showBoxes: boolean;
  showLabels: boolean;
  showConfidence: boolean;
  showOverlays: boolean;
  showAllDetections: boolean;
  zoneColor: string;
  boxColor: string;
  zoneOpacity: number;
}

export interface AdvancedConfig {
  resolution: string;
  frameRate: number;
  model: string;
  processingSpeed: string;
  preset: string;
  cameraId: number;
}

export interface CameraInfo {
  id: number;
  name: string;
  resolution: string;
  isActive: boolean;
}

export interface SimulationConfig {
  enabled: boolean;
}

export interface AppConfig {
  detection: DetectionConfig;
  visual: VisualConfig;
  advanced: AdvancedConfig;
  simulation: SimulationConfig;
}

export interface User {
  uid: string;
  email: string;
  role: 'admin';
  displayName?: string;
  createdAt?: unknown;
  lastLogin?: unknown;
}

export interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
}