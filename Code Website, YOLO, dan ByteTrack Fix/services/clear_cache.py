#!/usr/bin/env python3
"""
Clear PyTorch and YOLOv5 cache to fix loading issues
"""
import os
import shutil
import torch.hub
from pathlib import Path

def clear_pytorch_cache():
    """Clear PyTorch hub cache"""
    try:
        cache_dir = torch.hub.get_dir()
        print(f"PyTorch cache directory: {cache_dir}")
        
        # Clear YOLOv5 specific cache
        yolo_cache = os.path.join(cache_dir, 'ultralytics_yolov5_master')
        if os.path.exists(yolo_cache):
            print("🗑️ Clearing YOLOv5 cache...")
            shutil.rmtree(yolo_cache)
            print("✅ YOLOv5 cache cleared")
        else:
            print("ℹ️ YOLOv5 cache not found")
        
        # Clear checkpoints cache
        checkpoints_cache = os.path.join(cache_dir, 'checkpoints')
        if os.path.exists(checkpoints_cache):
            print("🗑️ Clearing checkpoints cache...")
            shutil.rmtree(checkpoints_cache)
            print("✅ Checkpoints cache cleared")
        else:
            print("ℹ️ Checkpoints cache not found")
            
    except Exception as e:
        print(f"❌ Error clearing PyTorch cache: {e}")

def clear_pip_cache():
    """Clear pip cache"""
    try:
        import subprocess
        result = subprocess.run(['pip', 'cache', 'purge'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Pip cache cleared")
        else:
            print(f"⚠️ Pip cache clear warning: {result.stderr}")
    except Exception as e:
        print(f"❌ Error clearing pip cache: {e}")

def setup_environment():
    """Set up environment variables for YOLOv5 compatibility"""
    os.environ['TORCH_LOAD_WEIGHTS_ONLY'] = 'False'
    os.environ['YOLOV5_VERBOSE'] = 'False'
    print("✅ Environment variables set for YOLOv5 compatibility")

def main():
    print("=" * 60)
    print("🧹 CLEARING PYTORCH AND YOLOV5 CACHE")
    print("=" * 60)
    
    clear_pytorch_cache()
    clear_pip_cache()
    setup_environment()
    
    print("\n🎉 Cache clearing completed!")
    print("You can now run: python App.py")

if __name__ == "__main__":
    main()