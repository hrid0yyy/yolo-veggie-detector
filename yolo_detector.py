"""
YOLO Vegetable Detection Module

This module handles YOLO model loading and object detection
Can be imported into main.py to add YOLO endpoints
"""

from ultralytics import YOLO
import cv2
import numpy as np
import os
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class YOLODetector:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.last_load_attempt = None
        self.load_error = None
        
    def load_model(self, model_path=None):
        """Load YOLO model with better error handling"""
        try:
            model_path = model_path or "best.pt"
            self.last_load_attempt = datetime.now()
            
            # Check if file exists
            if not os.path.exists(model_path):
                self.load_error = f"YOLO model file '{model_path}' not found in {os.getcwd()}"
                logger.error(f"❌ {self.load_error}")
                logger.error("   Make sure 'best.pt' exists in the project root directory")
                return False
            
            # Check file size
            file_size = os.path.getsize(model_path)
            logger.info(f"📁 Found model file: {model_path} ({file_size/1024/1024:.1f} MB)")
            
            if file_size < 1024 * 1024:  # Less than 1MB is suspicious
                logger.warning(f"⚠️  Model file seems small ({file_size} bytes) - might be corrupted")
            
            # Load the model
            logger.info("🔄 Loading YOLO model...")
            self.model = YOLO(model_path)
            
            # Test the model with a dummy prediction to ensure it's working
            logger.info("🧪 Testing model...")
            dummy_image = np.zeros((640, 640, 3), dtype=np.uint8)
            test_results = self.model(dummy_image, verbose=False)
            
            self.model_loaded = True
            self.load_error = None
            logger.info(f"✅ YOLO model loaded and tested successfully from {model_path}")
            
            # Log model info
            if hasattr(self.model, 'names'):
                class_count = len(self.model.names)
                logger.info(f"🏷️  Model has {class_count} classes: {list(self.model.names.values())}")
            
            return True
            
        except Exception as e:
            self.load_error = f"Error loading YOLO model: {str(e)}"
            logger.error(f"❌ {self.load_error}")
            logger.error(f"   Exception details: {type(e).__name__}: {e}")
            return False
    
    def detect_objects(self, image_data):
        """Detect objects in image data"""
        if not self.model_loaded:
            return None, "YOLO model not loaded"
        
        try:
            # Convert image data to OpenCV format
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None, "Failed to decode image"
            
            # Run YOLO detection
            results = self.model(img, conf=0.3, verbose=False)
            
            # Process results
            detections = []
            total_objects = 0
            
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        # Get detection info
                        confidence = float(box.conf[0])
                        class_id = int(box.cls[0])
                        class_name = self.model.names[class_id] if class_id in self.model.names else f"class_{class_id}"
                        
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        
                        detection_info = {
                            "object": class_name,
                            "confidence": round(confidence * 100, 1),
                            "bounding_box": {
                                "x1": round(x1),
                                "y1": round(y1),
                                "x2": round(x2),
                                "y2": round(y2),
                                "width": round(x2 - x1),
                                "height": round(y2 - y1)
                            }
                        }
                        
                        detections.append(detection_info)
                        total_objects += 1
            
            return {
                "total_objects": total_objects,
                "objects_detected": detections,
                "image_dimensions": {
                    "width": img.shape[1],
                    "height": img.shape[0]
                }
            }, None
            
        except Exception as e:
            logger.error(f"❌ Error in YOLO detection: {str(e)}")
            return None, f"Detection error: {str(e)}"

# Global detector instance
yolo_detector = YOLODetector()

def initialize_yolo():
    """Initialize YOLO detector with retry logic"""
    print("🔍 Initializing YOLO detector...")
    
    # Check current directory
    current_dir = os.getcwd()
    print(f"📂 Current directory: {current_dir}")
    
    # List files in current directory to help debug
    files = [f for f in os.listdir('.') if f.endswith('.pt')]
    if files:
        print(f"📋 Found .pt files: {files}")
    else:
        print("❌ No .pt files found in current directory")
        print("   Make sure to download or copy your trained 'best.pt' model file here")
    
    # Try to load the model
    success = yolo_detector.load_model()
    
    if success:
        print("🔍 YOLO detector initialized successfully")
    else:
        print("⚠️  YOLO detector failed to initialize")
        print(f"   Error: {yolo_detector.load_error}")
        print("   Object detection will not work until the model is loaded")
        
    return success
