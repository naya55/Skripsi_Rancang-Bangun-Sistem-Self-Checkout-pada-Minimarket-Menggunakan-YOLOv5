#!/usr/bin/env python3
"""
Delete script to remove products and/or transactions from Firestore
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from FirestoreManager import FirestoreManager

def delete_all_products(firestore_manager):
    """Delete all products from Firestore"""
    print("\n=== Deleting All Products ===")
    
    confirm = input("⚠️  Are you sure you want to delete ALL products? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    result = firestore_manager.delete_all_products()
    print(f"✅ Deleted {result['deleted_count']} products from Firestore")

def delete_all_transactions(firestore_manager):
    """Delete all transactions from Firestore"""
    print("\n=== Deleting All Transactions ===")
    
    confirm = input("⚠️  Are you sure you want to delete ALL transactions? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    result = firestore_manager.delete_all_transactions()
    print(f"✅ Deleted {result['deleted_count']} transactions from Firestore")

def main():
    """Main delete function"""
    print("🗑️  Firestore Data Deletion Script")
    print("=" * 50)
    
    # Initialize Firestore
    firestore_manager = FirestoreManager()
    
    if not firestore_manager.is_connected():
        print("❌ Failed to connect to Firestore. Please check your credentials.")
        return
    
    print("✅ Connected to Firestore")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--products':
            delete_all_products(firestore_manager)
        elif sys.argv[1] == '--transactions' or sys.argv[1] == '--history':
            delete_all_transactions(firestore_manager)
        elif sys.argv[1] == '--all':
            delete_all_products(firestore_manager)
            delete_all_transactions(firestore_manager)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Usage: python DeleteData.py [--products|--transactions|--history|--all]")
    else:
        # Interactive mode
        print("\nWhat would you like to delete?")
        print("1. Products only")
        print("2. Transactions only") 
        print("3. Both products and transactions")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            delete_all_products(firestore_manager)
        elif choice == "2":
            delete_all_transactions(firestore_manager)
        elif choice == "3":
            delete_all_products(firestore_manager)
            delete_all_transactions(firestore_manager)
        elif choice == "4":
            print("Exiting...")
        else:
            print("Invalid choice")
    
    print("\n✨ Operation complete!")

if __name__ == "__main__":
    main()