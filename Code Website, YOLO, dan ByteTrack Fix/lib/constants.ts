const getApiBaseUrl = () => {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:5002';
  }
  
  const envUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envUrl) {
    return envUrl;
  }
  
  const hostname = window.location.hostname;
  const port = '5002';
  
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `http://127.0.0.1:${port}`;
  }
  
  if (hostname.startsWith('192.168.') || hostname.startsWith('10.') || hostname.startsWith('172.')) {
    return `http://${hostname}:${port}`;
  }
  
  return `http://127.0.0.1:${port}`;
};

export const API_BASE_URL = getApiBaseUrl();
export const SOCKET_URL = API_BASE_URL;

export const DEFAULT_CONFIG = {
  detection: {
    zoneMode: 'vertical' as const,
    zoneStart: 70,
    zoneWidth: 20,
    showZone: true,
    threshold: 0.5,
    autoCount: true
  },
  visual: {
    showBoxes: true,
    showLabels: true,
    showConfidence: true,
    showOverlays: true,
    showAllDetections: false,
    zoneColor: "#ff0000",
    boxColor: "#00ff00",
    zoneOpacity: 0.2
  },
  advanced: {
    resolution: "640x480",
    frameRate: 30,
    model: "yolov5s",
    processingSpeed: "balanced",
    preset: "retail",
    cameraId: 0
  },
  simulation: {
    enabled: false
  }
};

export const PRESETS = {
  retail: {
    detection: { threshold: 0.7, autoCount: true },
    visual: { showBoxes: true, showLabels: true, showConfidence: false, showOverlays: true, showAllDetections: false }
  },
  demo: {
    detection: { threshold: 0.5, autoCount: true },
    visual: { showBoxes: true, showLabels: true, showConfidence: true, showOverlays: true, showAllDetections: false }
  },
  debug: {
    detection: { threshold: 0.3, autoCount: false },
    visual: { showBoxes: true, showLabels: true, showConfidence: true, showOverlays: true, showAllDetections: true }
  }
};

export const PRODUCT_OPTIONS = [
  "person", "laptop", "smartphone", "mouse", "keyboard", 
  "headphones", "monitor", "tablet", "usb drive", "hard drive", "webcam",
  "indomie", "indomilk", "kecap", "keju", "sabun"
];