from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import time
from datetime import datetime

# Enhanced logging for debugging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import YOLO detector
from yolo_detector import yolo_detector, initialize_yolo

app = FastAPI()

# Add CORS middleware for ESP32 compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    """Log all incoming requests"""
    client_ip = request.client.host if request.client else "unknown"
    start_time = time.time()
    
    logger.info(f"📥 {request.method} {request.url.path} from {client_ip}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"📤 {request.method} {request.url.path} -> {response.status_code} ({process_time:.3f}s)")
    
    return response

@app.post("/yolo-detect")
async def yolo_detect_objects(request: Request):
    """YOLO object detection endpoint"""
    start_time = time.time()
    request_time = datetime.now().isoformat()
    
    try:
        # Check if YOLO model is loaded, try to reload if not
        if not yolo_detector.model_loaded:
            logger.warning("🔄 YOLO model not loaded, attempting to reload...")
            reload_success = yolo_detector.load_model()
            
            if not reload_success:
                logger.error("🚫 YOLO model still not loaded after retry - check server startup logs")
                return JSONResponse({
                    "status": "error",
                    "error": "YOLO model not loaded",
                    "details": yolo_detector.load_error or "Unknown model loading error",
                    "last_attempt": yolo_detector.last_load_attempt.isoformat() if yolo_detector.last_load_attempt else None,
                    "processing_time": round(time.time() - start_time, 3)
                }, status_code=503)
        
        # Get client IP
        client_ip = request.client.host if hasattr(request, 'client') and request.client else "unknown"
        logger.info(f"🔍 Received YOLO detection request from {client_ip}")
        
        # Read raw image data from request body
        image_data = await request.body()
        image_size = len(image_data)
        
        logger.info(f"📦 YOLO Image data: {image_size} bytes ({image_size/1024:.1f} KB)")
        
        # Basic validation
        if image_size < 1000:
            return JSONResponse({
                "status": "error",
                "error": "Image too small - minimum 1KB required",
                "processing_time": round(time.time() - start_time, 3)
            }, status_code=400)
        
        if image_size > 10 * 1024 * 1024:  # 10MB limit
            return JSONResponse({
                "status": "error",
                "error": "Image too large - maximum 10MB allowed",
                "processing_time": round(time.time() - start_time, 3)
            }, status_code=413)
        
        # Check JPEG format
        if not (image_data.startswith(b'\xff\xd8') and image_data.endswith(b'\xff\xd9')):
            return JSONResponse({
                "status": "error",
                "error": "Invalid JPEG format",
                "processing_time": round(time.time() - start_time, 3)
            }, status_code=400)
        
        # Run YOLO detection
        logger.info("🔍 Running YOLO detection...")
        detection_start = time.time()
        
        detection_results, error = yolo_detector.detect_objects(image_data)
        
        detection_time = round(time.time() - detection_start, 3)
        
        if error:
            return JSONResponse({
                "status": "error",
                "error": error,
                "processing_time": round(time.time() - start_time, 3)
            }, status_code=500)
        
        processing_time = round(time.time() - start_time, 3)
        
        # Prepare response
        response_data = {
            "status": "success",
            "message": "YOLO detection completed successfully",
            "image_info": {
                "size_bytes": image_size,
                "size_kb": round(image_size / 1024, 1),
                "dimensions": detection_results["image_dimensions"],
                "format": "JPEG"
            },
            "detection_results": {
                "total_objects": detection_results["total_objects"],
                "objects_detected": detection_results["objects_detected"],
                "detection_time": detection_time
            },
            "processing_time": processing_time,
            "server_timestamp": request_time
        }
        
        # Log results
        total_objects = detection_results["total_objects"]
        object_summary = {}
        for detection in detection_results["objects_detected"]:
            obj_name = detection["object"]
            if obj_name in object_summary:
                object_summary[obj_name] += 1
            else:
                object_summary[obj_name] = 1
        
        summary_str = ", ".join([f"{count}x {obj}" for obj, count in object_summary.items()])
        logger.info(f"✅ YOLO Detection complete: {total_objects} objects found - {summary_str}")
        print(f"🔍 YOLO DETECTION: {total_objects} objects: {summary_str}")
        
        return JSONResponse(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error in YOLO detection: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": f"YOLO detection error: {str(e)}",
            "processing_time": round(time.time() - start_time, 3)
        }, status_code=500)

@app.get("/")
async def root():
    return JSONResponse(
        content={"status": "online", "message": "Image Processing API is running"},
        headers={"Content-Type": "application/json"}
    )

@app.get("/health")
async def health_check():
    """Simple health check for ESP32"""
    return JSONResponse(
        content={"status": "ok"},
        headers={"Content-Type": "application/json"}
    )

@app.post("/upload-image")
async def upload_image_direct(request: Request):
    """Handle direct JPEG image upload from ESP32 camera - Save only"""
    start_time = time.time()
    request_time = datetime.now().isoformat()
    
    try:
        # Get client IP
        client_ip = request.client.host if hasattr(request, 'client') and request.client else "unknown"
        logger.info(f"📸 Received direct image upload from {client_ip}")
        
        # Read raw image data from request body
        image_data = await request.body()
        image_size = len(image_data)
        
        logger.info(f"📦 Image data: {image_size} bytes ({image_size/1024:.1f} KB)")
        
        # Basic validation
        if image_size < 1000:  # Less than 1KB is probably not a valid image
            logger.warning("❌ Image too small")
            return JSONResponse({
                "status": "error",
                "error": "Image too small - minimum 1KB required",
                "processing_time": round(time.time() - start_time, 3)
            }, status_code=400)
        
        if image_size > 5 * 1024 * 1024:  # More than 5MB
            logger.warning("❌ Image too large")
            return JSONResponse({
                "status": "error", 
                "error": "Image too large - maximum 5MB allowed",
                "processing_time": round(time.time() - start_time, 3)
            }, status_code=413)
        
        # Check if it's a JPEG image (basic check)
        if not (image_data.startswith(b'\xff\xd8') and image_data.endswith(b'\xff\xd9')):
            logger.warning("❌ Invalid JPEG format")
            return JSONResponse({
                "status": "error",
                "error": "Invalid JPEG format",
                "processing_time": round(time.time() - start_time, 3)
            }, status_code=400)
        
        # Generate filename for storage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"esp32_image_{timestamp}.jpg"
        
        # Save image to disk
        save_dir = "received_images"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        file_path = os.path.join(save_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        processing_time = round(time.time() - start_time, 3)
        
        response_data = {
            "status": "success",
            "message": "Image received and saved successfully",
            "image_info": {
                "filename": filename,
                "size_bytes": image_size,
                "size_kb": round(image_size / 1024, 1),
                "format": "JPEG"
            },
            "processing_time": processing_time,
            "server_timestamp": request_time,
            "saved_to": file_path
        }
        
        logger.info(f"✅ Image saved: {filename} ({image_size/1024:.1f}KB)")
        print(f"📷 IMAGE SAVED: {filename} ({image_size/1024:.1f}KB)")
        
        return JSONResponse(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error saving image: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": f"Save error: {str(e)}",
            "processing_time": round(time.time() - start_time, 3)
        }, status_code=500)

if __name__ == "__main__":
    import uvicorn
    
    # Check for model file before starting
    model_file = "best.pt"
    if not os.path.exists(model_file):
        print(f"❌ ERROR: Model file '{model_file}' not found!")
        print(f"📂 Current directory: {os.getcwd()}")
        print("📋 Files in current directory:")
        for f in os.listdir('.'):
            if f.endswith('.pt') or f.endswith('.pth'):
                print(f"   - {f}")
        print("\n🔧 To fix this:")
        print("   1. Make sure your trained YOLO model file is named 'best.pt'")
        print("   2. Place it in the project root directory")
        print("   3. Restart the server")
        print("\n⚠️  Server will start but YOLO detection will fail until model is available\n")
    
    # Initialize YOLO detector
    print("🔍 Initializing YOLO detector...")
    yolo_success = initialize_yolo()
    
    if not yolo_success:
        print("⚠️  YOLO initialization failed!")
        if os.path.exists(model_file):
            print("   Model file exists but failed to load - check the file integrity")
        else:
            print(f"   Model file '{model_file}' not found in project root")
        print("   The server will start but YOLO detection will not work.")
    
    print("🚀 Starting FastAPI server...")
    print("📡 Server will be available at: http://0.0.0.0:8000")
    print("🔍 Health check: http://192.168.0.113:8000/health")
    print("🔍 YOLO detection: http://192.168.0.113:8000/yolo-detect")
    print("📷 Upload image: http://192.168.0.113:8000/upload-image")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)


