import cv2
import threading
import time
import numpy as np
from flask import Response
import io


class StreamingServer:
    def __init__(self):
        self.frame = None
        self.frame_lock = threading.Lock()
        self.output_frame = None
        self.frame_count = 0
        self.is_running = False
        
    def update_frame(self, frame):
        """Update the current frame thread-safely"""
        if frame is not None:
            with self.frame_lock:
                self.frame = frame.copy()
                self.frame_count += 1
    
    def get_frame(self):
        """Get current frame thread-safely"""
        with self.frame_lock:
            if self.frame is not None:
                return self.frame.copy()
            return None
    
    # No placeholder frames - direct frame handling only
    
    def generate_mjpeg_stream(self):
        """Generate MJPEG stream for video element"""
        self.is_running = True
        frame_count = 0
        
        pass
        
        while self.is_running:
            try:
                frame_count += 1
                
                # Get current frame
                frame = self.get_frame()
                
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Encode frame as JPEG with high quality
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                success, encoded_image = cv2.imencode('.jpg', frame, encode_param)
                
                if not success:
                    print(f"❌ Frame encoding failed at frame {frame_count}")
                    continue
                
                # Log every 100 frames
                if frame_count % 100 == 0:
                    pass
                
                # Create MJPEG frame
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(encoded_image)) + b'\r\n'
                       b'\r\n' + encoded_image.tobytes() + b'\r\n')
                
                # Control frame rate - 25 FPS
                time.sleep(0.04)
                
            except GeneratorExit:
                pass
                break
            except Exception as e:
                print(f"💥 MJPEG streaming error: {e}")
                time.sleep(0.1)
        
        print("🔚 MJPEG Stream ended")
    
    def generate_single_frame(self):
        """Generate single frame"""
        try:
            frame = self.get_frame()
            
            if frame is None:
                return None
            
            # Encode as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            success, encoded_image = cv2.imencode('.jpg', frame, encode_param)
            
            if success:
                return encoded_image.tobytes()
            else:
                return None
                
        except Exception as e:
            print(f"Single frame generation error: {e}")
            return None
    
    def stop(self):
        """Stop the streaming server"""
        self.is_running = False