import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
import datetime
import uuid
import json
from zoneinfo import ZoneInfo


class FirestoreManager:
    def __init__(self, credentials_path="firebase-credentials.json"):
        self.credentials_path = credentials_path
        self.db = None
        self.initialize_firestore()
    
    @staticmethod
    def get_wib_time():
        """Get current time in WIB (GMT+7) timezone"""
        return datetime.datetime.now(ZoneInfo("Asia/Jakarta"))
    
    @staticmethod
    def convert_to_wib(timestamp):
        """Convert timestamp to WIB timezone"""
        if timestamp is None:
            return None
        
        # If it's already timezone-aware, convert to WIB
        if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
            return timestamp.astimezone(ZoneInfo("Asia/Jakarta"))
        
        # If it's naive datetime, assume it's UTC and convert to WIB
        utc_timestamp = timestamp.replace(tzinfo=ZoneInfo("UTC"))
        return utc_timestamp.astimezone(ZoneInfo("Asia/Jakarta"))

    def initialize_firestore(self):
        if not os.path.exists(self.credentials_path):
            print(f"Firebase credentials file {self.credentials_path} not found.")
            print("Creating a sample credentials file. Please replace with your actual credentials.")
            self._create_sample_credentials()

        try:
            cred = credentials.Certificate(self.credentials_path)
            firebase_admin.initialize_app(cred)
            self.db = firestore.client()
        except Exception as e:
            print(f"Error initializing Firestore: {e}")
            self.db = None

    def _create_sample_credentials(self):
        sample_credentials = {
            "type": "service_account",
            "project_id": "your-project-id",
            "private_key_id": "your-private-key-id",
            "private_key": "your-private-key",
            "client_email": "your-client-email",
            "client_id": "your-client-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "your-client-cert-url"
        }

        with open(self.credentials_path, 'w') as f:
            json.dump(sample_credentials, f, indent=2)

    def is_connected(self):
        return self.db is not None

    def get_products(self):
        if not self.is_connected():
            return {}

        products = {}
        try:
            products_ref = self.db.collection('products')
            docs = products_ref.stream()

            for doc in docs:
                product_data = doc.to_dict()
                products[product_data['name'].lower()] = product_data['price']

            return products
        except Exception as e:
            print(f"Error retrieving products from Firestore: {e}")
            return {}

    def add_product(self, name, price):
        if not self.is_connected():
            return None

        try:
            product_id = str(uuid.uuid4())
            product_ref = self.db.collection('products').document(product_id)

            product_data = {
                'name': name.lower(),
                'price': price,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }

            product_ref.set(product_data)

            product_doc = product_ref.get()
            product_data = product_doc.to_dict()

            return {
                'id': product_id,
                'name': product_data['name'],
                'price': product_data['price']
            }
        except Exception as e:
            print(f"Error adding product to Firestore: {e}")
            return None

    def update_product(self, name, price):
        if not self.is_connected():
            return None

        try:
            products_ref = self.db.collection('products')
            query = products_ref.where('name', '==', name.lower())
            docs = query.stream()

            updated = False
            product_id = None

            for doc in docs:
                product_id = doc.id
                product_ref = products_ref.document(product_id)
                product_ref.update({
                    'price': price,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                updated = True
                break

            if updated:
                return {
                    'id': product_id,
                    'name': name.lower(),
                    'price': price
                }
            else:
                print(f"Product {name} not found in Firestore")
                return None
        except Exception as e:
            print(f"Error updating product in Firestore: {e}")
            return None

    def delete_product(self, name):
        if not self.is_connected():
            return None

        try:
            products_ref = self.db.collection('products')
            query = products_ref.where('name', '==', name.lower())
            docs = query.stream()

            deleted = False
            product_id = None

            for doc in docs:
                product_id = doc.id
                products_ref.document(product_id).delete()
                deleted = True
                break

            if deleted:
                return {
                    'id': product_id,
                    'name': name.lower()
                }
            else:
                print(f"Product {name} not found in Firestore")
                return None
        except Exception as e:
            print(f"Error deleting product from Firestore: {e}")
            return None

    def delete_all_products(self):
        if not self.is_connected():
            return {'deleted_count': 0}

        try:
            products_ref = self.db.collection('products')
            docs = products_ref.stream()
            
            deleted_count = 0
            for doc in docs:
                doc.reference.delete()
                deleted_count += 1
            
            return {'deleted_count': deleted_count}
        except Exception as e:
            print(f"Error deleting all products from Firestore: {e}")
            return {'deleted_count': 0}

    def save_transaction(self, cart, total):
        if not self.is_connected():
            return None

        try:
            # Create separate transaction documents for each item
            transaction_ids = []
            
            for product_name, details in cart.items():
                transaction_id = str(uuid.uuid4())
                transaction_ref = self.db.collection('transactions').document(transaction_id)
                
                transaction_data = {
                    'name': product_name,
                    'price': details['price'],
                    'quantity': details['quantity'],
                    'subtotal': details['price'] * details['quantity'],
                    'total': total,
                    'timestamp': firestore.SERVER_TIMESTAMP
                }
                
                transaction_ref.set(transaction_data)
                transaction_ids.append(transaction_id)
            
            # Return the list of created transaction IDs
            return {
                'transaction_ids': transaction_ids,
                'total': total,
                'timestamp': self.get_wib_time()
            }
        except Exception as e:
            print(f"Error saving transaction to Firestore: {e}")
            return None

    def get_transactions(self, limit=20):
        if not self.is_connected():
            return []

        try:
            transactions_ref = self.db.collection('transactions')
            query = transactions_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            docs = query.stream()

            # Group transactions by timestamp and total to reconstruct cart transactions
            grouped_transactions = {}
            
            for doc in docs:
                data = doc.to_dict()
                timestamp = data.get('timestamp')
                total = data.get('total', 0)
                
                # Create a key from timestamp and total to group items
                if timestamp:
                    key = f"{timestamp}_{total}"
                    
                    if key not in grouped_transactions:
                        grouped_transactions[key] = {
                            'id': doc.id,  # Use first doc id as transaction id
                            'items': [],
                            'total': total,
                            'timestamp': timestamp
                        }
                    
                    # Add item to the transaction
                    grouped_transactions[key]['items'].append({
                        'name': data.get('name', ''),
                        'price': data.get('price', 0),
                        'quantity': data.get('quantity', 0),
                        'subtotal': data.get('subtotal', 0)
                    })
            
            # Convert to list and sort by timestamp
            transactions = list(grouped_transactions.values())
            transactions.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.datetime.min, reverse=True)
            
            return transactions[:limit]
        except Exception as e:
            print(f"Error retrieving transactions from Firestore: {e}")
            return []

    def get_transactions_by_date_range(self, start_date, end_date):
        if not self.is_connected():
            return []

        try:
            transactions_ref = self.db.collection('transactions')

            if isinstance(start_date, str):
                start_date = datetime.datetime.fromisoformat(start_date)
            if isinstance(end_date, str):
                end_date = datetime.datetime.fromisoformat(end_date)

            end_date = end_date + datetime.timedelta(days=1)

            query = transactions_ref.where('timestamp', '>=', start_date).where('timestamp', '<', end_date)
            docs = query.stream()

            # Group transactions by timestamp and total
            grouped_transactions = {}
            
            for doc in docs:
                data = doc.to_dict()
                timestamp = data.get('timestamp')
                total = data.get('total', 0)
                
                if timestamp:
                    key = f"{timestamp}_{total}"
                    
                    if key not in grouped_transactions:
                        grouped_transactions[key] = {
                            'id': doc.id,
                            'items': [],
                            'total': total,
                            'timestamp': timestamp
                        }
                    
                    grouped_transactions[key]['items'].append({
                        'name': data.get('name', ''),
                        'price': data.get('price', 0),
                        'quantity': data.get('quantity', 0),
                        'subtotal': data.get('subtotal', 0)
                    })
            
            transactions = list(grouped_transactions.values())
            transactions.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.datetime.min, reverse=True)
            
            return transactions
        except Exception as e:
            print(f"Error retrieving transactions by date range from Firestore: {e}")
            return []

    def delete_transaction(self, transaction_id):
        if not self.is_connected():
            return False

        try:
            transaction_ref = self.db.collection('transactions').document(transaction_id)
            transaction_doc = transaction_ref.get()

            if not transaction_doc.exists:
                print(f"Transaction {transaction_id} not found in Firestore")
                return False

            transaction_ref.delete()
            return True
        except Exception as e:
            print(f"Error deleting transaction from Firestore: {e}")
            return False

    def delete_all_transactions(self):
        if not self.is_connected():
            return {'deleted_count': 0}

        try:
            transactions_ref = self.db.collection('transactions')
            docs = transactions_ref.stream()
            
            deleted_count = 0
            for doc in docs:
                doc.reference.delete()
                deleted_count += 1
            
            return {'deleted_count': deleted_count}
        except Exception as e:
            print(f"Error deleting all transactions from Firestore: {e}")
            return {'deleted_count': 0}

    def save_settings(self, doc_id, settings):
        """Save application settings to Firestore settings collection"""
        if not self.is_connected():
            return False

        try:
            settings_ref = self.db.collection('settings').document(doc_id)
            
            # Add timestamp for tracking
            settings_data = {
                **settings,
                'updated_at': self.get_wib_time(),
                'created_at': self.get_wib_time()
            }
            
            # Check if document exists to update created_at properly
            existing_doc = settings_ref.get()
            if existing_doc.exists:
                existing_data = existing_doc.to_dict()
                if 'created_at' in existing_data:
                    settings_data['created_at'] = existing_data['created_at']
            
            settings_ref.set(settings_data)
            return True
            
        except Exception as e:
            print(f"Error saving settings to Firestore: {e}")
            return False

    def load_settings(self, doc_id):
        """Load application settings from Firestore settings collection"""
        if not self.is_connected():
            return None

        try:
            settings_ref = self.db.collection('settings').document(doc_id)
            settings_doc = settings_ref.get()
            
            if not settings_doc.exists:
                print(f"Settings document {doc_id} not found in Firestore")
                return None
            
            settings_data = settings_doc.to_dict()
            
            # Remove Firestore metadata fields before returning
            if 'updated_at' in settings_data:
                del settings_data['updated_at']
            if 'created_at' in settings_data:
                del settings_data['created_at']
            
            return settings_data
            
        except Exception as e:
            print(f"Error loading settings from Firestore: {e}")
            return None

    def get_transaction_by_id(self, transaction_id):
        if not self.is_connected():
            return None

        try:
            # First, try to get the specific document
            transaction_ref = self.db.collection('transactions').document(transaction_id)
            transaction_doc = transaction_ref.get()

            if not transaction_doc.exists:
                print(f"Transaction {transaction_id} not found in Firestore")
                return None

            data = transaction_doc.to_dict()
            timestamp = data.get('timestamp')
            total = data.get('total', 0)
            
            # Find all items with the same timestamp and total
            transactions_ref = self.db.collection('transactions')
            query = transactions_ref.where('timestamp', '==', timestamp).where('total', '==', total)
            docs = query.stream()
            
            items = []
            for doc in docs:
                item_data = doc.to_dict()
                items.append({
                    'name': item_data.get('name', ''),
                    'price': item_data.get('price', 0),
                    'quantity': item_data.get('quantity', 0),
                    'subtotal': item_data.get('subtotal', 0)
                })
            
            return {
                'id': transaction_id,
                'items': items,
                'total': total,
                'timestamp': timestamp
            }
        except Exception as e:
            print(f"Error retrieving transaction from Firestore: {e}")
            return None
