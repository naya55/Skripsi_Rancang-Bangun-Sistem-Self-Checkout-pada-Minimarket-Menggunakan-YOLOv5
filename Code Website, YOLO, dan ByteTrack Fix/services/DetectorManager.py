import cv2
import time
import threading
import numpy as np
import json
import os
from CameraManager import CameraManager


class DetectorManager:
    def __init__(self, model_path, product_manager, firestore_manager=None, camera_manager=None):
        from ProductDetector import ProductDetector
        self.detector = ProductDetector(model_path=model_path)
        self.product_manager = product_manager
        self.firestore_manager = firestore_manager
        self.camera_manager = camera_manager or CameraManager()
        self.is_scanning = False
        self.lock = threading.Lock()
        self.zone_start_percent = 70
        self.zone_width_percent = 20

        self.objects_in_zone = {}
        self.counted_objects = {}
        self.last_detections = {}
        self.object_timeout = 2.0

        self.simulation_mode = False
        self.simulated_objects = {}
        self.next_sim_id = 1

        self.config = {
            'detection': {
                'zoneMode': 'vertical',
                'zoneStart': 70,
                'zoneWidth': 20,
                'showZone': True,
                'threshold': 0.5,
                'autoCount': True
            },
            'visual': {
                'showBoxes': True,
                'showLabels': True,
                'showConfidence': True,
                'showOverlays': True,
                'showAllDetections': False,
                'zoneColor': '#ff0000',
                'boxColor': '#00ff00',
                'zoneOpacity': 0.2
            },
            'advanced': {
                'resolution': '640x480',
                'frameRate': 30,
                'model': 'yolov5s',
                'processingSpeed': 'balanced',
                'preset': 'retail',
                'cameraId': 0
            }
        }

        self.presets = {
            'retail': {
                'detection': {'threshold': 0.7, 'autoCount': True},
                'visual': {'showBoxes': True, 'showLabels': True, 'showConfidence': False, 'showAllDetections': False}
            },
            'demo': {
                'detection': {'threshold': 0.5, 'autoCount': True},
                'visual': {'showBoxes': True, 'showLabels': True, 'showConfidence': True, 'showAllDetections': False}
            },
            'debug': {
                'detection': {'threshold': 0.3, 'autoCount': False},
                'visual': {'showBoxes': True, 'showLabels': True, 'showConfidence': True, 'showAllDetections': True}
            }
        }

        self.config_file = 'detection_config.json'
        self.load_config_from_sources()

    def set_zone_parameters(self, start_percent, width_percent):
        self.zone_start_percent = start_percent
        self.zone_width_percent = width_percent
        self.config['detection']['zoneStart'] = start_percent
        self.config['detection']['zoneWidth'] = width_percent

    def toggle_simulation_mode(self, enabled):
        with self.lock:
            self.simulation_mode = enabled
            if not enabled:
                self.simulated_objects.clear()

    def add_simulated_object(self, label, x, y, width, height):
        with self.lock:
            obj_id = f"sim_{self.next_sim_id}"
            self.next_sim_id += 1

            self.simulated_objects[obj_id] = {
                'label': label.lower(),
                'x': x,
                'y': y,
                'width': width,
                'height': height,
                'created_time': time.time()
            }

            return obj_id

    def update_simulated_object(self, obj_id, x=None, y=None, width=None, height=None, label=None):
        with self.lock:
            if obj_id in self.simulated_objects:
                obj = self.simulated_objects[obj_id]
                if x is not None:
                    obj['x'] = x
                if y is not None:
                    obj['y'] = y
                if width is not None:
                    obj['width'] = width
                if height is not None:
                    obj['height'] = height
                if label is not None:
                    obj['label'] = label.lower()
                return True
            return False

    def remove_simulated_object(self, obj_id):
        with self.lock:
            if obj_id in self.simulated_objects:
                del self.simulated_objects[obj_id]
                self.objects_in_zone.pop(obj_id, None)
                self.counted_objects.pop(obj_id, None)
                return True
            return False

    def get_simulated_objects(self):
        return self.simulated_objects.copy()

    def start_scanning(self):
        with self.lock:
            self.detector.clear_cart()
            self.is_scanning = True
            self.objects_in_zone.clear()
            self.counted_objects.clear()
            self.last_detections.clear()

    def stop_scanning(self):
        with self.lock:
            self.is_scanning = False

    def apply_detection_config(self, config):
        try:
            with self.lock:
                self.config['detection'].update(config)

                if 'zoneStart' in config:
                    self.zone_start_percent = config['zoneStart']
                if 'zoneWidth' in config:
                    self.zone_width_percent = config['zoneWidth']

                self.detector.set_detection_threshold(config.get('threshold', 0.5))
                self.detector.set_auto_count(config.get('autoCount', True))

                return True
        except Exception as e:
            print(f"Error applying detection config: {e}")
            return False

    def apply_visual_config(self, config):
        try:
            with self.lock:
                self.config['visual'].update(config)

                self.detector.set_show_boxes(config.get('showBoxes', True))
                self.detector.set_show_labels(config.get('showLabels', True))
                self.detector.set_show_confidence(config.get('showConfidence', True))
                self.detector.set_show_overlays(config.get('showOverlays', True))
                self.detector.set_show_all_detections(config.get('showAllDetections', False))
                self.detector.set_zone_color(config.get('zoneColor', '#ff0000'))
                self.detector.set_box_color(config.get('boxColor', '#00ff00'))
                self.detector.set_zone_opacity(config.get('zoneOpacity', 0.2))

                return True
        except Exception as e:
            print(f"Error applying visual config: {e}")
            return False

    def apply_advanced_config(self, config):
        try:
            with self.lock:
                self.config['advanced'].update(config)

                if 'resolution' in config:
                    self.detector.set_resolution(config['resolution'])
                if 'frameRate' in config:
                    self.detector.set_frame_rate(config['frameRate'])
                if 'model' in config:
                    self.detector.set_model(config['model'])
                if 'processingSpeed' in config:
                    self.detector.set_processing_speed(config['processingSpeed'])

                return True
        except Exception as e:
            print(f"Error applying advanced config: {e}")
            return False

    def apply_preset_config(self, preset_name):
        try:
            if preset_name in self.presets:
                preset = self.presets[preset_name]

                if 'detection' in preset:
                    self.apply_detection_config(preset['detection'])
                if 'visual' in preset:
                    self.apply_visual_config(preset['visual'])

                self.config['advanced']['preset'] = preset_name
                return True
            return False
        except Exception as e:
            print(f"Error applying preset config: {e}")
            return False

    def apply_full_config(self, config):
        try:
            success = True
            if 'detection' in config:
                success &= self.apply_detection_config(config['detection'])
            if 'visual' in config:
                success &= self.apply_visual_config(config['visual'])
            if 'advanced' in config:
                success &= self.apply_advanced_config(config['advanced'])
                # Handle camera switching if camera ID changed
                if 'cameraId' in config['advanced']:
                    self.handle_camera_change(config['advanced']['cameraId'])
            return success
        except Exception as e:
            print(f"Error applying full config: {e}")
            return False

    def save_config(self, config=None):
        try:
            config_to_save = config if config else self.config
            
            # Save to Firebase only
            if self.firestore_manager and self.firestore_manager.is_connected():
                success = self.firestore_manager.save_settings('app_config', config_to_save)
                return success
            else:
                return False
            
        except Exception as e:
            print(f"[ERROR] Error saving config: {e}")
            return False

    def load_config_from_sources(self):
        """Load config from Firebase only"""
        try:
            if self.firestore_manager and self.firestore_manager.is_connected():
                firebase_config = self.firestore_manager.load_settings('app_config')
                if firebase_config:
                    self.config.update(firebase_config)
                    self.apply_full_config(self.config)
                    return self.config
                else:
                    # Save current default config to Firebase
                    self.save_config()
                    return self.config
            else:
                return self.config
            
        except Exception as e:
            print(f"[ERROR] Error loading config from Firebase: {e}")
            print("⚠️ Config will remain default until Firebase connection succeeds")
            return self.config

    def reload_config_from_firebase(self):
        """Reload config from Firebase - for retry functionality"""
        return self.load_config_from_sources()

    def reset_config(self):
        try:
            default_config = {
                'detection': {
                    'zoneStart': 70,
                    'zoneWidth': 20,
                    'showZone': True,
                    'threshold': 0.5,
                    'autoCount': True
                },
                'visual': {
                    'showBoxes': True,
                    'showLabels': True,
                    'showConfidence': True,
                    'zoneColor': '#ff0000',
                    'boxColor': '#00ff00',
                    'zoneOpacity': 0.2
                },
                'advanced': {
                    'resolution': '640x480',
                    'frameRate': 30,
                    'model': 'yolov5s',
                    'processingSpeed': 'balanced',
                    'preset': 'retail'
                }
            }

            self.config = default_config
            self.apply_full_config(self.config)
            self.save_config()
            return True
        except Exception as e:
            print(f"Error resetting config: {e}")
            return False

    def get_current_config(self):
        return self.config.copy()

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

    def _find_matching_object(self, detection, label):
        best_match = None
        best_iou = 0.0
        threshold = 0.3

        for tracked_id, tracked_data in self.last_detections.items():
            if tracked_data['label'] != label:
                continue

            iou = self._calculate_iou(detection['box'], tracked_data['box'])
            if iou > threshold and iou > best_iou:
                best_iou = iou
                best_match = tracked_id

        return best_match

    def _cleanup_old_objects(self, current_time):
        to_remove = []
        for obj_id, last_time in list(self.last_detections.items()):
            if current_time - last_time['timestamp'] > self.object_timeout:
                to_remove.append(obj_id)

        for obj_id in to_remove:
            self.last_detections.pop(obj_id, None)
            self.objects_in_zone.pop(obj_id, None)

    def _process_simulated_objects(self, frame, frame_width, frame_height):
        current_time = time.time()
        detected_objects = []

        zone_mode = self.config['detection'].get('zoneMode', 'vertical')

        for obj_id, obj_data in self.simulated_objects.items():
            x = obj_data['x']
            y = obj_data['y']
            w = obj_data['width']
            h = obj_data['height']
            label = obj_data['label']

            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(frame_width, x + w)
            y2 = min(frame_height, y + h)
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            is_valid_product = label in self.product_manager.get_products()

            if self.config['visual']['showBoxes']:
                color = self._hex_to_bgr(self.config['visual']['boxColor']) if is_valid_product else (0, 165, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            if self.config['visual']['showLabels']:
                confidence_text = ": 1.00" if self.config['visual']['showConfidence'] else ""
                text = f"[SIM] {label}{confidence_text}"
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]

                text_bg_x1 = x1
                text_bg_y1 = y1 - 25 if y1 - 25 > 0 else 0
                text_bg_x2 = x1 + text_size[0] + 10
                text_bg_y2 = y1

                color = self._hex_to_bgr(self.config['visual']['boxColor']) if is_valid_product else (0, 165, 255)
                cv2.rectangle(frame, (text_bg_x1, text_bg_y1), (text_bg_x2, text_bg_y2), color, -1)
                if self.config['visual']['showOverlays']:
                    cv2.putText(frame, text, (x1 + 5, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            if is_valid_product:
                detected_objects.append({
                    'label': label,
                    'box': (x1, y1, x2, y2),
                    'center': (center_x, center_y),
                    'track_id': int(obj_id.split('_')[1]),  # Extract sim ID as track ID
                    'confidence': 1.0  # Simulation objects have perfect confidence
                })

            # Zone detection based on mode
            if zone_mode == 'vertical':
                counting_zone_x = int(frame_width * self.zone_start_percent / 100)
                counting_zone_width = int(frame_width * self.zone_width_percent / 100)
                in_zone = (center_x > counting_zone_x and
                           center_x < counting_zone_x + counting_zone_width)
            else:  # horizontal
                counting_zone_y = int(frame_height * self.zone_start_percent / 100)
                counting_zone_height = int(frame_height * self.zone_width_percent / 100)
                in_zone = (center_y > counting_zone_y and
                           center_y < counting_zone_y + counting_zone_height)

            was_in_zone = self.objects_in_zone.get(obj_id, False)
            already_counted = self.counted_objects.get(obj_id, False)

            if in_zone:
                if not was_in_zone and not already_counted and is_valid_product and self.config['detection']['autoCount']:
                    self.detector.add_to_cart(label)
                    self.counted_objects[obj_id] = True
                    pass

                self.objects_in_zone[obj_id] = True
                cv2.circle(frame, (center_x, center_y), 8, (0, 255, 255), -1)
            else:
                if was_in_zone:
                    self.counted_objects.pop(obj_id, None)
                self.objects_in_zone[obj_id] = False

        return frame, detected_objects

    def _hex_to_bgr(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))

    def _draw_zone_overlay(self, frame, frame_width, frame_height):
        if not self.config['detection']['showZone']:
            return frame

        zone_mode = self.config['detection'].get('zoneMode', 'vertical')
        zone_color = self._hex_to_bgr(self.config['visual']['zoneColor'])
        overlay = frame.copy()
        opacity = self.config['visual']['zoneOpacity']

        if zone_mode == 'vertical':
            # Vertical mode: left-right zones
            counting_zone_x = int(frame_width * self.zone_start_percent / 100)
            counting_zone_width = int(frame_width * self.zone_width_percent / 100)

            zone_start = (counting_zone_x, 0)
            zone_end = (counting_zone_x, frame_height)
            zone_end_right = (counting_zone_x + counting_zone_width, 0)
            zone_start_right = (counting_zone_x + counting_zone_width, frame_height)

            cv2.rectangle(overlay, (counting_zone_x, 0), (counting_zone_x + counting_zone_width, frame_height), zone_color, -1)
            cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)
            cv2.line(frame, zone_start, zone_end, zone_color, 2)
            cv2.line(frame, zone_end_right, zone_start_right, zone_color, 2)

            zone_text = "COUNTING ZONE (VERTIKAL)"
            text_size = cv2.getTextSize(zone_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            text_x = counting_zone_x + (counting_zone_width - text_size[0]) // 2
            text_y = 30
        else:
            # Horizontal mode: top-bottom zones
            counting_zone_y = int(frame_height * self.zone_start_percent / 100)
            counting_zone_height = int(frame_height * self.zone_width_percent / 100)

            zone_start = (0, counting_zone_y)
            zone_end = (frame_width, counting_zone_y)
            zone_end_bottom = (0, counting_zone_y + counting_zone_height)
            zone_start_bottom = (frame_width, counting_zone_y + counting_zone_height)

            cv2.rectangle(overlay, (0, counting_zone_y), (frame_width, counting_zone_y + counting_zone_height), zone_color, -1)
            cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)
            cv2.line(frame, zone_start, zone_end, zone_color, 2)
            cv2.line(frame, zone_end_bottom, zone_start_bottom, zone_color, 2)

            zone_text = "COUNTING ZONE (HORIZONTAL)"
            text_size = cv2.getTextSize(zone_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            text_x = (frame_width - text_size[0]) // 2
            text_y = counting_zone_y + (counting_zone_height + text_size[1]) // 2

        if self.config['visual']['showOverlays']:
            cv2.rectangle(frame, (text_x - 5, text_y - text_size[1] - 5),
                          (text_x + text_size[0] + 5, text_y + 5), zone_color, -1)
            cv2.putText(frame, zone_text, (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        return frame

    def process_frame(self, frame, frame_width, frame_height):
        if frame is None:
            return None  # Let web handle blank screen

        try:
            # Ensure frame is valid
            if len(frame.shape) != 3 or frame.shape[2] != 3:
                print(f"Invalid frame shape: {frame.shape}")
                return frame
            
            # Add timestamp and frame info for debugging
            debug_frame = frame.copy()
            if self.config['visual']['showOverlays']:
                cv2.putText(debug_frame, f"Live Feed: {frame_width}x{frame_height}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(debug_frame, f"Mode: {'SCAN' if self.is_scanning else 'READY'}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if self.is_scanning:
                self.detector.product_catalog = self.product_manager.get_products()
                self.detector.show_overlays = self.config['visual']['showOverlays']

                if self.simulation_mode:
                    processed_frame, detected_objects = self._process_simulated_objects(debug_frame, frame_width, frame_height)
                else:
                    processed_frame, detected_objects = self.detector.detect_objects(debug_frame)

                current_time = time.time()
                current_detections = {}
                zone_mode = self.config['detection'].get('zoneMode', 'vertical')

                for obj in detected_objects:
                    label = obj['label']
                    box = obj['box']
                    center_x = obj['center'][0]
                    center_y = obj['center'][1]

                    # Zone detection based on mode
                    if zone_mode == 'vertical':
                        counting_zone_x = int(frame_width * self.zone_start_percent / 100)
                        counting_zone_width = int(frame_width * self.zone_width_percent / 100)
                        in_zone = (center_x > counting_zone_x and
                                   center_x < counting_zone_x + counting_zone_width)
                    else:  # horizontal
                        counting_zone_y = int(frame_height * self.zone_start_percent / 100)
                        counting_zone_height = int(frame_height * self.zone_width_percent / 100)
                        in_zone = (center_y > counting_zone_y and
                                   center_y < counting_zone_y + counting_zone_height)

                    # Use tracking ID from SimpleTracker if available
                    track_id = obj.get('track_id')
                    if track_id is not None:
                        obj_id = f"{label}_track_{track_id}"
                    else:
                        # Fallback to old matching method
                        matched_id = self._find_matching_object(obj, label)
                        if matched_id:
                            obj_id = matched_id
                        else:
                            obj_id = f"{label}_{int(current_time * 1000)}_{len(current_detections)}"

                    current_detections[obj_id] = {
                        'label': label,
                        'box': box,
                        'center': obj['center'],
                        'timestamp': current_time,
                        'in_zone': in_zone,
                        'track_id': track_id
                    }

                    was_in_zone = self.objects_in_zone.get(obj_id, False)
                    already_counted = self.counted_objects.get(obj_id, False)

                    if in_zone:
                        if not was_in_zone and not already_counted and self.config['detection']['autoCount']:
                            # Use tracking ID for better duplicate prevention
                            if track_id is not None:
                                # Check if this track_id was already counted recently
                                track_key = f"track_{track_id}"
                                recent_tracks = {k: v for k, v in self.counted_objects.items() if track_key in k}
                                if not recent_tracks:
                                    self.detector.add_to_cart(label)
                                    self.counted_objects[obj_id] = True
                                    print(f"✅ Added {label} (Track ID: {track_id}) to cart")
                                else:
                                    print(f"⚠️ Track ID {track_id} already counted, skipping")
                            else:
                                # Fallback to old method
                                self.detector.add_to_cart(label)
                                self.counted_objects[obj_id] = True
                                print(f"✅ Added {label} (No Track ID) to cart")

                        self.objects_in_zone[obj_id] = True
                    else:
                        if was_in_zone and not track_id:
                            # Only remove non-tracked objects when exiting zone
                            self.counted_objects.pop(obj_id, None)
                        self.objects_in_zone[obj_id] = False

                self.last_detections = current_detections
                self._cleanup_old_objects(current_time)

            else:
                processed_frame = debug_frame.copy()

                if self.simulation_mode:
                    self._process_simulated_objects(processed_frame, frame_width, frame_height)

            processed_frame = self._draw_zone_overlay(processed_frame, frame_width, frame_height)
            
            # Add overlay text and zone
            if self.config['visual']['showOverlays']:
                mode_text = "🎮 SIMULATION MODE" if self.simulation_mode else "📹 REAL MODE"
                zone_mode = self.config['detection'].get('zoneMode', 'vertical')
                zone_text = "Vertikal" if zone_mode == 'vertical' else "Horizontal"
                settings_text = f"{mode_text} | Zone {zone_text}: {self.zone_start_percent}%, Size: {self.zone_width_percent}%"
                cv2.putText(processed_frame, settings_text, (10, frame_height - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                objects_in_zone_count = sum(1 for in_zone in self.objects_in_zone.values() if in_zone)
                tracking_text = f"Objects in zone: {objects_in_zone_count} | Simulated objects: {len(self.simulated_objects)}"
                cv2.putText(processed_frame, tracking_text, (10, frame_height - 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            return processed_frame
            
        except Exception as e:
            print(f"Error in process_frame: {e}")
            # Return None - let web handle blank screen
            return None

    def get_cart(self):
        return self.detector.get_cart()

    def calculate_total(self):
        return self.detector.calculate_total()

    def clear_cart(self):
        self.detector.clear_cart()
        self.objects_in_zone.clear()
        self.counted_objects.clear()
        self.last_detections.clear()

    # Camera management methods
    def get_available_cameras(self):
        """Get list of available cameras"""
        try:
            cameras = self.camera_manager.detect_available_cameras()
            return {
                'success': True,
                'cameras': cameras
            }
        except Exception as e:
            print(f"❌ Error getting available cameras: {e}")
            return {
                'success': False,
                'error': str(e),
                'cameras': []
            }

    def switch_camera(self, camera_id):
        """Switch to a different camera"""
        try:
            result = self.camera_manager.switch_camera(camera_id)
            if result['success']:
                # Update config to reflect the change
                self.config['advanced']['cameraId'] = camera_id
            return result
        except Exception as e:
            print(f"❌ Error switching camera: {e}")
            return {
                'success': False,
                'error': str(e),
                'camera_id': self.camera_manager.current_camera_id
            }

    def handle_camera_change(self, new_camera_id):
        """Handle camera change from config update"""
        current_id = self.camera_manager.current_camera_id
        if new_camera_id != current_id:
            return self.switch_camera(new_camera_id)
        return {'success': True, 'camera_id': current_id}

    def get_current_camera_info(self):
        """Get current camera information"""
        return self.camera_manager.get_current_camera_info()

    def initialize_camera_manager(self, camera_id=0):
        """Initialize camera manager with specified camera"""
        try:
            success = self.camera_manager.initialize_camera(camera_id)
            if success:
                self.config['advanced']['cameraId'] = camera_id
            return success
        except Exception as e:
            print(f"❌ Error initializing camera manager: {e}")
            return False

    def remove_item(self, product_name):
        with self.lock:
            cart = self.detector.get_cart()
            product_lower = product_name.lower()

            if product_lower in cart:
                if cart[product_lower]["quantity"] > 1:
                    cart[product_lower]["quantity"] -= 1
                    return True
                else:
                    del cart[product_lower]
                    return True

            return False

    def change_model(self, model_path):
        """Change the current YOLO model"""
        try:
            with self.lock:
                # Stop scanning if active
                was_scanning = self.is_scanning
                if was_scanning:
                    self.stop_scanning()
                
                # Create new detector with new model
                from ProductDetector import ProductDetector
                new_detector = ProductDetector(model_path=model_path)
                
                # Replace old detector
                old_detector = self.detector
                self.detector = new_detector
                
                # Clean up old detector if needed
                del old_detector
                
                # Update config to reflect current model
                if 'advanced' not in self.config:
                    self.config['advanced'] = {}
                self.config['advanced']['model'] = model_path
                
                # Save updated config to Firebase and local file
                self.save_config()
                
                # Clear detection state
                self.clear_cart()
                
                # Resume scanning if it was active
                if was_scanning:
                    self.start_scanning()
                
                return True
                
        except Exception as e:
            print(f"[ERROR] Failed to change model: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_current_model(self):
        """Get the current model path"""
        return self.config.get('advanced', {}).get('model', 'unknown')
    
    def get_model_labels(self):
        """Get available labels from the current model"""
        try:
            if self.detector and self.detector.model:
                return self.detector.get_model_labels()
            else:
                return []
        except Exception as e:
            print(f"[ERROR] Failed to get model labels: {e}")
            import traceback
            traceback.print_exc()
            return []
