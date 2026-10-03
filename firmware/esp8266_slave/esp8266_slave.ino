#include <ESP8266WiFi.h>
#include <espnow.h>

#define RADAR_PIN   D2 // GPIO4 - LD2410 OUT pin
#define RELAY_PIN   D1 // GPIO5 - Relay IN1 pin

#define RELAY_ON    LOW
#define RELAY_OFF   HIGH

#define AUTO_OFF_TIMEOUT_MS 15000 // 15 seconds timeout for demo

// Structs matching project spec PHUONG_AN_KY_THUAT.md
struct __attribute__((packed)) DeskCommandPacket {
    uint8_t magic; // 0x5A
    uint8_t cmd;   // 0: Off, 1: On, 2: Auto
};

struct __attribute__((packed)) DeskStatusPacket {
    uint8_t  magic;             // 0xA5
    uint8_t  is_sitting;        // 1: sitting, 0: left
    uint8_t  lamp_state;        // 1: on, 0: off
    uint32_t sitting_time_sec; // sitting duration in seconds
};

// Global variables
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
DeskStatusPacket statusPacket;
DeskCommandPacket rxPacket;

bool manualOverride = false;
bool currentLampState = false;
bool currentSittingState = false;
unsigned long sittingStartMs = 0;
unsigned long totalSittingSec = 0;
unsigned long lastOccupiedMs = 0;
unsigned long lastStatusReportMs = 0;

void setRelay(bool turnOn) {
    currentLampState = turnOn;
    digitalWrite(RELAY_PIN, turnOn ? RELAY_ON : RELAY_OFF);
    Serial.printf("[RELAY] State set to: %s (Pin D1 = %s)\n", 
                  turnOn ? "ON (Lamp Sang)" : "OFF (Lamp Tat)", 
                  turnOn ? "LOW" : "HIGH");
}

void onDataRecv(uint8_t * mac, uint8_t *incomingData, uint8_t len) {
    if (len == sizeof(DeskCommandPacket)) {
        memcpy(&rxPacket, incomingData, sizeof(rxPacket));
        if (rxPacket.magic == 0x5A) {
            Serial.printf("[ESP-NOW] Received Cmd: %d\n", rxPacket.cmd);
            if (rxPacket.cmd == 1) { // Force On
                manualOverride = true;
                setRelay(true);
            } else if (rxPacket.cmd == 0) { // Force Off
                manualOverride = true;
                setRelay(false);
            } else if (rxPacket.cmd == 2) { // Auto
                manualOverride = false;
                Serial.println("[ESP-NOW] Reset to AUTO mode");
            }
        }
    }
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n==========================================");
    Serial.println(" SMART DESK ASSISTANT - ESP8266 SLAVE ");
    Serial.println("==========================================");

    pinMode(RADAR_PIN, INPUT);
    pinMode(RELAY_PIN, OUTPUT);
    setRelay(false); // Default OFF

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    if (esp_now_init() != 0) {
        Serial.println("[ESP-NOW] Init Failed!");
    } else {
        Serial.println("[ESP-NOW] Init Success!");
        esp_now_set_self_role(ESP_NOW_ROLE_COMBO);
        esp_now_register_recv_cb(onDataRecv);
        esp_now_add_peer(broadcastAddress, ESP_NOW_ROLE_COMBO, 1, NULL, 0);
    }
}

void loop() {
    unsigned long now = millis();
    int radarVal = digitalRead(RADAR_PIN);
    bool occupied = (radarVal == HIGH);

    if (occupied) {
        lastOccupiedMs = now;
        if (!currentSittingState) {
            currentSittingState = true;
            sittingStartMs = now;
            Serial.println("[RADAR] Phat hien nguoi ngoi vao ban! (D2 = HIGH)");
        }
        totalSittingSec = (now - sittingStartMs) / 1000;

        if (!manualOverride && !currentLampState) {
            setRelay(true);
        }
    } else {
        if (currentSittingState) {
            if (now - lastOccupiedMs >= AUTO_OFF_TIMEOUT_MS) {
                currentSittingState = false;
                manualOverride = false; // Reset manual override on leave
                Serial.println("[RADAR] Roi ban (het timeout)! (D2 = LOW)");
                if (currentLampState) {
                    setRelay(false);
                }
            }
        }
    }

    // Send status report every 1 second
    if (now - lastStatusReportMs >= 1000) {
        lastStatusReportMs = now;
        statusPacket.magic = 0xA5;
        statusPacket.is_sitting = currentSittingState ? 1 : 0;
        statusPacket.lamp_state = currentLampState ? 1 : 0;
        statusPacket.sitting_time_sec = currentSittingState ? totalSittingSec : 0;

        esp_now_send(broadcastAddress, (uint8_t *) &statusPacket, sizeof(statusPacket));

        Serial.printf("[STATUS] Sitting: %d | Lamp: %d | Time: %lus | Radar (D2): %s\n",
                      statusPacket.is_sitting,
                      statusPacket.lamp_state,
                      statusPacket.sitting_time_sec,
                      occupied ? "HIGH" : "LOW");
    }

    delay(50);
}
