#include <WiFi.h>
#include <esp_now.h>

#define BOARD_NAME "ESP32-S3 MASTER"

struct __attribute__((packed)) DeskCommandPacket {
    uint8_t magic; // 0x5A
    uint8_t cmd;   // 0: Off, 1: On, 2: Auto
};

struct __attribute__((packed)) DeskStatusPacket {
    uint8_t  magic;             // 0xA5
    uint8_t  is_sitting;        // 1: sitting, 0: left
    uint8_t  lamp_state;        // 1: on, 0: off
    uint32_t sitting_time_sec; // sitting duration
};

uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

void sendEspNowCommand(uint8_t cmd) {
    DeskCommandPacket pkt;
    pkt.magic = 0x5A;
    pkt.cmd = cmd;
    esp_now_send(broadcastAddress, (uint8_t *)&pkt, sizeof(pkt));
    Serial.printf("[ESP32-S3] Sent ESP-NOW Cmd: %d (%s)\n", cmd, cmd == 1 ? "ON" : "OFF");
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n==========================================");
    Serial.println(" SMART DESK ASSISTANT - ESP32-S3 MASTER ");
    Serial.println("==========================================");

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    if (esp_now_init() != ESP_OK) {
        Serial.println("[ESP-NOW] Init Failed!");
        return;
    }

    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, broadcastAddress, 6);
    peerInfo.channel = 0;
    peerInfo.encrypt = false;

    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
        Serial.println("[ESP-NOW] Failed to add peer!");
        return;
    }

    Serial.println("[ESP-NOW] Master Initialized successfully!");
}

void loop() {
    if (Serial.available()) {
        char c = Serial.read();
        if (c == '1' || c == 'on' || c == 'O') {
            sendEspNowCommand(1);
        } else if (c == '0' || c == 'off' || c == 'F') {
            sendEspNowCommand(0);
        }
    }
    delay(50);
}
