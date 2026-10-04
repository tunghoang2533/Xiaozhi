#include <ESP8266WiFi.h>
#include <espnow.h>

#define RADAR_PIN   D2 // GPIO4 - LD2410 OUT pin
#define RELAY_PIN   D1 // GPIO5 - Relay IN1 pin

// Relay Polarity:
// true  = Active LOW (Standard for 2-channel optocoupler relay module with Jumper at 'L')
// false = Active HIGH (Standard for 1-channel transistor relay module / Jumper at 'H')
// Can be toggled at runtime via Serial command 'P'
bool relayActiveLow = false;

#define AUTO_OFF_TIMEOUT_MS 15000 // 15 seconds timeout for demo (30s in production)

// Known SSIDs to scan and synchronize Wi-Fi channel with ESP32-S3
const char* KNOWN_SSIDS[] = {
    "TP-Link_C710",
    "Tung Quan",
    "Tp_LinkC6F2",
    "Xiaozhi-DD2D"
};
const char* KNOWN_PASSWORDS[] = {
    "49878080",
    "23101272005",
    "123456789",
    ""
};
const int KNOWN_NETWORKS_COUNT = 4;

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
int currentChannel = 10; // Default to Channel 10 based on local environment

// Debounce filter for radar
int lastRawRadar = -1;
unsigned long rawRadarChangeMs = 0;
bool debouncedOccupied = false;

void setRelay(bool turnOn) {
    currentLampState = turnOn;
    int pinLevel = turnOn ? (relayActiveLow ? LOW : HIGH) : (relayActiveLow ? HIGH : LOW);
    digitalWrite(RELAY_PIN, pinLevel);
    Serial.printf("[RELAY] State set to: %s (Pin D1 = %s | ActiveLow: %s)\n", 
                  turnOn ? "ON (Lamp Sang)" : "OFF (Lamp Tat)", 
                  pinLevel == LOW ? "LOW" : "HIGH",
                  relayActiveLow ? "YES" : "NO");
}

void onDataRecv(uint8_t * mac, uint8_t *incomingData, uint8_t len) {
    if (len == sizeof(DeskCommandPacket)) {
        memcpy(&rxPacket, incomingData, sizeof(rxPacket));
        if (rxPacket.magic == 0x5A) {
            Serial.printf("[ESP-NOW] Received Cmd: %d (%s) from MAC %02X:%02X:%02X:%02X:%02X:%02X\n",
                          rxPacket.cmd,
                          rxPacket.cmd == 1 ? "FORCE ON" : (rxPacket.cmd == 0 ? "FORCE OFF" : "AUTO"),
                          mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
            if (rxPacket.cmd == 1) { // Force On
                manualOverride = true;
                setRelay(true);
                lastOccupiedMs = millis(); // Refresh activity
            } else if (rxPacket.cmd == 0) { // Force Off
                manualOverride = true;
                setRelay(false);
            } else if (rxPacket.cmd == 2) { // Auto
                manualOverride = false;
                Serial.println("[ESP-NOW] Reset to AUTO mode");
                if (debouncedOccupied) {
                    setRelay(true);
                } else {
                    setRelay(false);
                }
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

    pinMode(RADAR_PIN, INPUT_PULLUP);
    pinMode(RELAY_PIN, OUTPUT);
    setRelay(false); // Default OFF

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    delay(100);

    // Auto-discover router WiFi channel to match ESP32-S3
    Serial.println("[WIFI] Scanning networks to synchronize channel with ESP32...");
    int n = WiFi.scanNetworks();
    int targetChannel = 10; // Default to 10
    int matchedIdx = -1;

    for (int i = 0; i < n; i++) {
        String ssid = WiFi.SSID(i);
        int ch = WiFi.channel(i);
        Serial.printf("[WIFI] Found SSID: %-25s | Ch: %2d | RSSI: %3d dBm\n", ssid.c_str(), ch, (int)WiFi.RSSI(i));
        for (int k = 0; k < KNOWN_NETWORKS_COUNT; k++) {
            if (ssid == KNOWN_SSIDS[k]) {
                targetChannel = ch;
                matchedIdx = k;
                Serial.printf("[WIFI] >>> MATCHED Known Network: %s on Channel %d!\n", ssid.c_str(), ch);
                break;
            }
        }
        if (matchedIdx >= 0) break;
    }

    currentChannel = targetChannel;

    // Lock Wi-Fi channel in unassociated STA mode with sleep disabled (NONE_SLEEP_T)
    // This guarantees:
    // 1. Radio is 100% awake listening for ESP-NOW frames (Zero modem-sleep drops)
    // 2. No AP BSSID filtering
    // 3. Instant startup (<100ms)
    WiFi.disconnect();
    WiFi.mode(WIFI_STA);
    wifi_set_sleep_type(NONE_SLEEP_T);
    wifi_promiscuous_enable(1);
    wifi_set_channel(currentChannel);
    wifi_promiscuous_enable(0);
    Serial.printf("[WIFI] Radio locked to Channel %d (NONE_SLEEP, 100%% active listening)\n", currentChannel);

    if (esp_now_init() != 0) {
        Serial.println("[ESP-NOW] Init Failed!");
    } else {
        Serial.printf("[ESP-NOW] Init Success on Channel %d!\n", currentChannel);
        esp_now_set_self_role(ESP_NOW_ROLE_COMBO);
        esp_now_register_recv_cb(onDataRecv);
        esp_now_add_peer(broadcastAddress, ESP_NOW_ROLE_COMBO, currentChannel, NULL, 0);
    }
}

void loop() {
    unsigned long now = millis();

    // 1. Debounce Radar Input (D2)
    int rawRadar = digitalRead(RADAR_PIN);
    if (rawRadar != lastRawRadar) {
        lastRawRadar = rawRadar;
        rawRadarChangeMs = now;
    }

    // Require stable signal for at least 100ms before changing debounced state
    if (now - rawRadarChangeMs >= 100) {
        bool newOccupied = (rawRadar == HIGH); // LD2410: HIGH = target detected
        if (newOccupied != debouncedOccupied) {
            debouncedOccupied = newOccupied;
            if (debouncedOccupied) {
                Serial.println("[RADAR] Phat hien nguoi ngoi vao ban! (D2 = HIGH confirmed)");
            } else {
                Serial.println("[RADAR] Phat hien roi ban (D2 = LOW confirmed)");
            }
        }
    }

    // 2. Desk Ergonomics & Automation Logic
    if (debouncedOccupied) {
        lastOccupiedMs = now;
        if (!currentSittingState) {
            currentSittingState = true;
            sittingStartMs = now;
            Serial.println("[DESK] Bat dau dem thoi gian ngoi ban lam viec!");
        }
        totalSittingSec = (now - sittingStartMs) / 1000;

        // Auto-turn-on lamp if no manual override is active
        if (!manualOverride && !currentLampState) {
            setRelay(true);
        }
    } else {
        // Person is away
        if (now - lastOccupiedMs >= AUTO_OFF_TIMEOUT_MS) {
            if (currentSittingState || manualOverride || currentLampState) {
                currentSittingState = false;
                manualOverride = false; // Always clear override when desk is empty for timeout
                Serial.println("[DESK] Roi ban (het timeout)! Chuyen ve che do tu dong.");
                if (currentLampState) {
                    setRelay(false);
                }
            }
        }
    }

    // 3. Serial Command Interface for Testing & Calibration
    if (Serial.available()) {
        char c = Serial.read();
        if (c == '1') {
            Serial.println("[SERIAL] Manual Command: Turn ON");
            manualOverride = true;
            setRelay(true);
            lastOccupiedMs = now;
        } else if (c == '0') {
            Serial.println("[SERIAL] Manual Command: Turn OFF");
            manualOverride = true;
            setRelay(false);
        } else if (c == 'a' || c == 'A') {
            Serial.println("[SERIAL] Manual Command: Reset AUTO mode");
            manualOverride = false;
            if (debouncedOccupied) setRelay(true); else setRelay(false);
        } else if (c == 'p' || c == 'P') {
            relayActiveLow = !relayActiveLow;
            Serial.printf("[SERIAL] Toggled Relay Polarity: ActiveLow is now %s\n", relayActiveLow ? "TRUE" : "FALSE");
            setRelay(currentLampState); // Re-apply with new polarity
        } else if (c == 's' || c == 'S') {
            Serial.printf("[DIAG] Sitting: %d | Lamp: %d | Time: %lus | Radar(D2): %d | Ch: %d | ActiveLow: %s\n",
                          currentSittingState ? 1 : 0, currentLampState ? 1 : 0,
                          currentSittingState ? totalSittingSec : 0,
                          rawRadar, currentChannel, relayActiveLow ? "YES" : "NO");
        }
    }

    // 4. Send Status Report Every 1 Second via ESP-NOW Broadcast
    if (now - lastStatusReportMs >= 1000) {
        lastStatusReportMs = now;
        statusPacket.magic = 0xA5;
        statusPacket.is_sitting = currentSittingState ? 1 : 0;
        statusPacket.lamp_state = currentLampState ? 1 : 0;
        statusPacket.sitting_time_sec = currentSittingState ? totalSittingSec : 0;

        esp_now_send(broadcastAddress, (uint8_t *) &statusPacket, sizeof(statusPacket));

        Serial.printf("[STATUS] Sitting: %d | Lamp: %d | Time: %lus | Radar (D2): %s (raw=%d) | Ch: %d\n",
                      statusPacket.is_sitting,
                      statusPacket.lamp_state,
                      statusPacket.sitting_time_sec,
                      debouncedOccupied ? "HIGH" : "LOW",
                      rawRadar,
                      currentChannel);
    }

    delay(20);
}
