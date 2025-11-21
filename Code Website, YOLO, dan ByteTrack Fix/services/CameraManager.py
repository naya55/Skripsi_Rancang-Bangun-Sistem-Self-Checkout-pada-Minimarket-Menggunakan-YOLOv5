import cv2
import time
import threading
from typing import List, Dict, Optional


class CameraManager:
    """
    Manages camera detection, switching, and lifecycle.
    Handles safe camera switching and management.
    """
    
    def __init__(self):
        self.current_camera = None
        self.current_camera_id = 1
        self.available_cameras = []
        self.lock = threading.Lock()
        self.is_switching = False
        
    
    def detect_available_cameras(self, max_cameras: int = 5) -> List[Dict]:
        """
        Scan for all available cameras on the system with enhanced error handling.
        
        Args:
            max_cameras: Maximum number of camera indices to check (reduced to 5 for safety)
            
        Returns:
            List of camera info dictionaries
        """
        available_cameras = []
        
        # Store current camera state to restore later
        current_id_stored = self.current_camera_id
        was_camera_active = self.current_camera is not None and self.current_camera.isOpened()
        
        print(f"🔍 Starting camera detection scan (max {max_cameras} cameras)")
        
        # FULLY release current camera for scanning
        if self.current_camera:
            try:
                print(f"🔄 Releasing current camera {current_id_stored} for scanning")
                self.current_camera.release()
                time.sleep(2.0)  # Even longer wait to ensure camera is fully released
            except Exception as release_error:
                print(f"❌ Error releasing camera for scanning: {release_error}")
            finally:
                self.current_camera = None
        
        # Suppress OpenCV errors temporarily
        import logging
        cv2_logger = logging.getLogger('cv2')
        original_level = cv2_logger.level
        cv2_logger.setLevel(logging.CRITICAL)
        
        try:
            for i in range(max_cameras):
                print(f"🔍 Testing camera index {i}...")
                cap = None
                cap = None
                
                try:
                    # Use DirectShow backend on Windows for better compatibility
                    import platform
                    if platform.system() == "Windows":
                        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    else:
                        cap = cv2.VideoCapture(i)
                    
                    # Set a timeout for camera operations
                    timeout_start = time.time()
                    timeout_duration = 5.0  # 5 seconds timeout per camera
                    
                    if cap.isOpened():
                        print(f"  📹 Camera {i} opened successfully")
                        
                        # Quick frame test first to avoid hanging
                        print(f"  🔍 Testing frame capture for camera {i}...")
                        ret, frame = cap.read()
                        
                        if ret and frame is not None and len(frame.shape) >= 2:
                            actual_height, actual_width = frame.shape[:2]
                            print(f"  ✅ Camera {i} basic test passed: {actual_width}x{actual_height}")
                            
                            # Test multiple resolutions to determine camera's actual capability
                            test_resolutions = [(1920, 1080), (1280, 720), (960, 540), (640, 480), (320, 240)]
                            max_supported_width, max_supported_height = actual_width, actual_height
                            
                            for test_w, test_h in test_resolutions:
                                if time.time() - timeout_start > timeout_duration:
                                    print(f"  ⏰ Timeout reached for camera {i}")
                                    break
                                
                                try:
                                    # Set the test resolution
                                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, test_w)
                                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, test_h)
                                    time.sleep(0.15)  # Longer pause for setting to take effect
                                    
                                    # Read a frame to see actual resolution
                                    ret, test_frame = cap.read()
                                    if ret and test_frame is not None and len(test_frame.shape) >= 2:
                                        test_height, test_width = test_frame.shape[:2]
                                        # Only log significant resolution changes to reduce console spam
                                        if test_width >= test_w * 0.9 and test_height >= test_h * 0.9:
                                            if test_width * test_height > max_supported_width * max_supported_height:
                                                max_supported_width, max_supported_height = test_width, test_height
                                                # Only print when we find a new higher resolution
                                                print(f"  ✅ Camera {i} supports {max_supported_width}x{max_supported_height}")
                                        
                                except Exception as res_error:
                                    print(f"  ⚠️ Resolution test {test_w}x{test_h} failed for camera {i}: {res_error}")
                                    continue
                            
                            # Use the highest supported resolution found
                            actual_width, actual_height = max_supported_width, max_supported_height
                            
                            # Get other properties safely
                            try:
                                fps = int(cap.get(cv2.CAP_PROP_FPS))
                                backend = cap.getBackendName()
                            except Exception:
                                fps = 30
                                backend = "Unknown"
                            
                            camera_info = {
                                'id': i,
                                'name': f'Camera {i} ({backend})',
                                'resolution': f'{actual_width}x{actual_height}',
                                'fps': fps if fps > 0 else 30,
                                'isActive': i == current_id_stored,
                                'backend': backend
                            }
                            
                            print(f"✅ Successfully detected Camera {i}: {actual_width}x{actual_height} @ {fps}fps ({backend})")
                            available_cameras.append(camera_info)
                        else:
                            print(f"❌ Camera {i}: Cannot read frames or invalid frame")
                    else:
                        print(f"❌ Camera {i}: Cannot open")
                
                except Exception as e:
                    print(f"❌ Error testing camera {i}: {str(e)}")
                    # Continue to next camera instead of failing completely
                
                finally:
                    if cap:
                        try:
                            cap.release()
                            time.sleep(0.3)  # Delay between camera tests for stability
                        except Exception as release_error:
                            print(f"⚠️ Error releasing camera {i}: {release_error}")
            
        except Exception as e:
            print(f"❌ Error during camera detection: {e}")
        
        finally:
            # Restore OpenCV logging level
            cv2_logger.setLevel(original_level)
        
        print(f"🔍 Camera detection completed - found {len(available_cameras)} cameras")
        
        # Restore current camera only if it was active before scanning
        if was_camera_active and current_id_stored is not None:
            print(f"🔄 Restoring previous camera {current_id_stored}")
            success = self.initialize_camera(current_id_stored)
            if not success:
                print(f"❌ Failed to restore Camera {current_id_stored}")
        
        self.available_cameras = available_cameras
        return available_cameras
    
    def switch_camera(self, new_camera_id: int) -> Dict:
        """
        Switch to a different camera with safe management.
        
        Args:
            new_camera_id: Index of the camera to switch to
            
        Returns:
            Dictionary with success status and details
        """
        with self.lock:
            if self.is_switching:
                return {
                    'success': False,
                    'error': 'Camera switch already in progress',
                    'camera_id': self.current_camera_id
                }
            
            # Validate camera_id range first
            if new_camera_id < 0 or new_camera_id > 10:
                return {
                    'success': False,
                    'error': f'Invalid camera ID {new_camera_id} - must be between 0 and 10',
                    'camera_id': self.current_camera_id
                }
            
            # If trying to switch to the same camera, just return success
            if new_camera_id == self.current_camera_id:
                return {
                    'success': True,
                    'camera_id': new_camera_id,
                    'message': f'Camera {new_camera_id} already active'
                }
            
            print(f"🔄 Switching camera from {self.current_camera_id} to {new_camera_id}")
            self.is_switching = True
            old_camera_id = self.current_camera_id
            
            try:
                # COMPLETELY release old camera first to avoid conflicts
                if self.current_camera:
                    try:
                        print(f"🔄 Releasing old camera {old_camera_id}")
                        self.current_camera.release()
                        time.sleep(1.5)  # Wait longer for camera to be fully released
                    except Exception as release_error:
                        print(f"❌ Error releasing old camera: {release_error}")
                    finally:
                        self.current_camera = None
                
                # Now try to initialize new camera with platform-specific backend
                import platform
                if platform.system() == "Windows":
                    new_cap = cv2.VideoCapture(new_camera_id, cv2.CAP_DSHOW)
                    print(f"🔄 Using DirectShow backend for camera switch to {new_camera_id}")
                else:
                    new_cap = cv2.VideoCapture(new_camera_id)
                
                if not new_cap.isOpened():
                    new_cap.release()
                    print(f"❌ Camera {new_camera_id} cannot be opened")
                    
                    # Try to restore old camera
                    if old_camera_id is not None:
                        restored_cap = cv2.VideoCapture(old_camera_id)
                        if restored_cap.isOpened():
                            self.current_camera = restored_cap
                        else:
                            restored_cap.release()
                            print(f"❌ Failed to restore Camera {old_camera_id}")
                    
                    self.is_switching = False
                    return {
                        'success': False,
                        'error': f'Camera {new_camera_id} cannot be opened',
                        'camera_id': self.current_camera_id
                    }
                
                # Test if camera can actually read frames
                ret, frame = new_cap.read()
                if not ret or frame is None:
                    new_cap.release()
                    print(f"❌ Camera {new_camera_id} cannot read frames")
                    
                    # Try to restore old camera
                    if old_camera_id is not None:
                        restored_cap = cv2.VideoCapture(old_camera_id)
                        if restored_cap.isOpened():
                            self.current_camera = restored_cap
                        else:
                            restored_cap.release()
                            print(f"❌ Failed to restore Camera {old_camera_id}")
                    
                    self.is_switching = False
                    return {
                        'success': False,
                        'error': f'Camera {new_camera_id} cannot read frames',
                        'camera_id': self.current_camera_id
                    }
                
                # Get new camera properties
                width = int(new_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(new_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                # Success! Switch to new camera
                self.current_camera = new_cap
                self.current_camera_id = new_camera_id
                
                self.is_switching = False
                
                return {
                    'success': True,
                    'camera_id': new_camera_id,
                    'resolution': f'{width}x{height}',
                    'previous_camera': old_camera_id
                }
                
            except Exception as e:
                print(f"❌ Error during camera switch: {e}")
                
                # Try to restore old camera if switch failed
                if self.current_camera is None and old_camera_id is not None:
                    try:
                        restored_cap = cv2.VideoCapture(old_camera_id)
                        if restored_cap.isOpened():
                            self.current_camera = restored_cap
                        else:
                            restored_cap.release()
                            print(f"❌ Failed to restore Camera {old_camera_id}")
                    except Exception as restore_error:
                        print(f"❌ Error restoring camera: {restore_error}")
                
                self.is_switching = False
                return {
                    'success': False,
                    'error': f'Camera switch failed: {str(e)}',
                    'camera_id': self.current_camera_id
                }
    
    def get_current_camera_info(self) -> Dict:
        """
        Get information about the currently active camera.
        
        Returns:
            Dictionary with current camera details
        """
        if not self.current_camera or not self.current_camera.isOpened():
            return {
                'id': None,
                'name': 'No camera active',
                'resolution': 'Unknown',
                'status': 'inactive'
            }
        
        try:
            width = int(self.current_camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.current_camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.current_camera.get(cv2.CAP_PROP_FPS))
            
            return {
                'id': self.current_camera_id,
                'name': f'Camera {self.current_camera_id}',
                'resolution': f'{width}x{height}',
                'fps': fps if fps > 0 else 30,
                'status': 'active'
            }
        except Exception as e:
            print(f"❌ Error getting camera info: {e}")
            return {
                'id': self.current_camera_id,
                'name': f'Camera {self.current_camera_id}',
                'resolution': 'Unknown',
                'status': 'error'
            }
    
    def initialize_camera(self, camera_id: int = 0) -> bool:
        """
        Initialize camera with given ID with enhanced error handling.
        
        Args:
            camera_id: Index of camera to initialize
            
        Returns:
            True if successful, False otherwise
        """
        print(f"🔄 Initializing camera {camera_id}...")
        
        # Validate camera_id range first
        if camera_id < 0 or camera_id > 10:
            print(f"❌ Invalid camera ID {camera_id} - must be between 0 and 10")
            return False
        
        try:
            # Release current camera completely
            if self.current_camera:
                try:
                    print(f"🔄 Releasing current camera {self.current_camera_id}")
                    self.current_camera.release()
                    time.sleep(1.5)  # Wait longer for camera to be fully released
                except Exception as release_error:
                    print(f"❌ Error releasing camera during init: {release_error}")
                finally:
                    self.current_camera = None
            
            # Try to initialize new camera with platform-specific backend
            import platform
            if platform.system() == "Windows":
                new_cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                print(f"🔄 Using DirectShow backend for camera {camera_id}")
            else:
                new_cap = cv2.VideoCapture(camera_id)
                print(f"🔄 Using default backend for camera {camera_id}")
            
            if new_cap.isOpened():
                print(f"✅ Camera {camera_id} opened successfully")
                
                # Test camera by reading a frame with timeout
                import threading
                import queue
                
                def read_frame_timeout(cap, result_queue):
                    try:
                        ret, frame = cap.read()
                        result_queue.put((ret, frame))
                    except Exception as e:
                        result_queue.put((False, None))
                
                result_queue = queue.Queue()
                thread = threading.Thread(target=read_frame_timeout, args=(new_cap, result_queue))
                thread.start()
                thread.join(timeout=3.0)  # 3 second timeout
                
                if thread.is_alive():
                    print(f"❌ Camera {camera_id} frame read timeout")
                    new_cap.release()
                    return False
                
                try:
                    ret, frame = result_queue.get_nowait()
                except queue.Empty:
                    print(f"❌ Camera {camera_id} no frame result")
                    new_cap.release()
                    return False
                
                if ret and frame is not None and len(frame.shape) >= 2:
                    height, width = frame.shape[:2]
                    print(f"✅ Camera {camera_id} frame test passed: {width}x{height}")
                    
                    # Success! Set as current camera
                    self.current_camera = new_cap
                    self.current_camera_id = camera_id
                    
                    print(f"✅ Camera {camera_id} initialization completed successfully")
                    return True
                else:
                    print(f"❌ Camera {camera_id} cannot read valid frames")
                    new_cap.release()
                    return False
            else:
                print(f"❌ Cannot open Camera {camera_id}")
                new_cap.release()
                return False
                
        except Exception as e:
            print(f"❌ Error initializing camera {camera_id}: {e}")
            if self.current_camera:
                try:
                    self.current_camera.release()
                except:
                    pass
                self.current_camera = None
            return False
    
    def read_frame(self):
        """
        Read a frame from the current camera with optimized error handling.
        
        Returns:
            Tuple of (success, frame) or (False, None) if no camera
        """
        if not self.current_camera or not self.current_camera.isOpened():
            return False, None
        
        try:
            ret, frame = self.current_camera.read()
            
            # Check if frame is valid
            if not ret or frame is None:
                return False, None
                
            return ret, frame
            
        except Exception as e:
            print(f"❌ Error reading frame from Camera {self.current_camera_id}: {e}")
            
            # Only try to reconnect for specific MSMF errors, not all errors
            # This reduces unnecessary reconnection attempts that cause lag
            if "cap_msmf.cpp" in str(e) and "grabFrame" in str(e):
                success = self.initialize_camera(self.current_camera_id)
                if success:
                    try:
                        ret, frame = self.current_camera.read()
                        return ret, frame
                    except:
                        pass
            
            return False, None
    
    def release_camera(self):
        """
        Release the current camera completely - called from DetectorManager.
        """
        return self.release()
    
    def release(self):
        """
        Release the current camera completely.
        """
        with self.lock:
            if self.current_camera:
                try:
                    self.current_camera.release()
                    time.sleep(0.5)  # Wait for camera to be fully released
                except Exception as e:
                    print(f"❌ Error releasing camera: {e}")
                finally:
                    self.current_camera = None
        
    def __del__(self):
        """
        Cleanup when object is destroyed.
        """
        self.release()