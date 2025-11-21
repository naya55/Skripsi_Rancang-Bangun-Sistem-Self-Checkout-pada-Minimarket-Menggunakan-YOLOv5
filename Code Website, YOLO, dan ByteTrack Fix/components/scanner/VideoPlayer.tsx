'use client';

import { useRef, useEffect } from 'react';
import { API_BASE_URL } from '@/lib/constants';

interface VideoPlayerProps {
  isConnected: boolean;
  isScanning: boolean;
  showCameraOverlay?: boolean;
  cameraOverlayMessage?: string;
  isModelTabActive?: boolean;
  onLoad?: () => void;
  onError?: () => void;
}

export default function VideoPlayer({ isConnected, showCameraOverlay = false, isModelTabActive = false, onLoad }: VideoPlayerProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const streamUrl = `${API_BASE_URL}/video_feed`;

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe || !isConnected) return;

    // Stop iframe if Model Tab is active
    if (isModelTabActive) {
      iframe.src = 'about:blank';
      return;
    }

    // Force reload iframe with cache-busting
    iframe.src = streamUrl + '?t=' + Date.now();
    
    // Simple load detection
    const loadTimer = setTimeout(() => {
      onLoad?.();
    }, 1000);

    return () => clearTimeout(loadTimer);
  }, [isConnected, streamUrl, isModelTabActive, onLoad]);

  if (!isConnected) {
    return (
      <div className="relative w-full max-h-[70vh] rounded-lg border bg-muted overflow-hidden flex items-center justify-center" style={{ height: '500px' }}>
        <div className="text-center">
          <p className="text-muted-foreground text-sm">❌ Server disconnected</p>
          <p className="text-xs text-muted-foreground/70 mt-1">Check backend connection</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full rounded-lg border bg-muted/50 overflow-hidden flex items-center justify-center" style={{ height: '500px' }}>
      <iframe
        ref={iframeRef}
        src={streamUrl}
        style={{
          width: '640px',
          height: '480px',
          border: 'none',
          background: 'var(--muted)',
          borderRadius: '8px'
        }}
        title="Live Video Feed"
        allow="camera"
        sandbox="allow-same-origin"
        scrolling="no"
        frameBorder="0"
      />
      
      {/* Camera Overlay (White) - for manual camera toggle */}
      {showCameraOverlay && (
        <div className="absolute inset-0 bg-white rounded-lg flex flex-col items-center justify-center z-10">
          <div className="text-center space-y-4 p-8">
            <div className="text-6xl">📷</div>
            <h3 className="text-xl font-semibold text-gray-800">
              Kamera Dimatikan
            </h3>
            <p className="text-gray-600 max-w-md mx-auto">
              Klik &quot;Hidupkan Kamera&quot; untuk memulai pemindaian produk
            </p>
          </div>
        </div>
      )}

    </div>
  );
}