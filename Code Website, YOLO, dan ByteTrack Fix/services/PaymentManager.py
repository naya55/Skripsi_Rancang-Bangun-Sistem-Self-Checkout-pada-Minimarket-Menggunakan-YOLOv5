#!/usr/bin/env python3
"""
PaymentManager.py
Midtrans Payment Integration Service for Self-Checkout System

Handles:
- Snap token generation
- Payment status tracking
- Webhook notification processing
- Transaction verification
"""

import os
import json
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import midtransclient
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentManager:
    """
    Comprehensive payment management using Midtrans Snap API
    Supports sandbox/production toggle via environment variables
    """
    
    def __init__(self):
        """Initialize PaymentManager dengan Midtrans configuration"""
        self.environment = os.getenv('MIDTRANS_ENVIRONMENT', 'sandbox')
        self.is_production = self.environment == 'production'
        
        # Load appropriate keys based on environment
        if self.is_production:
            self.server_key = os.getenv('MIDTRANS_SERVER_KEY_PRODUCTION')
            self.client_key = os.getenv('MIDTRANS_CLIENT_KEY_PRODUCTION')
            self.api_url = os.getenv('MIDTRANS_API_URL_PRODUCTION', 'https://app.midtrans.com')
        else:
            self.server_key = os.getenv('MIDTRANS_SERVER_KEY_SANDBOX')
            self.client_key = os.getenv('MIDTRANS_CLIENT_KEY_SANDBOX')
            self.api_url = os.getenv('MIDTRANS_API_URL_SANDBOX', 'https://app.sandbox.midtrans.com')
        
        # Payment configuration
        self.timeout_minutes = int(os.getenv('PAYMENT_TIMEOUT_MINUTES', 10))
        self.webhook_url = os.getenv('PAYMENT_WEBHOOK_URL')
        self.success_url = os.getenv('PAYMENT_SUCCESS_URL')
        self.error_url = os.getenv('PAYMENT_ERROR_URL')
        self.pending_url = os.getenv('PAYMENT_PENDING_URL')
        
        # Validate required configuration
        if not self.server_key or not self.client_key:
            raise ValueError(f"Missing Midtrans API keys for {self.environment} environment")
        
        # Initialize Midtrans Snap client
        try:
            self.snap = midtransclient.Snap(
                is_production=self.is_production,
                server_key=self.server_key,
                client_key=self.client_key
            )
            logger.info(f"PaymentManager initialized for {self.environment} environment")
        except Exception as e:
            logger.error(f"Failed to initialize Midtrans client: {str(e)}")
            raise
    
    def generate_order_id(self, transaction_id: str = None) -> str:
        """
        Generate unique order ID untuk Midtrans
        Format: ORDER_TIMESTAMP_TXNID
        """
        timestamp = int(time.time())
        if transaction_id:
            return f"ORDER_{timestamp}_{transaction_id}"
        return f"ORDER_{timestamp}"
    
    def create_payment_token(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Midtrans Snap token untuk payment
        
        Args:
            transaction_data: {
                'transaction_id': str,
                'items': List[Dict],
                'total': int,
                'customer': Dict (optional)
            }
        
        Returns:
            Dict dengan snap_token, redirect_url, order_id
        """
        try:
            # Generate unique order ID
            order_id = self.generate_order_id(transaction_data.get('transaction_id'))
            
            # Calculate expiry time
            expiry_time = datetime.now() + timedelta(minutes=self.timeout_minutes)
            
            # Prepare customer details
            customer_details = transaction_data.get('customer', {
                'first_name': 'Self Checkout',
                'last_name': 'Customer',
                'email': 'customer@selfcheckout.com',
                'phone': '+62812345678'
            })
            
            # Prepare transaction parameters for Midtrans
            transaction_params = {
                'transaction_details': {
                    'order_id': order_id,
                    'gross_amount': int(transaction_data['total'])
                },
                'item_details': [
                    {
                        'id': str(item.get('product_id', item.get('id', f'item_{idx}')))[:50],
                        'price': int(item['price']),
                        'quantity': int(item['quantity']),
                        'name': str(item['name'])[:50],  # Midtrans has length limits
                        'category': 'retail'
                    }
                    for idx, item in enumerate(transaction_data['items'])
                ],
                'customer_details': {
                    'first_name': customer_details.get('first_name', 'Customer')[:20],
                    'last_name': customer_details.get('last_name', '')[:20],
                    'email': customer_details.get('email', 'customer@selfcheckout.com'),
                    'phone': customer_details.get('phone', '+62812345678')
                },
                'credit_card': {
                    'secure': True
                },
                'callbacks': {
                    'finish': self.success_url,
                    'error': self.error_url,
                    'pending': self.pending_url
                },
                'expiry': {
                    'duration': self.timeout_minutes,
                    'unit': 'minutes'
                },
                'enabled_payments': self.get_enabled_payment_methods(),
                'custom_field1': transaction_data.get('transaction_id', ''),
                'custom_field2': 'self_checkout_system',
                'custom_field3': self.environment
            }
            
            # Create transaction dengan Midtrans
            logger.info(f"Creating payment token for order_id: {order_id}")
            transaction_result = self.snap.create_transaction(transaction_params)
            
            # Extract result
            snap_token = transaction_result['token']
            redirect_url = transaction_result['redirect_url']
            
            logger.info(f"Payment token created successfully: {order_id}")
            
            return {
                'success': True,
                'order_id': order_id,
                'snap_token': snap_token,
                'redirect_url': redirect_url,
                'expiry_time': expiry_time.isoformat(),
                'payment_url': f"{self.api_url}/snap/v2/vtweb/{snap_token}",
                'qr_code_url': f"{self.api_url}/snap/v1/transactions/{order_id}/qr-code",
                'environment': self.environment,
                'gross_amount': transaction_params['transaction_details']['gross_amount']
            }
            
        except Exception as e:
            logger.error(f"Error creating payment token: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'payment_creation_failed'
            }
    
    def check_payment_status(self, order_id: str) -> Dict[str, Any]:
        """
        Check payment status dari Midtrans
        
        Args:
            order_id: Midtrans order ID
            
        Returns:
            Dict dengan payment status information
        """
        try:
            # Get transaction status dari Midtrans
            status_response = self.snap.transactions.status(order_id)
            
            return {
                'success': True,
                'order_id': order_id,
                'transaction_id': status_response.get('transaction_id'),
                'payment_type': status_response.get('payment_type'),
                'transaction_status': status_response.get('transaction_status'),
                'fraud_status': status_response.get('fraud_status'),
                'status_code': status_response.get('status_code'),
                'gross_amount': status_response.get('gross_amount'),
                'transaction_time': status_response.get('transaction_time'),
                'settlement_time': status_response.get('settlement_time', ''),
                'status_message': status_response.get('status_message', ''),
                'raw_response': status_response
            }
            
        except Exception as e:
            logger.error(f"Error checking payment status for {order_id}: {str(e)}")
            return {
                'success': False,
                'order_id': order_id,
                'error': str(e),
                'error_type': 'status_check_failed'
            }
    
    def verify_webhook_signature(self, notification_body: str, signature_key: str) -> bool:
        """
        Verify Midtrans webhook notification signature
        
        Args:
            notification_body: Raw notification body
            signature_key: Signature dari Midtrans header
            
        Returns:
            Boolean indicating signature validity
        """
        try:
            # Parse notification data
            notification_data = json.loads(notification_body) if isinstance(notification_body, str) else notification_body
            
            # Create signature string
            order_id = notification_data.get('order_id', '')
            status_code = notification_data.get('status_code', '')
            gross_amount = notification_data.get('gross_amount', '')
            
            signature_string = f"{order_id}{status_code}{gross_amount}{self.server_key}"
            
            # Calculate expected signature
            calculated_signature = hashlib.sha512(signature_string.encode('utf-8')).hexdigest()
            
            # Compare signatures
            is_valid = hmac.compare_digest(calculated_signature, signature_key)
            
            if not is_valid:
                logger.warning(f"Invalid webhook signature for order_id: {order_id}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    def process_webhook_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook notification dari Midtrans
        
        Args:
            notification_data: Notification payload dari Midtrans
            
        Returns:
            Dict dengan processed notification information
        """
        try:
            order_id = notification_data.get('order_id')
            transaction_status = notification_data.get('transaction_status')
            payment_type = notification_data.get('payment_type')
            fraud_status = notification_data.get('fraud_status', 'accept')
            
            logger.info(f"Processing webhook for order_id: {order_id}, status: {transaction_status}")
            
            # Determine payment result
            payment_successful = (
                transaction_status == 'settlement' or
                (transaction_status == 'capture' and fraud_status == 'accept')
            )
            
            payment_pending = transaction_status in ['pending', 'challenge']
            payment_failed = transaction_status in ['cancel', 'deny', 'expire', 'failure']
            
            # Prepare processed result
            processed_notification = {
                'success': True,
                'order_id': order_id,
                'transaction_id': notification_data.get('transaction_id'),
                'payment_type': payment_type,
                'transaction_status': transaction_status,
                'fraud_status': fraud_status,
                'status_code': notification_data.get('status_code'),
                'gross_amount': notification_data.get('gross_amount'),
                'transaction_time': notification_data.get('transaction_time'),
                'settlement_time': notification_data.get('settlement_time', ''),
                'payment_successful': payment_successful,
                'payment_pending': payment_pending,
                'payment_failed': payment_failed,
                'status_message': notification_data.get('status_message', ''),
                'custom_field1': notification_data.get('custom_field1', ''),  # Original transaction_id
                'webhook_timestamp': datetime.now().isoformat(),
                'raw_notification': notification_data
            }
            
            return processed_notification
            
        except Exception as e:
            logger.error(f"Error processing webhook notification: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'webhook_processing_failed',
                'raw_notification': notification_data
            }
    
    def cancel_payment(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel payment di Midtrans (jika masih pending)
        
        Args:
            order_id: Midtrans order ID
            
        Returns:
            Dict dengan cancellation result
        """
        try:
            # Check current status first
            current_status = self.check_payment_status(order_id)
            
            if not current_status['success']:
                return current_status
            
            # Only cancel if status is still pending
            if current_status['transaction_status'] not in ['pending', 'challenge']:
                return {
                    'success': False,
                    'error': f"Cannot cancel payment with status: {current_status['transaction_status']}",
                    'error_type': 'invalid_status_for_cancellation'
                }
            
            # Attempt to cancel
            cancel_response = self.snap.transactions.cancel(order_id)
            
            logger.info(f"Payment cancelled for order_id: {order_id}")
            
            return {
                'success': True,
                'order_id': order_id,
                'status': 'cancelled',
                'message': 'Payment cancelled successfully',
                'raw_response': cancel_response
            }
            
        except Exception as e:
            logger.error(f"Error cancelling payment for {order_id}: {str(e)}")
            return {
                'success': False,
                'order_id': order_id,
                'error': str(e),
                'error_type': 'cancellation_failed'
            }
    
    def get_enabled_payment_methods(self) -> List[str]:
        """
        Get list of enabled payment method codes for Midtrans API
        Includes ALL VA (Virtual Account) + ALL QRIS payment methods
        
        Coverage:
        - VA: BCA, BNI, BRI, Permata, CIMB, Danamon, Mandiri, Other
        - QRIS: GoPay, Standard QRIS, Other QRIS providers
        
        Returns:
            List of payment method codes for enabled_payments parameter
        """
        return [
            # All Virtual Account (VA) methods
            'bca_va',        # BCA Virtual Account
            'bni_va',        # BNI Virtual Account  
            'bri_va',        # BRI Virtual Account
            'permata_va',    # Permata Virtual Account
            'cimb_va',       # CIMB Virtual Account
            'danamon_va',    # Danamon Virtual Account
            'echannel',      # Mandiri Bill Payment
            'other_va',      # Other Virtual Account
            
            # QRIS & E-Wallet methods (comprehensive list)
            'gopay',         # GoPay direct payment (app redirect/QR code)
            'qris',          # Standard QRIS (GoPay QRIS, ShopeePay QRIS, DANA, OVO, LinkAja)
            'other_qris'     # Other QRIS providers (generic QRIS)
        ]
    
    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get current environment configuration info
        
        Returns:
            Dict dengan environment information
        """
        return {
            'environment': self.environment,
            'is_production': self.is_production,
            'api_url': self.api_url,
            'timeout_minutes': self.timeout_minutes,
            'webhook_url': self.webhook_url,
            'success_url': self.success_url,
            'error_url': self.error_url,
            'pending_url': self.pending_url,
            'client_key': self.client_key,  # Safe to expose client key
            'server_key_configured': bool(self.server_key),  # Don't expose actual server key
            'enabled_payment_methods': self.get_enabled_payment_methods()
        }

# Example usage dan testing
if __name__ == "__main__":
    try:
        # Initialize PaymentManager
        payment_manager = PaymentManager()
        
        # Test configuration
        print("=== PaymentManager Configuration ===")
        env_info = payment_manager.get_environment_info()
        for key, value in env_info.items():
            print(f"{key}: {value}")
        
        # Test payment token creation (example)
        print("\n=== Test Payment Token Creation ===")
        test_transaction = {
            'transaction_id': 'TEST_001',
            'items': [
                {
                    'product_id': 'bottle_001',
                    'name': 'Aqua Botol 600ml',
                    'price': 3000,
                    'quantity': 2
                },
                {
                    'product_id': 'snack_001', 
                    'name': 'Chitato BBQ',
                    'price': 8000,
                    'quantity': 1
                }
            ],
            'total': 14000,
            'customer': {
                'first_name': 'Test',
                'last_name': 'Customer',
                'email': 'test@example.com',
                'phone': '+6281234567890'
            }
        }
        
        result = payment_manager.create_payment_token(test_transaction)
        
        if result['success']:
            print(f"✅ Payment token created successfully!")
            print(f"Order ID: {result['order_id']}")
            print(f"Snap Token: {result['snap_token'][:20]}...")
            print(f"Payment URL: {result['payment_url']}")
        else:
            print(f"❌ Failed to create payment token: {result['error']}")
            
    except Exception as e:
        print(f"❌ Error testing PaymentManager: {str(e)}")