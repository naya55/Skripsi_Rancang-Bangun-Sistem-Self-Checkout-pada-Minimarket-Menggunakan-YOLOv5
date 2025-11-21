from flask import Flask, Response, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS
import threading
import time
import numpy as np
import os
import cv2
import datetime
import json
import logging
from dotenv import load_dotenv

load_dotenv()

from DetectorManager import DetectorManager
from ProductManager import ProductManager
from FirestoreManager import FirestoreManager
from VideoStreamer import VideoStreamer
from StreamingServer import StreamingServer
from PaymentManager import PaymentManager


def format_transaction_for_json(transaction):
    formatted_transaction = transaction.copy()

    if 'timestamp' in formatted_transaction and formatted_transaction['timestamp']:
        timestamp = formatted_transaction['timestamp']
        if hasattr(timestamp, 'isoformat'):
            formatted_transaction['timestamp'] = timestamp.isoformat()
        elif hasattr(timestamp, 'timestamp'):
            formatted_transaction['timestamp'] = timestamp.timestamp()

    return formatted_transaction


class SelfCheckoutApp:
    def __init__(self):
        self.host = os.getenv('FLASK_HOST', '127.0.0.1')
        self.port = int(os.getenv('FLASK_PORT', 5002))
        self.debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
        self.secret_key = os.getenv('FLASK_SECRET_KEY', 'self-checkout-secret-key')
        
        # Rate limiting for socket events to prevent payload overflow
        self.last_emit_times = {}
        self.emit_rate_limit = 0.1  # Minimum 100ms between same event types
        
        cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3002,http://127.0.0.1:3002').split(',')
        
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = self.secret_key
        
        CORS(self.app, origins=cors_origins)
        
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins=cors_origins,
            async_mode='threading',
            logger=False,  # Disable verbose logging
            engineio_logger=False,  # Disable engine.io logging
            max_http_buffer_size=10**8,  # 100MB buffer size for large payloads
            ping_timeout=60,  # 60 seconds ping timeout
            ping_interval=25,  # 25 seconds ping interval
            engineio_options={
                'max_decode_packets': 500,  # Allow more packets per payload
                'max_encode_packets': 500,  # Allow more packets per payload
                'compression_threshold': 1024  # Compress messages larger than 1KB
            }
        )
        
        self.firestore_manager = FirestoreManager(os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json'))
        self.product_manager = ProductManager(self.firestore_manager)
        
        # Camera manager integrated with detector (ONLY camera system)
        self.detector_manager = DetectorManager(
            model_path=os.getenv('MODEL_PATH', 'models/yolov5s.pt'), 
            product_manager=self.product_manager,
            firestore_manager=self.firestore_manager
        )
        
        # Initialize camera manager with default camera
        initial_camera_id = int(os.getenv('CAMERA_ID', 0))
        self.detector_manager.initialize_camera_manager(initial_camera_id)
        
        # Initialize PaymentManager
        try:
            self.payment_manager = PaymentManager()
            print(f"✅ PaymentManager initialized for {self.payment_manager.environment} environment")
        except Exception as e:
            print(f"❌ Failed to initialize PaymentManager: {str(e)}")
            self.payment_manager = None
        
        self.video_streamer = VideoStreamer()
        self.streaming_server = StreamingServer()
        self.processing_thread = None
        self.is_processing = False
        self.camera_enabled = False  # Camera starts off by default
        self.yolo_initialized = False
        self.yolo_initializing = False
        self.last_transaction_request = 0  # Throttle transaction requests
        # Simplified camera control - no Model Tab state needed

        self.register_routes()
        self.register_socket_events()
        
        # Initialize YOLO in background thread on startup
        self._initialize_yolo_on_startup()

    def register_routes(self):
        @self.app.route('/')
        def index():
            return jsonify({
                'message': 'Self-Checkout API Server',
                'status': 'running',
                'version': '1.0.0',
                'endpoints': {
                    'video_feed': '/video_feed',
                    'socket': '/socket.io'
                }
            })

        @self.app.route('/api/health')
        def health_check():
            return jsonify({
                'status': 'healthy',
                'camera': self.detector_manager.camera_manager.is_active() if self.detector_manager.camera_manager else False,
                'firestore': self.firestore_manager.is_connected(),
                'products_count': len(self.product_manager.get_products())
            })

        @self.app.route('/video_feed')
        def video_feed():
            try:
                return Response(
                    self.video_streamer.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0',
                        'Connection': 'keep-alive',
                        'Access-Control-Allow-Origin': '*'
                    }
                )
            except Exception as e:
                print(f"Video feed error: {e}")
                return Response(
                    "Video feed error",
                    status=500,
                    mimetype='text/plain'
                )

        @self.app.route('/video_stream')
        def video_stream():
            """Proper MJPEG video stream for video element"""
            try:
                return Response(
                    self.streaming_server.generate_mjpeg_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={
                        'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
                        'Pragma': 'no-cache',
                        'Expires': '0',
                        'Connection': 'keep-alive',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    }
                )
            except Exception as e:
                print(f"Video stream error: {e}")
                return Response("Stream error", status=500)

        @self.app.route('/api/models', methods=['GET'])
        def get_models_api():
            """REST API endpoint for getting available models"""
            print("🌐 REST API /api/models endpoint called")
            try:
                # Get absolute path to models directory
                script_dir = os.path.dirname(os.path.abspath(__file__))
                models_dir = os.path.join(script_dir, 'models')
                available_models = []
                
                print(f"[API] REST API - Models directory: {models_dir}")
                print(f"[API] REST API - Directory exists: {os.path.exists(models_dir)}")
                
                if os.path.exists(models_dir):
                    files = os.listdir(models_dir)
                    print(f"[API] REST API - Files in directory: {files}")
                    
                    # Get all .pt files in models directory
                    for filename in files:
                        if filename.endswith('.pt'):
                            # Get full path to model file
                            full_model_path = os.path.join(models_dir, filename)
                            # Use relative path for model_path (for compatibility)
                            model_path = f"models/{filename}"
                            file_size = os.path.getsize(full_model_path)
                            
                            # Format file size
                            if file_size > 1024 * 1024:
                                size_str = f"{file_size / (1024 * 1024):.1f} MB"
                            else:
                                size_str = f"{file_size / 1024:.1f} KB"
                            
                            model_info = {
                                'filename': filename,
                                'path': model_path,
                                'size': size_str,
                                'display_name': filename.replace('.pt', '').replace('_', ' ').title()
                            }
                            available_models.append(model_info)
                            print(f"[API] REST API - Found model: {model_info}")
                else:
                    print(f"[ERROR] REST API - Models directory does not exist: {models_dir}")
                
                # Sort by filename
                available_models.sort(key=lambda x: x['filename'])
                
                response = {
                    'success': True,
                    'models': available_models
                }
                print(f"[API] REST API - Sending response: {response}")
                return jsonify(response)
                
            except Exception as e:
                error_msg = f"Error getting available models: {e}"
                print(f"[ERROR] REST API - {error_msg}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'models': []
                })

        # ======================== PAYMENT API ENDPOINTS ========================
        
        @self.app.route('/api/payment/create', methods=['POST'])
        def create_payment():
            """Create Midtrans Snap payment token"""
            try:
                if not self.payment_manager:
                    return jsonify({
                        'success': False,
                        'error': 'Payment system not available',
                        'error_type': 'payment_system_unavailable'
                    }), 503
                
                # Get request data
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'No request data provided',
                        'error_type': 'invalid_request_data'
                    }), 400
                
                # Validate required fields
                required_fields = ['items', 'total']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            'success': False,
                            'error': f'Missing required field: {field}',
                            'error_type': 'missing_required_field'
                        }), 400
                
                # Generate transaction ID if not provided
                if 'transaction_id' not in data:
                    data['transaction_id'] = f"TXN_{int(time.time())}"
                
                # Create payment token
                result = self.payment_manager.create_payment_token(data)
                
                if result['success']:
                    # Store transaction data in Firebase with payment info
                    try:
                        transaction_data = {
                            'transaction_id': data['transaction_id'],
                            'items': data['items'],
                            'total': data['total'],
                            'payment': {
                                'order_id': result['order_id'],
                                'snap_token': result['snap_token'],
                                'payment_url': result['payment_url'],
                                'status': 'pending',
                                'created_at': datetime.datetime.now().isoformat(),
                                'expires_at': result['expiry_time'],
                                'environment': result['environment']
                            },
                            'status': 'payment_pending',
                            'created_at': datetime.datetime.now().isoformat()
                        }
                        
                        # Save to Firebase
                        self.firestore_manager.add_transaction(transaction_data)
                        
                        pass
                        
                        # Emit to frontend via Socket.IO
                        self.socketio.emit('payment_created', {
                            'transaction_id': data['transaction_id'],
                            'order_id': result['order_id'],
                            'snap_token': result['snap_token'],
                            'payment_url': result['payment_url'],
                            'qr_code_url': result.get('qr_code_url', ''),
                            'expires_at': result['expiry_time']
                        })
                        
                    except Exception as e:
                        print(f"Warning: Failed to save transaction to Firebase: {str(e)}")
                    
                    return jsonify(result), 200
                else:
                    return jsonify(result), 400
                    
            except Exception as e:
                error_msg = f"Error creating payment: {str(e)}"
                print(f"❌ {error_msg}")
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'error_type': 'payment_creation_error'
                }), 500
        
        @self.app.route('/api/payment/status/<order_id>', methods=['GET'])
        def check_payment_status(order_id):
            """Check payment status from Midtrans"""
            try:
                if not self.payment_manager:
                    return jsonify({
                        'success': False,
                        'error': 'Payment system not available'
                    }), 503
                
                result = self.payment_manager.check_payment_status(order_id)
                return jsonify(result), 200 if result['success'] else 400
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'error_type': 'status_check_error'
                }), 500
        
        @self.app.route('/api/payment/webhook', methods=['POST'])
        def payment_webhook():
            """Handle Midtrans payment notification webhook"""
            try:
                if not self.payment_manager:
                    return jsonify({'status': 'error', 'message': 'Payment system not available'}), 503
                
                # Get notification data
                notification_data = request.get_json()
                if not notification_data:
                    notification_data = request.form.to_dict()
                
                # Get signature from headers
                signature_key = request.headers.get('X-Midtrans-Signature')
                
                # Verify signature if available
                if signature_key:
                    is_valid = self.payment_manager.verify_webhook_signature(
                        json.dumps(notification_data), 
                        signature_key
                    )
                    if not is_valid:
                        print(f"❌ Invalid webhook signature for order_id: {notification_data.get('order_id')}")
                        return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
                
                # Process notification
                result = self.payment_manager.process_webhook_notification(notification_data)
                
                if result['success']:
                    order_id = result['order_id']
                    transaction_status = result['transaction_status']
                    
                    print(f"📨 Webhook received: {order_id} -> {transaction_status}")
                    
                    # Update transaction in Firebase
                    try:
                        # Get existing transaction data
                        transactions = self.firestore_manager.get_transactions()
                        transaction_to_update = None
                        
                        for txn in transactions:
                            if txn.get('payment', {}).get('order_id') == order_id:
                                transaction_to_update = txn
                                break
                        
                        if transaction_to_update:
                            # Update payment status
                            transaction_to_update['payment']['status'] = transaction_status
                            transaction_to_update['payment']['updated_at'] = datetime.datetime.now().isoformat()
                            transaction_to_update['payment']['webhook_data'] = notification_data
                            
                            # Update overall transaction status
                            if result['payment_successful']:
                                transaction_to_update['status'] = 'completed'
                                transaction_to_update['completed_at'] = datetime.datetime.now().isoformat()
                            elif result['payment_failed']:
                                transaction_to_update['status'] = 'failed'
                            elif result['payment_pending']:
                                transaction_to_update['status'] = 'payment_pending'
                            
                            # Save updated transaction
                            self.firestore_manager.update_transaction(transaction_to_update)
                            
                    except Exception as e:
                        print(f"Warning: Failed to update transaction in Firebase: {str(e)}")
                    
                    # Emit real-time update via Socket.IO
                    self.socketio.emit('payment_status_update', {
                        'order_id': order_id,
                        'transaction_status': transaction_status,
                        'payment_successful': result['payment_successful'],
                        'payment_pending': result['payment_pending'],
                        'payment_failed': result['payment_failed'],
                        'payment_type': result.get('payment_type', ''),
                        'gross_amount': result.get('gross_amount', ''),
                        'transaction_time': result.get('transaction_time', ''),
                        'settlement_time': result.get('settlement_time', ''),
                        'custom_field1': result.get('custom_field1', ''),  # Original transaction_id
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    
                    # If payment successful, emit completion event
                    if result['payment_successful']:
                        self.socketio.emit('payment_completed', {
                            'order_id': order_id,
                            'transaction_id': result.get('custom_field1', ''),
                            'payment_type': result.get('payment_type', ''),
                            'gross_amount': result.get('gross_amount', ''),
                            'message': 'Payment completed successfully'
                        })
                    
                    return jsonify({'status': 'ok'}), 200
                else:
                    return jsonify({'status': 'error', 'message': result['error']}), 400
                    
            except Exception as e:
                error_msg = f"Webhook processing error: {str(e)}"
                print(f"❌ {error_msg}")
                return jsonify({'status': 'error', 'message': error_msg}), 500
        
        @self.app.route('/api/payment/cancel/<order_id>', methods=['POST'])
        def cancel_payment(order_id):
            """Cancel pending payment"""
            try:
                if not self.payment_manager:
                    return jsonify({
                        'success': False,
                        'error': 'Payment system not available'
                    }), 503
                
                result = self.payment_manager.cancel_payment(order_id)
                
                if result['success']:
                    # Emit cancellation event
                    self.socketio.emit('payment_cancelled', {
                        'order_id': order_id,
                        'message': 'Payment cancelled successfully'
                    })
                
                return jsonify(result), 200 if result['success'] else 400
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'error_type': 'cancellation_error'
                }), 500
        
        # Payment methods endpoint removed - now configured via enabled_payments parameter
        
        @self.app.route('/api/payment/config', methods=['GET'])
        def get_payment_config():
            """Get payment configuration info"""
            try:
                if not self.payment_manager:
                    return jsonify({
                        'success': False,
                        'error': 'Payment system not available'
                    }), 503
                
                config = self.payment_manager.get_environment_info()
                return jsonify({
                    'success': True,
                    'config': config
                }), 200
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # ======================== END PAYMENT ENDPOINTS ========================

        @self.app.route('/api/debug/routes')
        def debug_routes():
            """Debug endpoint to show all registered routes"""
            routes = []
            for rule in self.app.url_map.iter_rules():
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods),
                    'rule': str(rule)
                })
            return jsonify({'routes': routes})

        @self.app.route('/current_frame')
        def current_frame():
            """Single frame response"""
            try:
                frame_data = self.streaming_server.generate_single_frame()
                if frame_data is None:
                    return Response("Frame generation failed", status=500)
                
                response = Response(
                    frame_data,
                    mimetype='image/jpeg',
                    headers={
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0',
                        'Access-Control-Allow-Origin': '*'
                    }
                )
                return response
                
            except Exception as e:
                print(f"Current frame error: {e}")
                return Response("Frame error", status=500)

        @self.app.route('/debug')
        def debug_info():
            """Debug endpoint untuk check backend status"""
            try:
                camera_info = self.detector_manager.get_current_camera_info()
                return jsonify({
                    'camera_available': camera_info['status'] == 'active',
                    'camera_running': camera_info['status'] == 'active',
                    'processing_active': self.is_processing,
                    'frame_count': getattr(self.streaming_server, 'frame_count', 0),
                    'video_streamer_active': self.video_streamer.is_active,
                    'simulation_mode': self.detector_manager.simulation_mode,
                    'detector_scanning': self.detector_manager.is_scanning,
                    'timestamp': time.time()
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/test_stream')
        def test_stream():
            """Test page untuk debug streaming"""
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Video Stream Test</title>
                <style>
                    body { font-family: Arial; margin: 20px; background: #f0f0f0; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .test-section { margin: 20px 0; padding: 20px; background: white; border-radius: 8px; }
                    video, img, iframe { max-width: 100%; height: 300px; border: 2px solid #ccc; }
                    .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
                    .success { background: #d4edda; color: #155724; }
                    .error { background: #f8d7da; color: #721c24; }
                    button { padding: 10px 20px; margin: 5px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🔍 Video Stream Debug Test</h1>
                    
                    <div class="test-section">
                        <h3>1. Backend Status</h3>
                        <div id="status">Loading...</div>
                        <button onclick="checkStatus()">Refresh Status</button>
                    </div>
                    
                    <div class="test-section">
                        <h3>2. Native Video Element Test</h3>
                        <video id="nativeVideo" autoplay muted playsinline controls>
                            <source src="/video_stream" type="multipart/x-mixed-replace">
                            Your browser does not support video streaming.
                        </video>
                        <div id="videoStatus" class="status">Waiting...</div>
                    </div>
                    
                    <div class="test-section">
                        <h3>3. IMG Tag Test (Single Frame)</h3>
                        <img id="imgTest" src="/current_frame" alt="Single frame test">
                        <div id="imgStatus" class="status">Loading...</div>
                        <button onclick="refreshImage()">Refresh Image</button>
                    </div>
                    
                    <div class="test-section">
                        <h3>4. Iframe Test (MJPEG)</h3>
                        <iframe id="iframeTest" src="/video_feed"></iframe>
                        <div id="iframeStatus" class="status">Loading...</div>
                    </div>
                </div>

                <script>
                async function checkStatus() {
                    try {
                        const response = await fetch('/debug');
                        const data = await response.json();
                        document.getElementById('status').innerHTML = 
                            '<div class="success"><pre>' + JSON.stringify(data, null, 2) + '</pre></div>';
                    } catch (error) {
                        document.getElementById('status').innerHTML = 
                            '<div class="error">Error: ' + error.message + '</div>';
                    }
                }

                function refreshImage() {
                    const img = document.getElementById('imgTest');
                    img.src = '/current_frame?t=' + Date.now();
                }

                // Video event listeners
                const video = document.getElementById('nativeVideo');
                video.addEventListener('loadstart', () => {
                    document.getElementById('videoStatus').innerHTML = '<div class="status">Video loading started...</div>';
                });
                video.addEventListener('canplay', () => {
                    document.getElementById('videoStatus').innerHTML = '<div class="success">✅ Video can play!</div>';
                });
                video.addEventListener('error', (e) => {
                    document.getElementById('videoStatus').innerHTML = '<div class="error">❌ Video error: ' + e.message + '</div>';
                });
                video.addEventListener('stalled', () => {
                    document.getElementById('videoStatus').innerHTML = '<div class="error">⚠️ Video stalled</div>';
                });

                // Image event listeners
                document.getElementById('imgTest').addEventListener('load', () => {
                    document.getElementById('imgStatus').innerHTML = '<div class="success">✅ Image loaded</div>';
                });
                document.getElementById('imgTest').addEventListener('error', () => {
                    document.getElementById('imgStatus').innerHTML = '<div class="error">❌ Image failed to load</div>';
                });

                // Auto-refresh status every 5 seconds
                setInterval(checkStatus, 5000);
                checkStatus();
                </script>
            </body>
            </html>
            '''

    def register_socket_events(self):
        @self.socketio.on('connect')
        def handle_connect():
            print('Client connected')
            # Send current states to client
            camera_info = self.detector_manager.get_current_camera_info()
            self.socketio.emit('camera_status', {
                'enabled': self.camera_enabled,
                'available': camera_info['status'] == 'active'
            })
            self.socketio.emit('yolo_status', {
                'initialized': self.yolo_initialized,
                'initializing': self.yolo_initializing,
                'model_path': self.detector_manager.get_current_model() if self.detector_manager else None
            })
            
            # Send current camera status to help with debugging
            camera_info = self.detector_manager.get_current_camera_info()
            print(f"Client connected - Camera status: {camera_info['status']}, ID: {camera_info.get('id', 'None')}")
            self.socketio.emit('camera_info', {
                'success': True,
                'camera': camera_info
            })

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('Client disconnected')

        @self.socketio.on('start_scanning')
        def handle_start_scanning(data):
            try:
                # Simplified scanning - no Model Tab blocking needed
                
                # Apply detection config from frontend data
                if data and isinstance(data, dict):
                    print(f"📥 Received detection config from frontend: {data}")
                    # Apply the full detection config sent from frontend
                    success = self.detector_manager.apply_detection_config(data)
                    if success:
                        pass
                    else:
                        print("❌ Failed to apply detection config from frontend")
                else:
                    print("⚠️ No detection config provided - using current saved config")
                
                if not self.is_processing:
                    self.start_processing()
                
                self.detector_manager.start_scanning()
                
                # Send confirmation back to frontend
                current_config = self.detector_manager.get_current_config()
                self.socketio.emit('scanning_started', {
                    'success': True,
                    'config': current_config['detection']
                })
                
            except Exception as e:
                print(f"[ERROR] Error starting scanning: {e}")
                self.socketio.emit('scanning_started', {
                    'success': False,
                    'error': str(e)
                })

        @self.socketio.on('stop_scanning')
        def handle_stop_scanning():
            self.detector_manager.stop_scanning()
            self.socketio.emit('scanning_complete', {
                'cart': self.detector_manager.get_cart(),
                'total': self.detector_manager.calculate_total()
            })
            print("Scanning stopped")

        @self.socketio.on('update_zone')
        def handle_update_zone(data):
            self.detector_manager.set_zone_parameters(data['zone_start'], data['zone_width'])
            print(f"Zone updated - start: {data['zone_start']}%, width: {data['zone_width']}%")

        @self.socketio.on('clear_cart')
        def handle_clear_cart():
            self.detector_manager.clear_cart()
            self.socketio.emit('cart_update', {
                'cart': {},
                'total': 0
            })
            print("Cart cleared")

        @self.socketio.on('remove_item')
        def handle_remove_item(data):
            result = self.detector_manager.remove_item(data['name'])
            if result:
                self.socketio.emit('cart_update', {
                    'cart': self.detector_manager.get_cart(),
                    'total': self.detector_manager.calculate_total()
                })
                self.socketio.emit('item_removed', {
                    'success': True,
                    'name': data['name']
                })
                print(f"Removed item: {data['name']} from cart")
            else:
                self.socketio.emit('item_removed', {
                    'success': False,
                    'name': data['name']
                })
                print(f"Failed to remove item: {data['name']} (not found)")

        @self.socketio.on('checkout_complete')
        def handle_checkout_complete(data=None):
            cart = self.detector_manager.get_cart()
            total = self.detector_manager.calculate_total()

            if self.firestore_manager.is_connected():
                transaction = self.firestore_manager.save_transaction(cart, total)
                if transaction:
                    print(f"Transaction saved to Firestore with IDs: {transaction['transaction_ids']}")

            # Clear cart
            self.detector_manager.clear_cart()
            self.socketio.emit('cart_update', {
                'cart': {},
                'total': 0
            })
            
            # Show camera overlay after checkout (hide camera view)
            self.socketio.emit('camera_overlay', {
                'show': True,
                'message': 'Checkout berhasil! Kamera disembunyikan'
            })
            
            print("Checkout completed - cart cleared and overlay shown")

        @self.socketio.on('get_products')
        def handle_get_products():
            products = self.product_manager.get_products()
            self.socketio.emit('products_list', products)

        @self.socketio.on('add_product')
        def handle_add_product(data):
            result = self.product_manager.add_product(data['name'], data['price'])
            self.socketio.emit('product_added', result)
            print(f"Added product: {result['name']} - Rp {result['price']}")

        @self.socketio.on('update_product')
        def handle_update_product(data):
            result = self.product_manager.update_product(data['name'], data['price'])
            if result:
                self.socketio.emit('product_updated', result)
                print(f"Updated product: {result['name']} - Rp {result['price']}")

        @self.socketio.on('delete_product')
        def handle_delete_product(data):
            result = self.product_manager.delete_product(data['name'])
            if result:
                self.socketio.emit('product_deleted', result)
                print(f"Deleted product: {result['name']}")

        @self.socketio.on('delete_all_products')
        def handle_delete_all_products():
            result = self.product_manager.delete_all_products()
            self.socketio.emit('all_products_deleted', result)
            print(f"Deleted all products: {result['deleted_count']} products removed")

        @self.socketio.on('get_transaction_history')
        def handle_get_transaction_history(data=None):
            # Throttle requests - only allow one every 2 seconds
            current_time = time.time()
            if current_time - self.last_transaction_request < 2.0:
                print("Transaction history request throttled")
                return
            
            self.last_transaction_request = current_time
            
            if not self.firestore_manager.is_connected():
                self.socketio.emit('transaction_history', [])
                return

            limit = data.get('limit', 20) if data else 20
            transactions = self.firestore_manager.get_transactions(limit=limit)

            formatted_transactions = []
            for transaction in transactions:
                formatted_transaction = format_transaction_for_json(transaction)

                if formatted_transaction.get('timestamp'):
                    timestamp = transaction.get('timestamp')
                    if hasattr(timestamp, 'strftime'):
                        # Convert to WIB timezone (GMT+7)
                        wib_timestamp = self.firestore_manager.convert_to_wib(timestamp)
                        formatted_transaction['formatted_date'] = wib_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        formatted_transaction['formatted_date'] = str(timestamp)

                formatted_transactions.append(formatted_transaction)

            self.socketio.emit('transaction_history', formatted_transactions)
            print(f"Sent {len(formatted_transactions)} transactions to client")

        @self.socketio.on('get_transactions_by_date')
        def handle_get_transactions_by_date(data):
            if not self.firestore_manager.is_connected():
                self.socketio.emit('transaction_history', [])
                return

            start_date = data.get('start_date')
            end_date = data.get('end_date')

            if not start_date or not end_date:
                transactions = self.firestore_manager.get_transactions()
            else:
                transactions = self.firestore_manager.get_transactions_by_date_range(start_date, end_date)

            formatted_transactions = []
            for transaction in transactions:
                formatted_transaction = format_transaction_for_json(transaction)

                if formatted_transaction.get('timestamp'):
                    timestamp = transaction.get('timestamp')
                    if hasattr(timestamp, 'strftime'):
                        # Convert to WIB timezone (GMT+7)
                        wib_timestamp = self.firestore_manager.convert_to_wib(timestamp)
                        formatted_transaction['formatted_date'] = wib_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        formatted_transaction['formatted_date'] = str(timestamp)

                formatted_transactions.append(formatted_transaction)

            self.socketio.emit('transaction_history', formatted_transactions)
            print(f"Sent {len(formatted_transactions)} transactions by date range to client")

        @self.socketio.on('delete_transaction')
        def handle_delete_transaction(data):
            if not self.firestore_manager.is_connected():
                self.socketio.emit('transaction_deleted', {
                    'success': False,
                    'message': 'Firestore not connected'
                })
                return

            transaction_id = data.get('id')
            if not transaction_id:
                self.socketio.emit('transaction_deleted', {
                    'success': False,
                    'message': 'No transaction ID provided'
                })
                return

            result = self.firestore_manager.delete_transaction(transaction_id)
            if result:
                self.socketio.emit('transaction_deleted', {
                    'success': True,
                    'id': transaction_id
                })
                print(f"Deleted transaction with ID: {transaction_id}")
            else:
                self.socketio.emit('transaction_deleted', {
                    'success': False,
                    'message': 'Failed to delete transaction'
                })

        @self.socketio.on('delete_all_transactions')
        def handle_delete_all_transactions():
            if not self.firestore_manager.is_connected():
                self.socketio.emit('all_transactions_deleted', {
                    'success': False,
                    'message': 'Firestore not connected'
                })
                return

            result = self.firestore_manager.delete_all_transactions()
            self.socketio.emit('all_transactions_deleted', {
                'success': True,
                'deleted_count': result['deleted_count']
            })
            print(f"Deleted all transactions: {result['deleted_count']} transactions removed")

        @self.socketio.on('toggle_simulation')
        def handle_toggle_simulation(data):
            enabled = data.get('enabled', False)
            self.detector_manager.toggle_simulation_mode(enabled)
            self.socketio.emit('simulation_toggled', {
                'enabled': enabled,
                'message': 'Simulation mode enabled' if enabled else 'Real detection mode enabled'
            })
            print(f"Simulation mode: {'ON' if enabled else 'OFF'}")

        @self.socketio.on('add_simulated_object')
        def handle_add_simulated_object(data):
            label = data.get('label', 'person')
            x = int(data.get('x', 100))
            y = int(data.get('y', 100))
            width = int(data.get('width', 100))
            height = int(data.get('height', 100))

            obj_id = self.detector_manager.add_simulated_object(label, x, y, width, height)

            self.socketio.emit('simulated_object_added', {
                'success': True,
                'obj_id': obj_id,
                'label': label,
                'x': x,
                'y': y,
                'width': width,
                'height': height
            })
            print(f"Added simulated object: {label} at ({x}, {y})")

        @self.socketio.on('update_simulated_object')
        def handle_update_simulated_object(data):
            obj_id = data.get('obj_id')
            x = data.get('x')
            y = data.get('y')
            width = data.get('width')
            height = data.get('height')
            label = data.get('label')

            success = self.detector_manager.update_simulated_object(
                obj_id, x=x, y=y, width=width, height=height, label=label
            )

            self.socketio.emit('simulated_object_updated', {
                'success': success,
                'obj_id': obj_id
            })

            if success:
                print(f"Updated simulated object {obj_id}")

        @self.socketio.on('remove_simulated_object')
        def handle_remove_simulated_object(data):
            obj_id = data.get('obj_id')
            success = self.detector_manager.remove_simulated_object(obj_id)

            self.socketio.emit('simulated_object_removed', {
                'success': success,
                'obj_id': obj_id
            })

            if success:
                print(f"Removed simulated object {obj_id}")

        @self.socketio.on('get_simulated_objects')
        def handle_get_simulated_objects():
            objects = self.detector_manager.get_simulated_objects()
            self.socketio.emit('simulated_objects_list', objects)

        @self.socketio.on('move_simulated_object')
        def handle_move_simulated_object(data):
            obj_id = data.get('obj_id')
            direction = data.get('direction')
            step = data.get('step', 10)

            objects = self.detector_manager.get_simulated_objects()
            if obj_id in objects:
                obj = objects[obj_id]
                x, y = obj['x'], obj['y']

                if direction == 'left':
                    x = max(0, x - step)
                elif direction == 'right':
                    x = min(600, x + step)
                elif direction == 'up':
                    y = max(0, y - step)
                elif direction == 'down':
                    y = min(400, y + step)

                self.detector_manager.update_simulated_object(obj_id, x=x, y=y)

                self.socketio.emit('simulated_object_moved', {
                    'success': True,
                    'obj_id': obj_id,
                    'x': x,
                    'y': y
                })

        @self.socketio.on('preset_move_to_zone')
        def handle_preset_move_to_zone(data):
            obj_id = data.get('obj_id')

            frame_width = 640
            zone_start_percent = self.detector_manager.zone_start_percent
            zone_width_percent = self.detector_manager.zone_width_percent

            counting_zone_x = int(frame_width * zone_start_percent / 100)
            counting_zone_width = int(frame_width * zone_width_percent / 100)
            zone_center_x = counting_zone_x + (counting_zone_width // 2)

            y_pos = 150

            success = self.detector_manager.update_simulated_object(
                obj_id, x=zone_center_x - 50, y=y_pos
            )

            self.socketio.emit('simulated_object_moved_to_zone', {
                'success': success,
                'obj_id': obj_id,
                'x': zone_center_x - 50,
                'y': y_pos
            })

            if success:
                print(f"Moved simulated object {obj_id} to counting zone")

        @self.socketio.on('simulate_conveyor_movement')
        def handle_simulate_conveyor_movement(data):
            obj_id = data.get('obj_id')
            speed = data.get('speed', 5)

            self.socketio.emit('conveyor_simulation_started', {
                'obj_id': obj_id,
                'speed': speed
            })

            print(f"Started conveyor simulation for {obj_id}")

        @self.socketio.on('update_detection_config')
        def handle_update_detection_config(data):
            success = self.detector_manager.apply_detection_config(data)
            if success:
                # Save updated config to Firebase and local file
                self.detector_manager.save_config()
                pass
            
            self.socketio.emit('config_updated', {
                'success': success,
                'type': 'detection',
                'config': data
            })

        @self.socketio.on('update_visual_config')
        def handle_update_visual_config(data):
            success = self.detector_manager.apply_visual_config(data)
            if success:
                # Save updated config to Firebase and local file
                self.detector_manager.save_config()
                pass
            
            self.socketio.emit('config_updated', {
                'success': success,
                'type': 'visual',
                'config': data
            })

        @self.socketio.on('update_advanced_config')
        def handle_update_advanced_config(data):
            success = self.detector_manager.apply_advanced_config(data)
            if success:
                # Save updated config to Firebase and local file
                self.detector_manager.save_config()
                pass
            
            self.socketio.emit('config_updated', {
                'success': success,
                'type': 'advanced',
                'config': data
            })

        @self.socketio.on('apply_preset_config')
        def handle_apply_preset_config(data):
            preset = data
            success = self.detector_manager.apply_preset_config(preset)
            if success:
                # Save updated config to Firebase and local file
                self.detector_manager.save_config()
                pass
            
            self.socketio.emit('config_applied', {
                'success': success,
                'preset': preset
            })

        @self.socketio.on('apply_full_config')
        def handle_apply_full_config(data):
            success = self.detector_manager.apply_full_config(data)
            if success:
                # Save updated config to Firebase and local file
                self.detector_manager.save_config()
                pass
            
            self.socketio.emit('config_applied', {
                'success': success,
                'config': data
            })

        @self.socketio.on('save_config')
        def handle_save_config(data):
            success = self.detector_manager.save_config(data)
            self.socketio.emit('config_saved', {
                'success': success
            })
            if success:
                print("Configuration saved")

        @self.socketio.on('test_event')
        def handle_test_event(data):
            self.socketio.emit('test_event', {'message': 'Backend test response'})

        @self.socketio.on('get_available_models')
        def handle_get_available_models():
            """Get list of available model files from models directory"""
            pass
            try:
                # Get absolute path to models directory
                script_dir = os.path.dirname(os.path.abspath(__file__))
                models_dir = os.path.join(script_dir, 'models')
                available_models = []
                
                print(f"📁 Script directory: {script_dir}")
                print(f"📁 Models directory: {models_dir}")
                print(f"📂 Directory exists: {os.path.exists(models_dir)}")
                print(f"📂 Current working directory: {os.getcwd()}")
                
                if os.path.exists(models_dir):
                    files = os.listdir(models_dir)
                    print(f"📄 Files in directory: {files}")
                    
                    # Get all .pt files in models directory
                    for filename in files:
                        if filename.endswith('.pt'):
                            # Get full path to model file
                            full_model_path = os.path.join(models_dir, filename)
                            # Use relative path for model_path (for compatibility)
                            model_path = f"models/{filename}"
                            file_size = os.path.getsize(full_model_path)
                            
                            # Format file size
                            if file_size > 1024 * 1024:
                                size_str = f"{file_size / (1024 * 1024):.1f} MB"
                            else:
                                size_str = f"{file_size / 1024:.1f} KB"
                            
                            model_info = {
                                'filename': filename,
                                'path': model_path,
                                'size': size_str,
                                'display_name': filename.replace('.pt', '').replace('_', ' ').title()
                            }
                            available_models.append(model_info)
                            pass
                else:
                    print(f"❌ Models directory does not exist: {models_dir}")
                
                # Sort by filename
                available_models.sort(key=lambda x: x['filename'])
                
                response = {
                    'success': True,
                    'models': available_models
                }
                pass
                self.socketio.emit('available_models', response)
                pass
                
            except Exception as e:
                error_msg = f"Error getting available models: {e}"
                print(f"❌ {error_msg}")
                self.socketio.emit('available_models', {
                    'success': False,
                    'error': str(e),
                    'models': []
                })

        @self.socketio.on('change_model')
        def handle_change_model(data):
            """Change the current model"""
            print(f"[SOCKET] Received change_model request: {data}")
            try:
                model_path = data.get('model_path')
                print(f"[SOCKET] Model path requested: {model_path}")
                
                if not model_path:
                    error_msg = 'No model path provided'
                    print(f"[ERROR] {error_msg}")
                    self.socketio.emit('model_changed', {
                        'success': False,
                        'error': error_msg
                    })
                    return
                
                # Check if file exists
                print(f"[SOCKET] Checking if model file exists: {model_path}")
                if not os.path.exists(model_path):
                    error_msg = f'Model file not found: {model_path}'
                    print(f"[ERROR] {error_msg}")
                    self.socketio.emit('model_changed', {
                        'success': False,
                        'error': error_msg
                    })
                    return
                
                print(f"[SOCKET] Model file exists, attempting to change model...")
                
                # Update detector manager with new model
                success = self.detector_manager.change_model(model_path)
                print(f"[SOCKET] Model change result: {success}")
                
                response = {
                    'success': success,
                    'model_path': model_path if success else None,
                    'error': None if success else 'Failed to load model'
                }
                
                print(f"[SOCKET] Sending model_changed response: {response}")
                self.socketio.emit('model_changed', response)
                
                if success:
                    print(f"[SUCCESS] Model successfully changed to: {model_path}")
                else:
                    print(f"[ERROR] Failed to change model to: {model_path}")
                    
            except Exception as e:
                error_msg = f"Error changing model: {e}"
                print(f"[EXCEPTION] Exception in change_model: {error_msg}")
                import traceback
                traceback.print_exc()
                
                self.socketio.emit('model_changed', {
                    'success': False,
                    'error': str(e)
                })

        @self.socketio.on('get_model_labels')
        def handle_get_model_labels():
            """Get labels/classes from the currently loaded model"""
            try:
                # Get labels from detector manager
                labels = self.detector_manager.get_model_labels()
                
                self.socketio.emit('model_labels', {
                    'success': len(labels) > 0,
                    'labels': labels,
                    'count': len(labels),
                    'error': None if len(labels) > 0 else "No labels found in model"
                })
                
            except Exception as e:
                print(f"[ERROR] Error getting model labels: {e}")
                import traceback
                traceback.print_exc()
                
                self.socketio.emit('model_labels', {
                    'success': False,
                    'error': str(e),
                    'labels': []
                })

        @self.socketio.on('load_config')
        def handle_load_config():
            config = self.detector_manager.load_config_from_sources()
            firebase_connected = self.firestore_manager.is_connected() if self.firestore_manager else False
            
            self.socketio.emit('config_loaded', {
                'success': config is not None,
                'config': config,
                'firebase_connected': firebase_connected
            })
            

        @self.socketio.on('reload_config')
        def handle_reload_config():
            """Reload config from Firebase - for retry functionality"""
            try:
                config = self.detector_manager.reload_config_from_firebase()
                firebase_connected = self.firestore_manager.is_connected() if self.firestore_manager else False
                
                self.socketio.emit('config_reloaded', {
                    'success': firebase_connected and config is not None,
                    'config': config,
                    'firebase_connected': firebase_connected,
                    'message': 'Config reloaded from Firebase' if firebase_connected else 'Firebase connection failed'
                })
                
                    
            except Exception as e:
                print(f"[ERROR] Error reloading config: {e}")
                self.socketio.emit('config_reloaded', {
                    'success': False,
                    'config': None,
                    'firebase_connected': False,
                    'error': str(e),
                    'message': f'Failed to reload config: {e}'
                })

        @self.socketio.on('reset_config')
        def handle_reset_config():
            success = self.detector_manager.reset_config()
            self.socketio.emit('config_reset', {
                'success': success
            })
            if success:
                print("Configuration reset to defaults")

        @self.socketio.on('toggle_camera')
        def handle_toggle_camera(data):
            enabled = data.get('enabled', False)
            
            # Simplified camera toggle - no Model Tab blocking needed
            
            if enabled:
                # Simple camera enable - just start processing if not already started
                if not self.is_processing:
                    self.start_processing()
            else:
                # Auto-stop scanning when camera is disabled
                if self.detector_manager.is_scanning:
                    self.detector_manager.stop_scanning()
            
            # Control overlay visibility
            self.socketio.emit('camera_overlay', {
                'show': not enabled,  # Show overlay when "camera disabled"
                'message': 'Kamera dimatikan' if not enabled else 'Kamera dihidupkan'
            })

        @self.socketio.on('initialize_yolo')
        def handle_initialize_yolo():
            if not self.yolo_initialized and not self.yolo_initializing:
                self._initialize_yolo()

        # ======================== CAMERA SOCKET.IO EVENTS ========================
        
        @self.socketio.on('get_available_cameras')
        def handle_get_available_cameras():
            """Get list of available cameras"""
            try:
                result = self.detector_manager.get_available_cameras()
                self.socketio.emit('available_cameras', result)
                pass
            except Exception as e:
                print(f"❌ Error getting available cameras: {e}")
                self.socketio.emit('available_cameras', {
                    'success': False,
                    'error': str(e),
                    'cameras': []
                })

        @self.socketio.on('switch_camera')
        def handle_switch_camera(data):
            """Switch to a different camera"""
            try:
                camera_id = data.get('camera_id')
                if camera_id is None:
                    self.socketio.emit('camera_switched', {
                        'success': False,
                        'error': 'Camera ID is required'
                    })
                    return

                print(f"🔄 Starting camera switch to Camera {camera_id}")
                
                # Stop processing first to avoid conflicts during switch
                if self.is_processing:
                    print("🔄 Stopping processing for camera switch...")
                    self.stop_processing()
                    time.sleep(0.5)  # Wait for processing to stop completely
                
                result = self.detector_manager.switch_camera(camera_id)
                
                # Restart processing if switch successful
                if result['success'] and not self.is_processing:
                    print("🔄 Restarting processing after successful camera switch...")
                    self.start_processing()
                
                # Emit result to client
                self.socketio.emit('camera_switched', result)
                
                if result['success']:
                    pass
                else:
                    print(f"❌ Camera switch failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ Error in switch_camera handler: {e}")
                self.socketio.emit('camera_switched', {
                    'success': False,
                    'error': str(e)
                })

        @self.socketio.on('get_camera_info')
        def handle_get_camera_info():
            """Get current camera information"""
            try:
                camera_info = self.detector_manager.get_current_camera_info()
                self.socketio.emit('camera_info', {
                    'success': True,
                    'camera': camera_info
                })
            except Exception as e:
                print(f"❌ Error getting camera info: {e}")
                self.socketio.emit('camera_info', {
                    'success': False,
                    'error': str(e)
                })


        @self.socketio.on('initialize_camera')
        def handle_initialize_camera(data):
            """Initialize camera with specified ID"""
            try:
                camera_id = data.get('camera_id', 1)
                print(f"🔄 Starting camera initialization for Camera {camera_id}")
                
                # Stop processing first to avoid conflicts
                if self.is_processing:
                    print("🔄 Stopping processing for camera switch...")
                    self.stop_processing()
                    time.sleep(0.5)  # Wait for processing to stop
                
                # Initialize camera with detailed error reporting
                success = self.detector_manager.initialize_camera_manager(camera_id)
                
                if success:
                    print(f"✅ Camera {camera_id} initialized successfully")
                    
                    # Start video processing
                    print("🔄 Starting video processing...")
                    self.start_processing()
                    
                    self.socketio.emit('camera_initialized', {
                        'success': True,
                        'camera_id': camera_id,
                        'message': f'Camera {camera_id} initialized successfully'
                    })
                else:
                    # Get more specific error information from camera manager
                    error_msg = f'Failed to initialize camera {camera_id}'
                    if (self.detector_manager and 
                        self.detector_manager.camera_manager and 
                        hasattr(self.detector_manager.camera_manager, 'current_camera') and
                        self.detector_manager.camera_manager.current_camera is None):
                        error_msg += ' - Camera may be in use by another application or not accessible'
                    
                    print(f"❌ {error_msg}")
                    self.socketio.emit('camera_initialized', {
                        'success': False,
                        'camera_id': camera_id,
                        'error': error_msg
                    })
                    
            except Exception as e:
                print(f"❌ Error initializing camera: {e}")
                self.socketio.emit('camera_initialized', {
                    'success': False,
                    'error': str(e)
                })

        # ======================== SIMPLIFIED CAMERA CONTROL ========================
        
        @self.socketio.on('kill_camera_for_config')
        def handle_kill_camera_for_config():
            """SIMPLE: Kill camera immediately when configuration opens"""
            try:
                print("🔴 KILLING CAMERA FOR CONFIGURATION - no matter what state")
                
                # Force kill camera completely
                if self.detector_manager and self.detector_manager.camera_manager:
                    self.detector_manager.camera_manager.release_camera()
                    print("🔴 Camera released successfully")
                
                # Stop video processing
                if self.is_processing:
                    self.stop_processing()
                    print("🔴 Video processing stopped")
                
                # Emit success response
                self.socketio.emit('camera_killed_for_config', {
                    'success': True,
                    'message': 'Camera killed for configuration'
                })
                
            except Exception as e:
                print(f"❌ Error killing camera for config: {e}")
                self.socketio.emit('camera_killed_for_config', {
                    'success': False,
                    'error': str(e)
                })

        # ======================== MODEL TAB CAMERA MANAGEMENT (SIMPLIFIED) ========================
        # The Model Tab now uses the same simple camera control as the configuration system


    def processing_loop(self):
        frame_count = 0
        last_process_time = time.time()
        skip_frames = 0
        
        while self.is_processing:
            try:
                # Processing loop simplified - no Model Tab state check needed
                
                frame_count += 1
                current_time = time.time()
                
                # Check camera status less frequently to reduce overhead
                if frame_count % 1000 == 0:
                    camera_info = self.detector_manager.get_current_camera_info()
                
                processed_frame = None
                
                # Use camera manager for frame reading
                success, frame = self.detector_manager.camera_manager.read_frame()
                
                if success and frame is not None:
                    # Frame skipping when processing is behind (target: ~30 FPS = 0.033s per frame)
                    time_since_last = current_time - last_process_time
                    if time_since_last < 0.025:  # If processing faster than 40 FPS, occasionally skip
                        skip_frames += 1
                        if skip_frames >= 2:  # Skip every 2nd frame when too fast
                            skip_frames = 0
                            continue
                    else:
                        skip_frames = 0  # Reset skip counter if processing is slow
                    
                    # Get frame dimensions from the frame itself
                    frame_height, frame_width = frame.shape[:2]
                    processed_frame = self.detector_manager.process_frame(frame, frame_width, frame_height)
                    self.video_streamer.update_frame(processed_frame)
                    self.streaming_server.update_frame(processed_frame)  # Feed to streaming server
                    
                    last_process_time = current_time
                    
                    # Only emit cart updates during scanning to reduce socket overhead
                    if self.detector_manager.is_scanning and frame_count % 3 == 0:  # Reduce cart update frequency
                        self.socketio.emit('cart_update', {
                            'cart': self.detector_manager.get_cart(),
                            'total': self.detector_manager.calculate_total()
                        })
                else:
                    # Camera read failed - reduce error checking frequency
                    if frame_count % 500 == 0:  # Check errors less frequently
                        camera_info = self.detector_manager.get_current_camera_info()
                        print(f"❌ Camera read failed - Camera status: {camera_info['status']}, ID: {camera_info.get('id', 'None')}")
                        
                        # Try to reinitialize camera if it's not active
                        if camera_info['status'] != 'active':
                            current_camera_id = self.detector_manager.config['advanced'].get('cameraId', 0)
                            pass
                            self.detector_manager.initialize_camera_manager(current_camera_id)
                    
                    # No frame creation needed - web handles blank screen for both simulation and error modes
                    pass
                
                # Emit frame via Socket.IO for real-time streaming
                if processed_frame is not None:
                    self._emit_frame_via_socket(processed_frame)
                
                time.sleep(0.033)  # 30 FPS for real-time feel
                
            except Exception as e:
                print(f"Processing error: {e}")
                # No error frame needed - web handles blank screen
                time.sleep(0.1)

    # REMOVED: No error frame creation - web handles blank screen
    
    # REMOVED: All frame creation functions - web handles blank screen
    
    def _emit_frame_via_socket(self, frame):
        """Emit frame via Socket.IO as base64 encoded JPEG"""
        try:
            # Encode frame to JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 75]  # Lower quality for faster transmission
            success, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            if success:
                # Convert to base64 string
                import base64
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Emit to all connected clients
                self.socketio.emit('video_frame', {
                    'frame': frame_base64,
                    'timestamp': time.time(),
                    'width': frame.shape[1],
                    'height': frame.shape[0]
                })
            
        except Exception as e:
            print(f"Error emitting frame via socket: {e}")

        # ======================== PAYMENT SOCKET.IO EVENTS ========================
        
        @self.socketio.on('create_payment')
        def handle_create_payment(data):
            """Create payment via Socket.IO"""
            try:
                if not self.payment_manager:
                    self.socketio.emit('payment_error', {
                        'error': 'Payment system not available',
                        'error_type': 'payment_system_unavailable'
                    })
                    return
                
                # Validate required fields
                if not data or 'items' not in data or 'total' not in data:
                    self.socketio.emit('payment_error', {
                        'error': 'Missing required payment data (items, total)',
                        'error_type': 'invalid_payment_data'
                    })
                    return
                
                # Generate transaction ID if not provided
                if 'transaction_id' not in data:
                    data['transaction_id'] = f"TXN_{int(time.time())}"
                
                pass
                
                # Create payment token
                result = self.payment_manager.create_payment_token(data)
                
                if result['success']:
                    # Store transaction data in Firebase
                    try:
                        transaction_data = {
                            'transaction_id': data['transaction_id'],
                            'items': data['items'],
                            'total': data['total'],
                            'payment': {
                                'order_id': result['order_id'],
                                'snap_token': result['snap_token'],
                                'payment_url': result['payment_url'],
                                'status': 'pending',
                                'created_at': datetime.datetime.now().isoformat(),
                                'expires_at': result['expiry_time'],
                                'environment': result['environment']
                            },
                            'status': 'payment_pending',
                            'created_at': datetime.datetime.now().isoformat()
                        }
                        
                        self.firestore_manager.add_transaction(transaction_data)
                        pass
                        
                    except Exception as e:
                        print(f"Warning: Failed to save transaction to Firebase: {str(e)}")
                    
                    # Emit success to frontend
                    self.socketio.emit('payment_created', {
                        'success': True,
                        'transaction_id': data['transaction_id'],
                        'order_id': result['order_id'],
                        'snap_token': result['snap_token'],
                        'payment_url': result['payment_url'],
                        'qr_code_url': result.get('qr_code_url', ''),
                        'expires_at': result['expiry_time'],
                        'environment': result['environment']
                    })
                    
                    pass
                    
                else:
                    self.socketio.emit('payment_error', {
                        'error': result['error'],
                        'error_type': result.get('error_type', 'payment_creation_failed'),
                        'transaction_id': data.get('transaction_id')
                    })
                    print(f"❌ Payment creation failed: {result['error']}")
                    
            except Exception as e:
                error_msg = f"Error creating payment: {str(e)}"
                print(f"❌ {error_msg}")
                self.socketio.emit('payment_error', {
                    'error': error_msg,
                    'error_type': 'payment_creation_exception',
                    'transaction_id': data.get('transaction_id') if data else None
                })
        
        @self.socketio.on('check_payment_status')
        def handle_check_payment_status(data):
            """Check payment status via Socket.IO"""
            try:
                if not self.payment_manager:
                    self.socketio.emit('payment_status_error', {
                        'error': 'Payment system not available'
                    })
                    return
                
                if not data or 'order_id' not in data:
                    self.socketio.emit('payment_status_error', {
                        'error': 'Missing order_id'
                    })
                    return
                
                order_id = data['order_id']
                result = self.payment_manager.check_payment_status(order_id)
                
                if result['success']:
                    self.socketio.emit('payment_status_checked', {
                        'success': True,
                        'order_id': order_id,
                        'transaction_status': result['transaction_status'],
                        'payment_type': result.get('payment_type', ''),
                        'gross_amount': result.get('gross_amount', ''),
                        'transaction_time': result.get('transaction_time', ''),
                        'settlement_time': result.get('settlement_time', '')
                    })
                else:
                    self.socketio.emit('payment_status_error', {
                        'error': result['error'],
                        'order_id': order_id
                    })
                    
            except Exception as e:
                self.socketio.emit('payment_status_error', {
                    'error': str(e),
                    'order_id': data.get('order_id') if data else None
                })
        
        @self.socketio.on('cancel_payment')
        def handle_cancel_payment(data):
            """Cancel payment via Socket.IO"""
            try:
                if not self.payment_manager:
                    self.socketio.emit('payment_cancel_error', {
                        'error': 'Payment system not available'
                    })
                    return
                
                if not data or 'order_id' not in data:
                    self.socketio.emit('payment_cancel_error', {
                        'error': 'Missing order_id'
                    })
                    return
                
                order_id = data['order_id']
                result = self.payment_manager.cancel_payment(order_id)
                
                if result['success']:
                    self.socketio.emit('payment_cancelled', {
                        'success': True,
                        'order_id': order_id,
                        'message': 'Payment cancelled successfully'
                    })
                    pass
                else:
                    self.socketio.emit('payment_cancel_error', {
                        'error': result['error'],
                        'order_id': order_id
                    })
                    
            except Exception as e:
                self.socketio.emit('payment_cancel_error', {
                    'error': str(e),
                    'order_id': data.get('order_id') if data else None
                })
        
        # Socket.IO payment methods handler removed - now configured via enabled_payments parameter
        
        @self.socketio.on('get_payment_config')
        def handle_get_payment_config():
            """Get payment configuration via Socket.IO"""
            try:
                if not self.payment_manager:
                    self.socketio.emit('payment_config_error', {
                        'error': 'Payment system not available'
                    })
                    return
                
                config = self.payment_manager.get_environment_info()
                self.socketio.emit('payment_config', {
                    'success': True,
                    'config': config
                })
                
            except Exception as e:
                self.socketio.emit('payment_config_error', {
                    'error': str(e)
                })
        
        # ======================== END PAYMENT SOCKET.IO EVENTS ========================

    def _initialize_yolo(self):
        """Initialize YOLO model in a separate thread"""
        def init_yolo():
            try:
                self.yolo_initializing = True
                self.socketio.emit('yolo_status', {
                    'initialized': False,
                    'initializing': True,
                    'model_path': self.detector_manager.get_current_model() if self.detector_manager else None
                })
                
                print("Initializing YOLO model...")
                # The detector manager initialization includes YOLO loading
                # This is already done in __init__, but we need to ensure it's ready
                if hasattr(self.detector_manager, 'detector'):
                    # Force model initialization if not already done
                    success = True
                    print("YOLO model initialized successfully")
                else:
                    success = False
                    print("Failed to initialize YOLO model")
                
                self.yolo_initialized = success
                self.yolo_initializing = False
                
                self.socketio.emit('yolo_status', {
                    'initialized': success,
                    'initializing': False,
                    'model_path': self.detector_manager.get_current_model() if self.detector_manager else None
                })
                
                if success:
                    pass
                else:
                    print("❌ YOLO initialization failed")
                    
            except Exception as e:
                print(f"Error initializing YOLO: {e}")
                self.yolo_initialized = False
                self.yolo_initializing = False
                self.socketio.emit('yolo_status', {
                    'initialized': False,
                    'initializing': False,
                    'error': str(e),
                    'model_path': self.detector_manager.get_current_model() if self.detector_manager else None
                })
        
        # Run initialization in background thread
        init_thread = threading.Thread(target=init_yolo)
        init_thread.daemon = True
        init_thread.start()

    def _initialize_yolo_on_startup(self):
        """Initialize YOLO model automatically on app startup"""
        def init_yolo_startup():
            # Wait a bit for app to fully initialize
            time.sleep(2)
            print("🚀 Starting background YOLO initialization...")
            
            try:
                self.yolo_initializing = True
                
                # Initialize the actual YOLO model in detector manager
                if hasattr(self.detector_manager, 'detector') and hasattr(self.detector_manager.detector, 'load_model'):
                    self.detector_manager.detector.load_model()
                    pass
                    self.yolo_initialized = True
                else:
                    print("❌ Failed to load YOLO model")
                    self.yolo_initialized = False
                    
            except Exception as e:
                print(f"❌ Background YOLO initialization error: {e}")
                self.yolo_initialized = False
            finally:
                self.yolo_initializing = False
                pass
                
                # Auto-start processing if camera is already enabled
                camera_info = self.detector_manager.get_current_camera_info()
                if self.yolo_initialized and self.camera_enabled and camera_info['status'] == 'active' and not self.is_processing:
                    pass
                    self.start_processing()
        
        # Run in background thread
        startup_thread = threading.Thread(target=init_yolo_startup)
        startup_thread.daemon = True
        startup_thread.start()

    def emit_with_rate_limit(self, event_name, data=None, namespace=None):
        """Emit socket event with rate limiting to prevent payload overflow"""
        current_time = time.time()
        
        # Check if enough time has passed since last emit of this event type
        if event_name in self.last_emit_times:
            time_diff = current_time - self.last_emit_times[event_name]
            if time_diff < self.emit_rate_limit:
                # Skip this emit if too soon
                return
        
        # Update last emit time and emit the event
        self.last_emit_times[event_name] = current_time
        self.socketio.emit(event_name, data, namespace=namespace)

    def start_processing(self):
        if self.is_processing:
            return
        
        # Simplified processing - no Model Tab blocking needed
            
        self.is_processing = True
        self.processing_thread = threading.Thread(target=self.processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        print("Video processing started")

    def stop_processing(self):
        print("🔧 Stopping processing completely...")
        self.is_processing = False
        print(f"🔧 is_processing set to: {self.is_processing}")
        
        if self.processing_thread:
            print("🔧 Joining processing thread...")
            self.processing_thread.join(timeout=1.0)
            self.processing_thread = None
            print("🔧 Processing thread stopped")
        
        # Legacy camera code removed - only using detector_manager.camera_manager now
        
        if hasattr(self, 'video_streamer') and self.video_streamer:
            print("🔧 Stopping video streamer...")
            self.video_streamer.stop()
            print("🔧 Video streamer stopped")

    def run(self):
        print(f"Starting Self-Checkout API Server on {self.host}:{self.port}")
        print(f"Environment: {os.getenv('NODE_ENV', 'development')}")
        print(f"Frontend should be running on http://localhost:{os.getenv('PORT', 3002)}")
        print(f"Video feed available at http://{self.host}:{self.port}/video_feed")
        
        # Print all registered routes for debugging
        print("\n[ROUTES] Registered routes:")
        for rule in self.app.url_map.iter_rules():
            methods = ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
            print(f"  {methods:10} {rule}")
        print()
        
        # Initialize video streamer without fallback frames
        
        # Initialize YOLO model first
        print("Starting YOLO initialization...")
        self._initialize_yolo()
        
        # Auto-start camera when backend starts (always running in background)
        pass
        
        # Initialize CameraManager with default camera (NO legacy camera)
        initial_camera_id = int(os.getenv('CAMERA_ID', 0))
        camera_manager_started = self.detector_manager.initialize_camera_manager(initial_camera_id)
        
        if camera_manager_started:
            pass
            # Show overlay by default at startup
            self.socketio.emit('camera_overlay', {
                'show': True,
                'message': 'Kamera menyala di background - tampil overlay putih default'
            })
        elif camera_manager_started:
            pass
            self.socketio.emit('camera_overlay', {
                'show': True,
                'message': 'Kamera menyala di background - tampil overlay putih default'
            })
        else:
            print("❌ Failed to auto-start both camera systems - web will handle blank screen")
        
        # Start processing loop
        self.start_processing()
        
        try:
            # Disable auto-reloading to prevent double initialization and blocking
            self.socketio.run(
                self.app, 
                host=self.host, 
                port=self.port, 
                debug=self.debug, 
                use_reloader=False,  # Disable auto-reloading
                allow_unsafe_werkzeug=True
            )
        finally:
            self.stop_processing()


if __name__ == '__main__':
    model_dir = os.getenv('MODEL_PATH', 'models/yolov5s.pt').split('/')[0]
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        print(f"Created '{model_dir}' directory")
        print("Please run 'python DownloadModel.py' to download YOLOv5 model")
    
    app = SelfCheckoutApp()
    app.run()