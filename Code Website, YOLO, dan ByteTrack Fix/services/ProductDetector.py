import cv2
import torch
import numpy as np
from PIL import Image
import time
import threading
import os
import warnings
import sys

warnings.filterwarnings("ignore", category=FutureWarning)

# Simple ByteTracker implementation
class SimpleTracker:
    def __init__(self, max_age=30, min_confidence=0.5):
        self.tracks = {}
        self.next_id = 1
        self.max_age = max_age
        self.min_confidence = min_confidence
        
    def update(self, detections):
        # Simple tracking based on IoU and position
        tracked_objects = []
        current_time = time.time()
        
        for det in detections:
            best_match = None
            best_iou = 0.3  # Minimum IoU threshold
            
            # Find best matching track
            for track_id, track_data in self.tracks.items():
                if track_data['label'] == det['label']:
                    iou = self._calculate_iou(det['box'], track_data['box'])
                    if iou > best_iou:
                        best_iou = iou
                        best_match = track_id
            
            if best_match:
                # Update existing track
                self.tracks[best_match].update({
                    'box': det['box'],
                    'center': det['center'],
                    'confidence': det['confidence'],
                    'last_seen': current_time,
                    'age': 0
                })
                track_id = best_match
            else:
                # Create new track
                track_id = self.next_id
                self.next_id += 1
                self.tracks[track_id] = {
                    'label': det['label'],
                    'box': det['box'],
                    'center': det['center'],
                    'confidence': det['confidence'],
                    'last_seen': current_time,
                    'age': 0
                }
            
            # Add track_id to detection
            det['track_id'] = track_id
            tracked_objects.append(det)
        
        # Age and remove old tracks
        to_remove = []
        for track_id, track_data in self.tracks.items():
            track_data['age'] += 1
            if track_data['age'] > self.max_age:
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del self.tracks[track_id]
        
        return tracked_objects
    
    def _calculate_iou(self, box1, box2):
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0


class ProductDetector:
    def __init__(self, model_path, camera_id=0):
        self.model_path = model_path
        self.camera_id = camera_id
        self.model = None
        self.is_running = False
        self.detection_thread = None
        self.cart = {}
        self.frame = None
        self.product_catalog = {}  # Will be updated by DetectorManager
        self.frame_width = 0
        self.frame_height = 0
        self.counted_objects = {}
        self.counting_zone_start_percent = 70
        self.counting_zone_width_percent = 20
        self.tracker = SimpleTracker()  # Add simple tracker
        self.load_model()
        self.stop_flag = threading.Event()

        self.detection_threshold = 0.5
        self.auto_count_enabled = True
        self.show_boxes = True
        self.show_labels = True
        self.show_confidence = True
        self.show_overlays = True  # NEW: Info overlay control
        self.show_all_detections = False  # NEW: Show all 80 classes vs only catalog products
        self.zone_color = (0, 0, 255)
        self.box_color = (0, 255, 0)
        self.zone_opacity = 0.2
        self.target_resolution = (640, 480)
        self.target_fps = 30
        self.processing_speed = 'balanced'
        self.model_type = 'yolov5s'
        
        # Info overlay tracking
        self.fps_counter = 0
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.detection_count = 0
        self.last_detection_time = time.time()
        self.processing_time = 0


    def load_model(self):
        try:
            
            # Check if file exists and is readable
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
            # Check file size
            file_size = os.path.getsize(self.model_path)
            
            if file_size == 0:
                raise ValueError(f"Model file is empty: {self.model_path}")
            
            print(f"Loading YOLOv5 model from: {self.model_path}")
            
            # Comprehensive fix for PyTorch 2.6+ security requirements
            # Clear cache first to avoid corrupted cache issues
            import shutil
            import torch.hub
            
            # Clear corrupted cache
            cache_dir = torch.hub.get_dir()
            yolo_cache = os.path.join(cache_dir, 'ultralytics_yolov5_master')
            if os.path.exists(yolo_cache):
                print("Clearing corrupted YOLOv5 cache...")
                shutil.rmtree(yolo_cache)
            
            # Set environment variable for weights_only=False
            os.environ['TORCH_LOAD_WEIGHTS_ONLY'] = 'False'
            
            # Try multiple loading strategies
            success = False
            
            # Strategy 1: Direct model loading with force_reload and weights_only=False
            try:
                print("Attempting direct model loading with force_reload...")
                self.model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                          path=self.model_path, 
                                          trust_repo=True, 
                                          force_reload=True,
                                          skip_validation=True)
                success = True
                print("✅ Model loaded successfully with direct loading")
            except Exception as e1:
                print(f"Direct loading failed: {e1}")
                
                # Strategy 2: Load with manual torch.load and weights_only=False
                try:
                    print("Attempting manual torch.load with weights_only=False...")
                    import torch
                    
                    # Load checkpoint manually
                    checkpoint = torch.load(self.model_path, map_location='cpu', weights_only=False)
                    
                    # Create model from checkpoint
                    self.model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                              path=self.model_path, 
                                              trust_repo=True, 
                                              force_reload=True)
                    success = True
                    print("✅ Model loaded successfully with manual loading")
                except Exception as e2:
                    print(f"Manual loading failed: {e2}")
                    raise e2
            
            if not success:
                raise Exception("All model loading strategies failed")
            
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def set_detection_threshold(self, threshold):
        self.detection_threshold = max(0.1, min(1.0, threshold))

    def set_auto_count(self, enabled):
        self.auto_count_enabled = enabled

    def set_show_boxes(self, show):
        self.show_boxes = show

    def set_show_labels(self, show):
        self.show_labels = show

    def set_show_confidence(self, show):
        self.show_confidence = show

    def set_show_overlays(self, show):
        self.show_overlays = show

    def set_show_all_detections(self, show):
        self.show_all_detections = show

    def set_zone_color(self, color):
        if isinstance(color, str):
            color = color.lstrip('#')
            self.zone_color = tuple(int(color[i:i+2], 16) for i in (4, 2, 0))
        elif isinstance(color, (list, tuple)) and len(color) == 3:
            self.zone_color = tuple(color)

    def set_box_color(self, color):
        if isinstance(color, str):
            color = color.lstrip('#')
            self.box_color = tuple(int(color[i:i+2], 16) for i in (4, 2, 0))
        elif isinstance(color, (list, tuple)) and len(color) == 3:
            self.box_color = tuple(color)

    def set_zone_opacity(self, opacity):
        self.zone_opacity = max(0.1, min(1.0, opacity))

    def set_resolution(self, resolution):
        if isinstance(resolution, str):
            width, height = map(int, resolution.split('x'))
            self.target_resolution = (width, height)
        elif isinstance(resolution, (list, tuple)) and len(resolution) == 2:
            self.target_resolution = tuple(resolution)

    def set_frame_rate(self, fps):
        self.target_fps = max(10, min(60, fps))

    def set_processing_speed(self, speed):
        self.processing_speed = speed

    def set_model(self, model_type):
        self.model_type = model_type

    def get_detection_settings(self):
        return {
            'threshold': self.detection_threshold,
            'autoCount': self.auto_count_enabled,
            'showBoxes': self.show_boxes,
            'showLabels': self.show_labels,
            'showConfidence': self.show_confidence,
            'zoneColor': self.zone_color,
            'boxColor': self.box_color,
            'zoneOpacity': self.zone_opacity,
            'resolution': self.target_resolution,
            'frameRate': self.target_fps,
            'processingSpeed': self.processing_speed,
            'modelType': self.model_type
        }

    def apply_visual_config(self, config):
        if 'showBoxes' in config:
            self.set_show_boxes(config['showBoxes'])
        if 'showLabels' in config:
            self.set_show_labels(config['showLabels'])
        if 'showConfidence' in config:
            self.set_show_confidence(config['showConfidence'])
        if 'showOverlays' in config:
            self.set_show_overlays(config['showOverlays'])
        if 'showAllDetections' in config:
            self.set_show_all_detections(config['showAllDetections'])
        if 'zoneColor' in config:
            self.set_zone_color(config['zoneColor'])
        if 'boxColor' in config:
            self.set_box_color(config['boxColor'])
        if 'zoneOpacity' in config:
            self.set_zone_opacity(config['zoneOpacity'])

    def apply_detection_config(self, config):
        if 'threshold' in config:
            self.set_detection_threshold(config['threshold'])
        if 'autoCount' in config:
            self.set_auto_count(config['autoCount'])

    def apply_advanced_config(self, config):
        if 'resolution' in config:
            self.set_resolution(config['resolution'])
        if 'frameRate' in config:
            self.set_frame_rate(config['frameRate'])
        if 'processingSpeed' in config:
            self.set_processing_speed(config['processingSpeed'])
        if 'model' in config:
            self.set_model(config['model'])

    def add_to_cart(self, product_name):
        product_lower = product_name.lower()
        if product_lower in self.product_catalog:
            price = self.product_catalog[product_lower]
            if product_lower in self.cart:
                self.cart[product_lower]["quantity"] += 1
            else:
                self.cart[product_lower] = {
                    "price": price,
                    "quantity": 1
                }
            return True
        return False

    def get_cart(self):
        return self.cart

    def clear_cart(self):
        self.cart = {}
        self.counted_objects = {}

    def calculate_total(self):
        total = 0
        for product, details in self.cart.items():
            total += details["price"] * details["quantity"]
        return total

    def format_cart_for_display(self):
        display_items = []
        for product, details in self.cart.items():
            display_items.append({
                "name": product,
                "price": details["price"],
                "quantity": details["quantity"],
                "subtotal": details["price"] * details["quantity"]
            })
        return display_items

    def _get_box_color(self, label_lower):
        if label_lower in self.product_catalog:
            return self.box_color
        else:
            return (0, 165, 255)

    def _draw_detection_box(self, frame, x1, y1, x2, y2, label, confidence, label_lower, track_id=None):
        if not self.show_boxes:
            return

        color = self._get_box_color(label_lower)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        if self.show_labels:
            confidence_text = f": {confidence:.2f}" if self.show_confidence else ""
            track_text = f" [ID:{track_id}]" if track_id is not None else ""
            
            # Get product price for display
            price_text = ""
            if label_lower in self.product_catalog:
                price = self.product_catalog[label_lower]
                price_text = f" Rp{price:,.0f}"
            
            text = f"{label}{confidence_text}{track_text}{price_text}"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]

            text_bg_x1 = x1
            text_bg_y1 = y1 - 25 if y1 - 25 > 0 else 0
            text_bg_x2 = x1 + text_size[0] + 10
            text_bg_y2 = y1

            cv2.rectangle(frame, (text_bg_x1, text_bg_y1), (text_bg_x2, text_bg_y2), color, -1)
            cv2.putText(frame, text, (x1 + 5, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    def _draw_info_overlay(self, frame, detected_objects, zone_status=False, total_detections=0):
        if not self.show_overlays:
            return
            
        # Update FPS calculation
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps_counter = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
        
        # Prepare overlay info
        overlay_info = [
            f"FPS: {self.fps_counter:.1f}",
            f"Products: {len(detected_objects)}",
            f"Model: {self.model_type}",
            f"Threshold: {self.detection_threshold:.2f}",
            f"Processing: {self.processing_time:.0f}ms"
        ]
        
        # Show detection mode
        if self.show_all_detections:
            overlay_info.append(f"Mode: All ({total_detections} total)")
        else:
            overlay_info.append("Mode: Products Only")
        
        if zone_status:
            overlay_info.append("Zone: ACTIVE")
        else:
            overlay_info.append("Zone: Clear")
            
        # Draw semi-transparent background
        overlay_height = len(overlay_info) * 25 + 10
        overlay_bg = np.zeros((overlay_height, 200, 3), dtype=np.uint8)
        overlay_bg[:] = (0, 0, 0)  # Black background
        
        # Position in top-left corner
        h, w = frame.shape[:2]
        roi = frame[10:10+overlay_height, 10:210]
        
        # Apply overlay with transparency
        alpha = 0.7
        cv2.addWeighted(overlay_bg, alpha, roi, 1-alpha, 0, roi)
        
        # Draw info text
        for i, info in enumerate(overlay_info):
            y_pos = 30 + i * 25
            color = (0, 255, 0) if "FPS" in info else (255, 255, 255)  # Green for FPS, white for others
            if "Zone: ACTIVE" in info:
                color = (0, 255, 255)  # Yellow for active zone
            cv2.putText(frame, info, (15, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def detect_objects(self, frame):
        start_time = time.time()
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_frame)

        if self.processing_speed == 'fast':
            size = 320
        elif self.processing_speed == 'accurate':
            size = 1280
        else:
            size = 640

        results = self.model(img, size=size)

        detected_objects = []
        zone_status = False  # Track if any object is in zone
        total_detections = 0  # Track total detections above threshold

        # Extract detections more efficiently
        if hasattr(results, 'pandas'):
            detections_df = results.pandas().xyxy[0]
            
            for i, row in detections_df.iterrows():
                label = row['name']
                label_lower = label.lower()
                confidence = row['confidence']
                x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])

                if confidence > self.detection_threshold:
                    total_detections += 1  # Count all detections above threshold
                    
                    # Determine if we should show this detection
                    is_catalog_product = label_lower in self.product_catalog
                    should_show = self.show_all_detections or is_catalog_product

                    # Only add to detected_objects if it's a catalog product (for cart functionality)
                    if is_catalog_product:
                        center_x = (x1 + x2) // 2
                        # Check if object is in counting zone
                        if self.frame_width > 0:
                            zone_start = int(self.frame_width * self.counting_zone_start_percent / 100)
                            zone_end = int(self.frame_width * (self.counting_zone_start_percent + self.counting_zone_width_percent) / 100)
                            if zone_start <= center_x <= zone_end:
                                zone_status = True
                                
                        detected_objects.append({
                            'label': label_lower,
                            'box': (x1, y1, x2, y2),
                            'center': ((x1 + x2) // 2, (y1 + y2) // 2),
                            'confidence': confidence
                        })

        # Apply tracking to catalog products only
        if detected_objects:
            detected_objects = self.tracker.update(detected_objects)

        # Draw detection boxes with tracking info
        for obj in detected_objects:
            if self.show_all_detections or obj['label'] in self.product_catalog:
                self._draw_detection_box(frame, *obj['box'], obj['label'], obj['confidence'], obj['label'], obj.get('track_id'))

        # Calculate processing time
        self.processing_time = (time.time() - start_time) * 1000
        
        # Draw info overlay
        self._draw_info_overlay(frame, detected_objects, zone_status, total_detections)

        return frame, detected_objects

    def start_detection(self):
        if self.is_running:
            return False

        self.is_running = True
        self.stop_flag.clear()
        self.detection_thread = threading.Thread(target=self._detection_loop)
        self.detection_thread.daemon = True
        self.detection_thread.start()
        return True

    def stop_detection(self):
        self.is_running = False
        self.stop_flag.set()
        if self.detection_thread:
            self.detection_thread.join(timeout=1.0)
            self.detection_thread = None
        return True

    def _detection_loop(self):
        cap = cv2.VideoCapture(self.camera_id)

        if self.target_resolution:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_resolution[1])

        if self.target_fps:
            cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self.frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        cv2.namedWindow("Controls")
        cv2.createTrackbar("Zone Start %", "Controls", self.counting_zone_start_percent, 100, lambda x: None)
        cv2.createTrackbar("Zone Width %", "Controls", self.counting_zone_width_percent, 50, lambda x: None)

        active_objects = {}
        last_seen = {}

        frame_time = 1.0 / self.target_fps if self.target_fps > 0 else 0.033

        try:
            while self.is_running and not self.stop_flag.is_set():
                start_time = time.time()

                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                self.counting_zone_start_percent = cv2.getTrackbarPos("Zone Start %", "Controls")
                self.counting_zone_width_percent = cv2.getTrackbarPos("Zone Width %", "Controls")

                counting_zone_x = int(self.frame_width * self.counting_zone_start_percent / 100)
                counting_zone_width = int(self.frame_width * self.counting_zone_width_percent / 100)

                processed_frame, detected_objects = self.detect_objects(frame)

                current_time = time.time()
                current_objects = set()

                for obj in detected_objects:
                    label = obj['label']
                    box = obj['box']
                    center_x = obj['center'][0]
                    object_id = f"{label}_{box[0]}_{box[1]}"
                    current_objects.add(object_id)

                    if (center_x > counting_zone_x and
                        center_x < counting_zone_x + counting_zone_width and
                        object_id not in self.counted_objects and
                            self.auto_count_enabled):
                        self.add_to_cart(label)
                        self.counted_objects[object_id] = True

                    last_seen[object_id] = current_time

                for obj_id in list(last_seen.keys()):
                    if obj_id not in current_objects:
                        if current_time - last_seen[obj_id] > 2.0:
                            del last_seen[obj_id]
                            if obj_id in self.counted_objects:
                                del self.counted_objects[obj_id]

                zone_start = (counting_zone_x, 0)
                zone_end = (counting_zone_x, self.frame_height)
                zone_end_right = (counting_zone_x + counting_zone_width, 0)
                zone_start_right = (counting_zone_x + counting_zone_width, self.frame_height)

                overlay = processed_frame.copy()
                cv2.rectangle(overlay, (counting_zone_x, 0),
                              (counting_zone_x + counting_zone_width, self.frame_height),
                              self.zone_color, -1)
                cv2.addWeighted(overlay, self.zone_opacity, processed_frame, 1 - self.zone_opacity, 0, processed_frame)

                cv2.line(processed_frame, zone_start, zone_end, self.zone_color, 2)
                cv2.line(processed_frame, zone_end_right, zone_start_right, self.zone_color, 2)

                zone_text = "COUNTING ZONE"
                text_size = cv2.getTextSize(zone_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                text_x = counting_zone_x + (counting_zone_width - text_size[0]) // 2
                text_y = 30

                if hasattr(self, 'show_overlays') and self.show_overlays:
                    cv2.rectangle(processed_frame, (text_x - 5, text_y - text_size[1] - 5),
                                  (text_x + text_size[0] + 5, text_y + 5), self.zone_color, -1)
                    cv2.putText(processed_frame, zone_text, (text_x, text_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

                    settings_text = f"Zone Start: {self.counting_zone_start_percent}%, Width: {self.counting_zone_width_percent}%"
                    cv2.putText(processed_frame, settings_text, (10, self.frame_height - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    config_text = f"Threshold: {self.detection_threshold:.1f} | FPS: {self.target_fps} | {self.processing_speed.title()}"
                    cv2.putText(processed_frame, config_text, (10, self.frame_height - 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                self.frame = processed_frame

                # NO GUI windows - this is a headless web service
                # cv2.imshow removed to prevent unwanted popups
                
                elapsed_time = time.time() - start_time
                sleep_time = max(0, frame_time - elapsed_time)
                time.sleep(sleep_time)

        finally:
            cap.release()
            # No GUI cleanup needed

    def get_current_frame(self):
        return self.frame

    def encode_frame_jpg(self):
        if self.frame is None:
            return None

        _, buffer = cv2.imencode('.jpg', self.frame)
        return buffer.tobytes()

    def print_cart_summary(self):
        cart_items = self.format_cart_for_display()
        if not cart_items:
            print("Shopping cart is empty.")
            return

        print("\n--- Shopping Cart Summary ---")
        for item in cart_items:
            print(f"{item['name']} x{item['quantity']} - Rp {item['price']} each = Rp {item['subtotal']}")

        print(f"Total: Rp {self.calculate_total()}")
        print("----------------------------")

    def get_performance_stats(self):
        return {
            'model_type': self.model_type,
            'resolution': self.target_resolution,
            'fps': self.target_fps,
            'processing_speed': self.processing_speed,
            'detection_threshold': self.detection_threshold,
            'total_products': len(self.product_catalog),
            'cart_items': len(self.cart),
            'cart_total': self.calculate_total()
        }
    
    def get_model_labels(self):
        """Get all available labels from the loaded YOLO model"""
        if self.model is None:
            return []
        
        try:
            # Method 1: Direct access to names
            if hasattr(self.model, 'names'):
                names = self.model.names
                # Convert to list format for frontend
                if isinstance(names, dict):
                    labels = [names[i] for i in sorted(names.keys())]
                    return labels
                elif isinstance(names, list):
                    return names
            
            # Method 2: Access via model.model.names (for YOLOv5)
            if hasattr(self.model, 'model') and hasattr(self.model.model, 'names'):
                names = self.model.model.names
                if isinstance(names, dict):
                    labels = [names[i] for i in sorted(names.keys())]
                    return labels
                elif isinstance(names, list):
                    return names
            
            # Method 3: Try module attribute
            if hasattr(self.model, 'module') and hasattr(self.model.module, 'names'):
                names = self.model.module.names
                if isinstance(names, dict):
                    return [names[i] for i in sorted(names.keys())]
                elif isinstance(names, list):
                    return names
            
            return []
            
        except Exception as e:
            print(f"[ERROR] Failed to get model labels: {e}")
            import traceback
            traceback.print_exc()
            return []
