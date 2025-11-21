"""
Script sederhana untuk melihat label/class names dalam model YOLO .pt

Cara menggunakan:
1. Pastikan sudah install: pip install torch ultralytics
2. Jalankan: python check_labels_simple.py

Atau gunakan method Ultralytics (lebih mudah):
"""

print("=== Cara Melihat Label Model YOLO ===\n")

print("Method 1: Menggunakan Ultralytics (Recommended)")
print("-" * 40)
print("""
from ultralytics import YOLO

# Load model
model = YOLO('path/to/model.pt')

# Lihat semua class names
print(model.names)
# Output: {0: 'person', 1: 'bicycle', 2: 'car', ...}

# Lihat jumlah classes
print(f"Total classes: {len(model.names)}")
""")

print("\nMethod 2: Menggunakan PyTorch langsung")
print("-" * 40)
print("""
import torch

# Load model
model = torch.load('path/to/model.pt', map_location='cpu')

# Cek berbagai lokasi untuk names
if 'names' in model:
    print(model['names'])
    
if 'model' in model and hasattr(model['model'], 'names'):
    print(model['model'].names)
    
if 'train_args' in model and 'names' in model['train_args']:
    print(model['train_args']['names'])
""")

print("\nMethod 3: Untuk model YOLOv5 default (COCO dataset)")
print("-" * 40)
print("""
YOLOv5 default menggunakan 80 classes COCO:
0: person          40: wine glass      
1: bicycle         41: cup             
2: car             42: fork            
3: motorcycle      43: knife           
4: airplane        44: spoon           
5: bus             45: bowl            
6: train           46: banana          
7: truck           47: apple           
8: boat            48: sandwich        
9: traffic light   49: orange          
10: fire hydrant   50: broccoli        
... dan seterusnya hingga 79: toothbrush
""")

print("\nContoh penggunaan di project ini:")
print("-" * 40)
print("""
# Di services/ProductDetector.py
import torch

model_path = "services/models/yolov5s.pt"
model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)

# Akses labels
labels = model.names  # atau model.model.names
print(labels)
""")

# Coba baca label dari model yang ada di project
import os

if os.path.exists("services/models/yolov5s.pt"):
    print("\n=== Info Model di Project Ini ===")
    print("Model tersedia: services/models/yolov5s.pt")
    print("Kemungkinan menggunakan COCO classes (80 classes)")
    print("Untuk melihat detail, jalankan dengan Python yang sudah install torch & ultralytics")
else:
    print("\nTidak ada model .pt yang ditemukan di services/models/")
    print("Model akan di-download otomatis saat menjalankan aplikasi")