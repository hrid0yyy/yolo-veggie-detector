# ESP32 YOLO Object Detection Server

A FastAPI server that receives images from ESP32 camera and performs YOLO object detection.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Server
```bash
python start_server.py
```

The server will start on `http://<your-local-ip>:8000`

## Endpoints

- `/health` - Health check
- `/yolo-detect` - YOLO object detection (POST)
- `/upload-image` - Save images (POST)

## ESP32 Setup

Update these values in `esp-yolo.ino`:
```cpp
const char* ssid = "your_wifi_name";
const char* password = "your_wifi_password"; 
const char* serverHost = "your_server_ip";
```

## Output

ESP32 will print detected objects:
```
onion: x=286, y=135, w=191, h=201
No object found
```

Detection runs every 1 second.
