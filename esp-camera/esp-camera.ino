/*
 * ESP32-S3 Camera - Send Images to Server
 * 
 * Captures and sends JPEG images to FastAPI server every 10 seconds
 * 
 * Required Libraries:
 * - ESP32 Camera (built-in)
 * - WiFi (built-in)
 * - HTTPClient (built-in)
 */

 #include "esp_camera.h"
 #include "WiFi.h"
 #include "HTTPClient.h"
 
 // WiFi credentials
 const char* ssid = "hridoy";
 const char* password = "arafat4542";
 
 // FastAPI Server endpoint
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
     Serial.println("║  ESP32-S3 Image Sender                 ║");
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
         Serial.println("❌ Camera initialization failed!");
         while(1) {
             digitalWrite(LED_PIN, !digitalRead(LED_PIN));
             delay(200);
         }
     }
     
     Serial.println("\n✅ System ready!");
     Serial.println("📸 Starting image capture every 10 seconds...\n");
 }
 
 void loop() {
     // Check WiFi connection
     if (WiFi.status() != WL_CONNECTED) {
         Serial.println("📡 WiFi disconnected, reconnecting...");
         connectWiFi();
         delay(1000);
         return;
     }
     
     // Capture image
     camera_fb_t *fb = esp_camera_fb_get();
     if (!fb) {
         Serial.println("❌ Camera capture failed");
         delay(1000);
         return;
     }
     
     Serial.printf("📷 Image captured: %d bytes (%.1f KB)\n", fb->len, fb->len / 1024.0);
     
     // Send image to server
     digitalWrite(LED_PIN, HIGH);
     bool success = sendImageToServer(fb->buf, fb->len);
     digitalWrite(LED_PIN, LOW);
     
     if (success) {
         Serial.println("✅ Image sent successfully\n");
     } else {
         Serial.println("❌ Failed to send image\n");
     }
     
     // Return frame buffer
     esp_camera_fb_return(fb);
     fb = nullptr;
     
     // Wait 10 seconds before next capture
     Serial.println("⏳ Waiting 10 seconds before next capture...");
     delay(10000);
 }
 
 void connectWiFi() {
     Serial.print("📡 Connecting to WiFi");
     WiFi.begin(ssid, password);
     
     int attempts = 0;
     while (WiFi.status() != WL_CONNECTED && attempts < 30) {
         delay(500);
         Serial.print(".");
         attempts++;
     }
     
     if (WiFi.status() == WL_CONNECTED) {
         Serial.println(" ✅");
         Serial.print("   IP address: ");
         Serial.println(WiFi.localIP());
         Serial.print("   Signal: ");
         Serial.print(WiFi.RSSI());
         Serial.println(" dBm");
     } else {
         Serial.println(" ❌");
         Serial.println("   WiFi connection failed!");
     }
 }
 
 void testServerConnection() {
     Serial.print("🔍 Testing server connection...");
     
     // Test TCP connection
     WiFiClient testClient;
     testClient.setTimeout(3000);
     if (!testClient.connect(serverHost, serverPort)) {
         Serial.println(" ❌");
         Serial.println("   Cannot connect to server");
         Serial.println("   Make sure server is running!");
         return;
     }
     testClient.stop();
     Serial.println(" ✅ Server is reachable");
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
         config.frame_size = FRAMESIZE_SVGA; // 800x600
         config.jpeg_quality = 10;
         config.fb_count = 1;
         config.fb_location = CAMERA_FB_IN_PSRAM;
     } else {
         config.frame_size = FRAMESIZE_QQVGA;
         config.jpeg_quality = 12;
         config.fb_count = 1;
     }
     
     esp_err_t err = esp_camera_init(&config);
     if (err != ESP_OK) {
         Serial.printf("Camera init failed: 0x%x\n", err);
         return false;
     }
     
     // Apply sensor settings
     sensor_t *s = esp_camera_sensor_get();
     if (s != NULL) {
         s->set_brightness(s, 0);
         s->set_contrast(s, 0);
         s->set_saturation(s, 0);
         s->set_special_effect(s, 0);
         s->set_whitebal(s, 1);
         s->set_awb_gain(s, 1);
         s->set_wb_mode(s, 0);
         s->set_exposure_ctrl(s, 1);
         s->set_aec2(s, 0);
         s->set_ae_level(s, 0);
         s->set_aec_value(s, 300);
         s->set_gain_ctrl(s, 1);
         s->set_agc_gain(s, 0);
         s->set_gainceiling(s, (gainceiling_t)0);
         s->set_bpc(s, 0);
         s->set_wpc(s, 1);
         s->set_raw_gma(s, 1);
         s->set_lenc(s, 1);
         s->set_hmirror(s, 0);
         s->set_vflip(s, 0);
         s->set_dcw(s, 1);
         s->set_colorbar(s, 0);
     }
     
     Serial.println("✅ Camera initialized successfully");
     return true;
 }
 
 bool sendImageToServer(uint8_t *imageData, size_t imageSize) {
     if (WiFi.status() != WL_CONNECTED) {
         Serial.println("❌ WiFi not connected!");
         return false;
     }
     
     HTTPClient http;
     String url = String("http://") + serverHost + ":" + serverPort + "/upload-image";
     
     http.begin(url);
     http.addHeader("Content-Type", "image/jpeg");
     http.setTimeout(15000); // 15 second timeout for image upload
     
     Serial.println("📤 Sending image to server...");
     unsigned long startTime = millis();
     
     int httpResponseCode = http.POST(imageData, imageSize);
     
     unsigned long endTime = millis();
     Serial.printf("⏱️  Upload took: %lu ms\n", endTime - startTime);
     
     bool success = false;
     
     if (httpResponseCode > 0) {
         Serial.printf("📄 HTTP Response: %d\n", httpResponseCode);
         
         if (httpResponseCode == 200) {
             String response = http.getString();
             Serial.printf("   Server response: %s\n", response.c_str());
             success = true;
         } else {
             Serial.printf("⚠️  HTTP Error: %d\n", httpResponseCode);
             String errorResponse = http.getString();
             if (errorResponse.length() > 0) {
                 Serial.printf("   Error details: %s\n", errorResponse.c_str());
             }
         }
     } else {
         Serial.printf("❌ Request failed: %s\n", http.errorToString(httpResponseCode).c_str());
     }
     
     http.end();
     return success;
 }