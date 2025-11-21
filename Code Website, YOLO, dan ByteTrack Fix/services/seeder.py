#!/usr/bin/env python3
"""
Seeder script to populate Firestore with sample products and transactions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from FirestoreManager import FirestoreManager
import random
from datetime import datetime, timedelta
import uuid

# Sample product data
SAMPLE_PRODUCTS = [
    {"name": "coca cola", "price": 5000},
    {"name": "pepsi", "price": 4500},
    {"name": "sprite", "price": 4500},
    {"name": "fanta", "price": 4500},
    {"name": "aqua", "price": 3000},
    {"name": "teh botol", "price": 4000},
    {"name": "pocari sweat", "price": 7000},
    {"name": "indomie goreng", "price": 3500},
    {"name": "mie sedaap", "price": 3500},
    {"name": "chitato", "price": 12000},
    {"name": "lays", "price": 13000},
    {"name": "pringles", "price": 25000},
    {"name": "oreo", "price": 8000},
    {"name": "silverqueen", "price": 15000},
    {"name": "kit kat", "price": 12000},
    {"name": "snickers", "price": 15000},
    {"name": "ultra milk", "price": 7000},
    {"name": "bear brand", "price": 9000},
    {"name": "yakult", "price": 3000},
    {"name": "nutrisari", "price": 2000}
]

def seed_products(firestore_manager):
    """Seed products to Firestore"""
    print("\n=== Seeding Products ===")
    
    success_count = 0
    for product in SAMPLE_PRODUCTS:
        result = firestore_manager.add_product(product["name"], product["price"])
        if result:
            print(f"✓ Added product: {product['name']} - Rp {product['price']:,}")
            success_count += 1
        else:
            print(f"✗ Failed to add product: {product['name']}")
    
    print(f"\nSuccessfully added {success_count}/{len(SAMPLE_PRODUCTS)} products")
    return success_count

def generate_random_transactions(firestore_manager, num_transactions=20):
    """Generate random transactions with sample products"""
    print(f"\n=== Generating {num_transactions} Sample Transactions ===")
    
    # Get all products
    products = firestore_manager.get_products()
    if not products:
        print("No products found. Please seed products first.")
        return 0
    
    product_list = list(products.items())
    success_count = 0
    
    for i in range(num_transactions):
        # Random date within last 30 days
        days_ago = random.randint(0, 30)
        transaction_date = datetime.now() - timedelta(days=days_ago)
        
        # Random number of items in cart (1-5)
        num_items = random.randint(1, min(5, len(product_list)))
        selected_products = random.sample(product_list, num_items)
        
        # Build cart
        cart = {}
        total = 0
        for product_name, price in selected_products:
            quantity = random.randint(1, 3)
            cart[product_name] = {
                'price': price,
                'quantity': quantity
            }
            total += price * quantity
        
        # Save transaction with custom timestamp
        try:
            # Create transaction documents
            transaction_ids = []
            for product_name, details in cart.items():
                transaction_id = str(uuid.uuid4())
                transaction_ref = firestore_manager.db.collection('transactions').document(transaction_id)
                
                transaction_data = {
                    'name': product_name,
                    'price': details['price'],
                    'quantity': details['quantity'],
                    'subtotal': details['price'] * details['quantity'],
                    'total': total,
                    'timestamp': transaction_date
                }
                
                transaction_ref.set(transaction_data)
                transaction_ids.append(transaction_id)
            
            print(f"✓ Transaction {i+1}: {len(cart)} items, Total: Rp {total:,}")
            success_count += 1
            
        except Exception as e:
            print(f"✗ Failed to create transaction {i+1}: {e}")
    
    print(f"\nSuccessfully created {success_count}/{num_transactions} transactions")
    return success_count

def main():
    """Main seeder function"""
    print("🌱 Firestore Seeder Script")
    print("=" * 50)
    
    # Initialize Firestore
    firestore_manager = FirestoreManager()
    
    if not firestore_manager.is_connected():
        print("❌ Failed to connect to Firestore. Please check your credentials.")
        return
    
    print("✅ Connected to Firestore")
    
    # Ask user what to seed
    print("\nWhat would you like to seed?")
    print("1. Products only")
    print("2. Transactions only") 
    print("3. Both products and transactions")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ")
    
    if choice == "1":
        seed_products(firestore_manager)
    elif choice == "2":
        num = input("How many transactions to generate? (default: 20): ")
        num_transactions = int(num) if num.isdigit() else 20
        generate_random_transactions(firestore_manager, num_transactions)
    elif choice == "3":
        seed_products(firestore_manager)
        num = input("How many transactions to generate? (default: 20): ")
        num_transactions = int(num) if num.isdigit() else 20
        generate_random_transactions(firestore_manager, num_transactions)
    elif choice == "4":
        print("Exiting...")
    else:
        print("Invalid choice")
    
    print("\n✨ Seeding complete!")

if __name__ == "__main__":
    main()