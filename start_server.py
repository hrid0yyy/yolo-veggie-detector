#!/usr/bin/env python3
import uvicorn
import socket
import sys
from main import app

def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def check_port_available(port):
    """Check if port is available"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(('0.0.0.0', port))
        s.close()
        return result != 0
    except Exception:
        return False

if __name__ == "__main__":
    port = 8000
    host = "0.0.0.0"
    
    print("🚀 Starting CropBox FastAPI Server")
    print("=" * 50)
    
    # Get local IP
    local_ip = get_local_ip()
    print(f"📡 Local IP Address: {local_ip}")
    
    # Check if port is available
    if not check_port_available(port):
        print(f"❌ Port {port} is already in use!")
        print("   Try killing the existing process or use a different port")
        sys.exit(1)
    
    print(f"🔍 Server will be available at:")
    print(f"   - Local: http://localhost:{port}")
    print(f"   - Network: http://{local_ip}:{port}")
    print(f"   - Health check: http://{local_ip}:{port}/health")
    print("=" * 50)
    print("🟢 Server starting...")
    
    try:
        uvicorn.run(
            app, 
            host=host, 
            port=port,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
