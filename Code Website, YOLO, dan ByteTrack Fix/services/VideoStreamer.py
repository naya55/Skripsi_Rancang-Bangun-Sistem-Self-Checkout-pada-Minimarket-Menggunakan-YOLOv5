import cv2
import threading
import time
import numpy as np


class VideoStreamer:
    def __init__(self):
        self.frame = None
        self.lock = threading.Lock()
        self.is_active = False
        self.frame_ready = threading.Event()
        self.frame = None
        self.frame_ready.set()
        
    def update_frame(self, frame):
        if frame is not None:
            with self.lock:
                self.frame = frame.copy()
                self.frame_ready.set()
    
    def get_latest_frame(self):
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            else:
                return None
    
    
    def generate_frames(self):
        self.is_active = True
        frame_count = 0
        
        while self.is_active:
            try:
                frame = self.get_latest_frame()
                
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Add frame counter
                frame_count += 1
                
                # Encode with good quality
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                success, buffer = cv2.imencode('.jpg', frame, encode_param)
                
                if not success:
                    print("Frame encoding failed")
                    continue  # Skip this frame, web will handle blank screen
                
                frame_bytes = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
                       b'\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(0.066)  # ~15 FPS - slower for stability
                
            except Exception as e:
                print(f"Video streaming error: {e}")
                # Skip error frame, web will handle blank screen
                time.sleep(0.1)
    
    def stop(self):
        self.is_active = False
        self.frame_ready.set()
    
    def wait_for_frame(self, timeout=5.0):
        return self.frame_ready.wait(timeout)