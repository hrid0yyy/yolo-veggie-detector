/*
 * ESP32-S3 Camera - YOLO Object Detection
 * 
 * Captures images and sends them to YOLO detection API
 * Receives detected objects with bounding boxes in response
 * 
 * Required Libraries:
 * - ESP32 Camera (built-in)
 * - WiFi (built-in)
 * - HTTPClient (built-in)
 * - ArduinoJson (install from Library Manager)
 */

#include "esp_camera.h"
#include "WiFi.h"
#include "HTTPClient.h"
#include "ArduinoJson.h"

// WiFi credentials
const char* ssid = "hridoy";
const char* password = "arafat4542";

// YOLO API Server endpoint
const char* serverHost = "192.168.0.113";
const int serverPort = 8000;

// Camera pins for ESP32-S3
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     15
#define SIOD_GPIO_NUM     4
#define SIOC_GPIO_NUM     5
#define Y9_GPIO_NUM       16
#define Y8_GPIO_NUM       17
#define Y7_GPIO_NUM       18
#define Y6_GPIO_NUM       12
#define Y5_GPIO_NUM       10
#define Y4_GPIO_NUM       8
#define Y3_GPIO_NUM       9
#define Y2_GPIO_NUM       11
#define VSYNC_GPIO_NUM    6
#define HREF_GPIO_NUM     7
#define PCLK_GPIO_NUM     13

// LED pin
#define LED_PIN 21

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n\n╔════════════════════════════════════════╗");
    Serial.println("║  ESP32-S3 YOLO Object Detection       ║");
    Serial.println("╚════════════════════════════════════════╝\n");
    
    // Initialize LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    
    // Connect to WiFi
    connectWiFi();
    
    // Test server connection
    testServerConnection();
    
    // Initialize camera
    if (!initCamera()) {
        while(1) {
            digitalWrite(LED_PIN, !digitalRead(LED_PIN));
            delay(200);
        }
    }
}

void loop() {
    // Check WiFi connection
    if (WiFi.status() != WL_CONNECTED) {
        connectWiFi();
        delay(1000);
        return;
    }
    
    // Capture image
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        delay(1000);
        return;
    }
    
    // Send to YOLO detection API
    digitalWrite(LED_PIN, HIGH);
    bool success = sendToYoloAPI(fb->buf, fb->len);
    digitalWrite(LED_PIN, LOW);
    
    esp_camera_fb_return(fb);
    
    delay(1000); // Changed to 1 second
}

void connectWiFi() {
    WiFi.begin(ssid, password);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        attempts++;
    }
}

void testServerConnection() {
    HTTPClient http;
    String healthUrl = String("http://") + serverHost + ":" + serverPort + "/health";
    http.begin(healthUrl);
    http.setTimeout(5000);
    
    int httpCode = http.GET();
    
    http.end();
}

bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    
    if(psramFound()){
        config.frame_size = FRAMESIZE_SVGA; // 800x600 for better detection
        config.jpeg_quality = 10;
        config.fb_count = 1;
        config.fb_location = CAMERA_FB_IN_PSRAM;
    } else {
        config.frame_size = FRAMESIZE_VGA;
        config.jpeg_quality = 12;
        config.fb_count = 1;
    }
    
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        return false;
    }
    
    return true;
}

bool sendToYoloAPI(uint8_t *imageData, size_t imageSize) {
    if (WiFi.status() != WL_CONNECTED) {
        return false;
    }
    
    HTTPClient http;
    String url = String("http://") + serverHost + ":" + serverPort + "/yolo-detect";
    
    http.begin(url);
    http.addHeader("Content-Type", "image/jpeg");
    http.setTimeout(30000);
    
    int httpResponseCode = http.POST(imageData, imageSize);
    
    bool success = false;
    
    if (httpResponseCode > 0) {
        if (httpResponseCode == 200) {
            String response = http.getString();
            success = true;
            
            // Parse and display detection results
            parseYoloResults(response);
        }
    }
    
    http.end();
    return success;
}

void parseYoloResults(String jsonResponse) {
    StaticJsonDocument<1024> doc;
    DeserializationError error = deserializeJson(doc, jsonResponse);
    
    if (error) {
        return;
    }
    
    if (doc["status"] == "success") {
        JsonObject detection = doc["detection_results"];
        int totalObjects = detection["total_objects"];
        
        if (totalObjects > 0) {
            JsonArray objects = detection["objects_detected"];
            
            for (JsonVariant obj : objects) {
                String objectName = obj["object"];
                JsonObject bbox = obj["bounding_box"];
                
                Serial.printf("%s: x=%d, y=%d, w=%d, h=%d\n", 
                             objectName.c_str(),
                             (int)bbox["x1"], (int)bbox["y1"], 
                             (int)bbox["width"], (int)bbox["height"]);
            }
        } else {
            Serial.println("No object found");
        }
    } else {
        Serial.println("No object found");
    }
}
