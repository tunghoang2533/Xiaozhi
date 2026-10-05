/*
 * ====================================================================================
 * DỰ ÁN: TRỢ LÝ BÀN LÀM VIỆC THÔNG MINH (SMART DESK ASSISTANT)
 * TẬP TIN: esp32_master.ino (FIRMWARE BO CHÍNH: ESP32-S3 MASTER)
 * ====================================================================================
 * VAI TRÒ HỆ THỐNG:
 * - Đặt trên mặt bàn làm việc, tích hợp Mic + Loa I2S đàm thoại AI Xiaozhi và màn hình LCD.
 * - Nhận lệnh từ người dùng (qua giọng nói AI hoặc cổng Serial).
 * - Đóng gói dữ liệu và truyền không dây qua giao thức ESP-NOW tới Bo phụ ESP8266 dưới gầm bàn
 *   để điều khiển bật/tắt đèn và đồng bộ trạng thái (Độ trễ truyền nhận cực thấp < 5ms).
 * ====================================================================================
 */

#include <WiFi.h>
#include <esp_now.h>

#define BOARD_NAME "ESP32-S3 MASTER"

// ====================================================================================
// 1. CẤU TRÚC GÓI TIN TRUYỀN THÔNG ESP-NOW (PHẢI TRÙNG KHỚP 100% VỚI BO PHỤ ESP8266)
// ====================================================================================

// Gói tin gửi lệnh điều khiển từ Master (ESP32-S3) sang Slave (ESP8266)
struct __attribute__((packed)) DeskCommandPacket {
    uint8_t magic; // Mã nhận diện gói tin hợp lệ (0x5A)
    uint8_t cmd;   // Lệnh điều khiển: 0 = Ép TẮT đèn, 1 = Ép BẬT đèn, 2 = Chế độ TỰ ĐỘNG (AUTO)
};

// Gói tin nhận phản hồi trạng thái từ Slave (ESP8266) gửi về Master (ESP32-S3)
struct __attribute__((packed)) DeskStatusPacket {
    uint8_t  magic;            // Mã nhận diện gói tin trạng thái (0xA5)
    uint8_t  is_sitting;       // Trạng thái người ngồi: 1 = Có người ngồi tại bàn, 0 = Đã rời bàn
    uint8_t  lamp_state;       // Trạng thái đèn bàn: 1 = Đèn đang sáng, 0 = Đèn đang tắt
    uint32_t sitting_time_sec; // Tổng thời gian ngồi làm việc liên tục (tính bằng giây)
};

// Địa chỉ Broadcast MAC (FF:FF:FF:FF:FF:FF) để phát cho mọi thiết bị trong mạng ESP-NOW
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// ====================================================================================
// 2. HÀM GỬI LỆNH ĐIỀU KHIỂN SANG ESP8266 QUA ESP-NOW
// ====================================================================================
void sendEspNowCommand(uint8_t cmd) {
    DeskCommandPacket pkt;
    pkt.magic = 0x5A; // Gán mã định danh chuẩn
    pkt.cmd = cmd;    // 0: Tắt, 1: Bật, 2: Tự động
    
    // Gửi gói tin nhị phân qua giao thức ESP-NOW
    esp_now_send(broadcastAddress, (uint8_t *)&pkt, sizeof(pkt));
    Serial.printf("[ESP32-S3] Sent ESP-NOW Cmd: %d (%s)\n", cmd, cmd == 1 ? "ON" : "OFF");
}

// ====================================================================================
// 3. KHỞI TẠO HỆ THỐNG (SETUP)
// ====================================================================================
void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n==========================================");
    Serial.println(" SMART DESK ASSISTANT - ESP32-S3 MASTER ");
    Serial.println("==========================================");

    // Bắt buộc chuyển WiFi sang chế độ Station (STA) để giao thức ESP-NOW hoạt động
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    // Khởi tạo thư viện ESP-NOW trên ESP32-S3
    if (esp_now_init() != ESP_OK) {
        Serial.println("[ESP-NOW] Init Failed!");
        return;
    }

    // Đăng ký thiết bị nhận (Peer) là địa chỉ Broadcast
    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, broadcastAddress, 6);
    peerInfo.channel = 0;     // Kênh 0: Tự động dùng chung kênh WiFi hiện tại
    peerInfo.encrypt = false; // Không mã hóa để tối ưu tốc độ phản hồi (< 5ms)

    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
        Serial.println("[ESP-NOW] Failed to add peer!");
        return;
    }

    Serial.println("[ESP-NOW] Master Initialized successfully!");
}

// ====================================================================================
// 4. VÒNG LẶP CHÍNH (LOOP)
// ====================================================================================
void loop() {
    // Lắng nghe lệnh điều khiển từ cổng Serial máy tính hoặc kết nối AI
    if (Serial.available()) {
        char c = Serial.read();
        if (c == '1' || c == 'on' || c == 'O') {
            // Lệnh BẬT đèn thủ công
            sendEspNowCommand(1);
        } else if (c == '0' || c == 'off' || c == 'F') {
            // Lệnh TẮT đèn thủ công
            sendEspNowCommand(0);
        } else if (c == 'a' || c == 'A') {
            // Lệnh chuyển lại chế độ TỰ ĐỘNG theo cảm biến
            sendEspNowCommand(2);
        }
    }
    delay(50);
}
