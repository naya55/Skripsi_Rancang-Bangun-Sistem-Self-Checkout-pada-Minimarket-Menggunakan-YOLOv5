import os
import requests
import torch
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def download_yolov5_model():
    model_path = Path(os.getenv('MODEL_PATH', 'models/yolov5s.pt'))
    models_dir = model_path.parent
    models_dir.mkdir(exist_ok=True)
    
    if model_path.exists():
        print(f"✅ Model already exists at {model_path}")
        return str(model_path)
    
    print("📥 Downloading YOLOv5s model...")
    
    try:
        # Clear corrupted cache first
        import shutil
        import torch.hub
        
        cache_dir = torch.hub.get_dir()
        yolo_cache = os.path.join(cache_dir, 'ultralytics_yolov5_master')
        if os.path.exists(yolo_cache):
            print("Clearing corrupted YOLOv5 cache...")
            shutil.rmtree(yolo_cache)
        
        # Set environment variable for weights_only=False
        os.environ['TORCH_LOAD_WEIGHTS_ONLY'] = 'False'
        
        print("Downloading YOLOv5s model with force_reload...")
        model = torch.hub.load('ultralytics/yolov5', 'yolov5s', 
                              pretrained=True, 
                              trust_repo=True, 
                              force_reload=True)
        torch.save(model.state_dict(), model_path)
        print(f"✅ YOLOv5s model downloaded successfully to {model_path}")
        return str(model_path)
        
    except Exception as e:
        print(f"❌ Error downloading model via torch.hub: {e}")
        
        try:
            print("📥 Trying direct download...")
            url = os.getenv('YOLO_MODEL_URL', 'https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.pt')
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r📥 Downloading: {percent:.1f}%", end='', flush=True)
            
            print(f"\n✅ YOLOv5s model downloaded successfully to {model_path}")
            return str(model_path)
            
        except Exception as e2:
            print(f"❌ Error downloading model directly: {e2}")
            return None


def verify_model():
    model_path = Path(os.getenv('MODEL_PATH', 'models/yolov5s.pt'))
    
    if not model_path.exists():
        print("❌ Model file not found")
        return False
    
    try:
        print("🔍 Verifying model...")
        # Set environment variable for weights_only=False
        os.environ['TORCH_LOAD_WEIGHTS_ONLY'] = 'False'
        
        model = torch.hub.load('ultralytics/yolov5', 'custom', 
                              path=str(model_path), 
                              trust_repo=True, 
                              force_reload=True)
        print("✅ Model verification successful")
        return True
        
    except Exception as e:
        print(f"❌ Model verification failed: {e}")
        return False


def check_dependencies():
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'torch', 'torchvision', 'opencv-python', 'pillow', 
        'numpy', 'matplotlib', 'pyyaml', 'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📦 Install missing packages:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All dependencies are installed")
    return True


def main():
    print("=" * 50)
    print("🛒 Self-Checkout System - Model Setup")
    print("=" * 50)
    
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        return
    
    model_path = download_yolov5_model()
    
    if model_path and verify_model():
        print("\n🎉 Setup completed successfully!")
        print(f"📁 Model location: {model_path}")
        print("\n🚀 You can now run: python app.py")
    else:
        print("\n❌ Setup failed. Please check the errors above.")


if __name__ == "__main__":
    main()