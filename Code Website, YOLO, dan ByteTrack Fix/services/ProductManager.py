class ProductManager:
    def __init__(self, firestore_manager):
        self.firestore_manager = firestore_manager
        self.products = {}
        self.load_products()

    def load_products(self):
        if self.firestore_manager.is_connected():
            self.products = self.firestore_manager.get_products()
        else:
            self.products = {}


    def get_products(self):
        return self.products

    def add_product(self, name, price):
        name_lower = name.lower()

        if not self.firestore_manager.is_connected():
            return None
            
        result = self.firestore_manager.add_product(name_lower, price)
        if result:
            self.products[name_lower] = price
            return {"name": name_lower, "price": price}
        return None

    def update_product(self, name, price):
        name_lower = name.lower()
        if name_lower not in self.products:
            return None

        if not self.firestore_manager.is_connected():
            return None
            
        result = self.firestore_manager.update_product(name_lower, price)
        if result:
            self.products[name_lower] = price
            return {"name": name_lower, "price": price}
        return None

    def delete_product(self, name):
        name_lower = name.lower()
        if name_lower not in self.products:
            return None

        if not self.firestore_manager.is_connected():
            return None
            
        result = self.firestore_manager.delete_product(name_lower)
        if result:
            del self.products[name_lower]
            return {"name": name_lower}
        return None

    def delete_all_products(self):
        if not self.firestore_manager.is_connected():
            return {"deleted_count": 0}
            
        result = self.firestore_manager.delete_all_products()
        deleted_count = len(self.products)
        self.products = {}
        
        return {"deleted_count": deleted_count}
