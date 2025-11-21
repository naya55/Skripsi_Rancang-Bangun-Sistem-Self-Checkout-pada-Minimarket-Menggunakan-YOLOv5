import torch
import yaml
from pathlib import Path

def check_yolo_labels(model_path):
    """
    Check labels/classes in a YOLO .pt model file
    """
    print(f"Loading model: {model_path}")
    
    try:
        # Load the model
        model = torch.load(model_path, map_location='cpu')
        
        # Method 1: Check if model has 'names' attribute
        if 'model' in model:
            if hasattr(model['model'], 'names'):
                print("\n=== Labels from model.names ===")
                names = model['model'].names
                for idx, name in enumerate(names):
                    print(f"{idx}: {name}")
        
        # Method 2: Check in model dictionary directly
        if 'names' in model:
            print("\n=== Labels from model['names'] ===")
            names = model['names']
            if isinstance(names, dict):
                for idx, name in names.items():
                    print(f"{idx}: {name}")
            elif isinstance(names, list):
                for idx, name in enumerate(names):
                    print(f"{idx}: {name}")
        
        # Method 3: Check model yaml data if exists
        if 'yaml' in model:
            print("\n=== YAML Configuration ===")
            yaml_data = yaml.safe_load(model['yaml'])
            if 'names' in yaml_data:
                print("Labels from YAML:")
                names = yaml_data['names']
                if isinstance(names, dict):
                    for idx, name in names.items():
                        print(f"{idx}: {name}")
                elif isinstance(names, list):
                    for idx, name in enumerate(names):
                        print(f"{idx}: {name}")
        
        # Method 4: For Ultralytics YOLO models
        if 'train_args' in model:
            if 'names' in model['train_args']:
                print("\n=== Labels from train_args ===")
                names = model['train_args']['names']
                for idx, name in names.items():
                    print(f"{idx}: {name}")
        
        # Show model info
        print("\n=== Model Info ===")
        print(f"Model keys: {list(model.keys())}")
        
        if 'model' in model:
            model_obj = model['model']
            if hasattr(model_obj, 'yaml'):
                print(f"Model YAML: {model_obj.yaml}")
            if hasattr(model_obj, 'nc'):
                print(f"Number of classes: {model_obj.nc}")
                
    except Exception as e:
        print(f"Error loading model: {e}")

# Alternative method using Ultralytics
def check_labels_ultralytics(model_path):
    """
    Check labels using Ultralytics YOLO library
    """
    try:
        from ultralytics import YOLO
        
        print(f"\n=== Using Ultralytics YOLO ===")
        model = YOLO(model_path)
        
        # Get class names
        names = model.names
        print(f"Number of classes: {len(names)}")
        print("\nClass labels:")
        for idx, name in names.items():
            print(f"{idx}: {name}")
            
    except ImportError:
        print("Ultralytics not installed. Install with: pip install ultralytics")
    except Exception as e:
        print(f"Error with Ultralytics: {e}")

if __name__ == "__main__":
    # Check if model exists in services/models/
    model_paths = [
        "services/models/yolov5s.pt",
        "services/models/yolov5m.pt",
        "services/models/yolov5l.pt",
        "services/models/yolov5x.pt"
    ]
    
    for path in model_paths:
        if Path(path).exists():
            print(f"\n{'='*50}")
            print(f"Checking: {path}")
            print('='*50)
            
            # Try both methods
            check_yolo_labels(path)
            check_labels_ultralytics(path)
            break
    else:
        print("No YOLO model found in services/models/")
        print("You can specify a model path as argument")