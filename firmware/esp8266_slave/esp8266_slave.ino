#include <ESP8266WiFi.h>
#include <espnow.h>
#include <EEPROM.h>

#define RADAR_PIN   D2 // GPIO4 - LD2410 OUT pin
#define RELAY_PIN   D1 // GPIO5 - Relay IN1 pin

#define EEPROM_MAGIC 0x55

// Relay Polarity:
// true  = Active LOW (Standard for 2-channel optocoupler relay module with Jumper at 'L')
// false = Active HIGH (Standard for 1-channel transistor relay module / Jumper at 'H')
// Can be toggled at runtime via Serial command 'P' and saved to EEPROM
bool relayActiveLow = false;

// Radar Logic:
// true  = Active HIGH (HLK-LD2410 default: 3.3V/HIGH = person detected, 0V/LOW = unoccupied)
// false = Active LOW (Inverted: LOW = person detected, HIGH = unoccupied)
// Can be toggled at runtime via Serial command 'R' and saved to EEPROM
bool radarActiveHigh = true;

void saveSettings() {
    EEPROM.write(0, EEPROM_MAGIC);
    EEPROM.write(1, relayActiveLow ? 1 : 0);
    EEPROM.write(2, radarActiveHigh ? 1 : 0);
    EEPROM.commit();
    Serial.println("[CONFIG] Saved settings to EEPROM!");
}

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

enum ControlMode {
    MODE_AUTO = 0,       // Tự động bật/tắt theo cảm biến radar LD2410
    MODE_MANUAL_OFF = 1, // Ưu tiên ra lệnh TẮT: Đèn luôn TẮT, cảm biến KHÔNG được tự ý bật đèn
    MODE_MANUAL_ON = 2   // Ưu tiên ra lệnh BẬT: Đèn luôn BẬT, cảm biến KHÔNG được tự ý tắt đèn
};

// Global variables
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
DeskStatusPacket statusPacket;
DeskCommandPacket rxPacket;

ControlMode currentMode = MODE_AUTO;
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
            if (rxPacket.cmd == 1) { // Lệnh ép bật (Ưu tiên người dùng)
                currentMode = MODE_MANUAL_ON;
                setRelay(true);
                lastOccupiedMs = millis(); // Refresh activity
                Serial.println("[MODE] MANUAL_ON: Uu tien bat den, cam bien khong the tat den!");
            } else if (rxPacket.cmd == 0) { // Lệnh ép tắt (Ưu tiên người dùng)
                currentMode = MODE_MANUAL_OFF;
                setRelay(false);
                Serial.println("[MODE] MANUAL_OFF: Uu tien tat den, cam bien khong the tu dong bat den!");
            } else if (rxPacket.cmd == 2) { // Reset về chế độ Tự động
                currentMode = MODE_AUTO;
                Serial.println("[MODE] Reset to AUTO mode: Cam bien radar quan ly den.");
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

    EEPROM.begin(64);
    if (EEPROM.read(0) == EEPROM_MAGIC) {
        relayActiveLow = (EEPROM.read(1) == 1);
        radarActiveHigh = (EEPROM.read(2) == 1);
        Serial.printf("[CONFIG] Loaded settings from EEPROM: RelayActiveLow=%s, RadarActiveHigh=%s\n",
                      relayActiveLow ? "YES (Jumper L)" : "NO (Jumper H)",
                      radarActiveHigh ? "YES (HIGH=Occupied)" : "NO (LOW=Occupied)");
    } else {
        relayActiveLow = false; // Default Active HIGH matching user's relay hardware (HIGH = ON, LOW = OFF)
        radarActiveHigh = true; // Default LD2410 Active HIGH
        EEPROM.write(0, EEPROM_MAGIC);
        EEPROM.write(1, relayActiveLow ? 1 : 0);
        EEPROM.write(2, radarActiveHigh ? 1 : 0);
        EEPROM.commit();
        Serial.println("[CONFIG] Initialized default settings to EEPROM (RelayActiveLow=NO, RadarActiveHigh=YES)");
    }

    pinMode(RADAR_PIN, INPUT);
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
        bool newOccupied = radarActiveHigh ? (rawRadar == HIGH) : (rawRadar == LOW);
        if (newOccupied != debouncedOccupied) {
            debouncedOccupied = newOccupied;
            if (debouncedOccupied) {
                Serial.printf("[RADAR] Phat hien nguoi ngoi vao ban! (D2=%s, Logic=%s)\n",
                              rawRadar == HIGH ? "HIGH" : "LOW",
                              radarActiveHigh ? "Active-HIGH" : "Active-LOW");
            } else {
                Serial.printf("[RADAR] Phat hien roi ban (D2=%s, Logic=%s)\n",
                              rawRadar == HIGH ? "HIGH" : "LOW",
                              radarActiveHigh ? "Active-HIGH" : "Active-LOW");
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

        // Xử lý bật/tắt đèn theo độ ưu tiên:
        if (currentMode == MODE_AUTO) {
            // Chế độ tự động: Bật đèn khi phát hiện người ngồi vào bàn
            if (!currentLampState) {
                setRelay(true);
            }
        } else if (currentMode == MODE_MANUAL_OFF) {
            // ƯU TIÊN LỆNH TẮT HƠN CẢM BIẾN:
            // Người dùng đã ra lệnh TẮT -> Giữ đèn luôn TẮT, cảm biến radar KHÔNG được tự ý bật đèn!
            if (currentLampState) {
                setRelay(false);
            }
        } else if (currentMode == MODE_MANUAL_ON) {
            // ƯU TIÊN LỆNH BẬT:
            // Người dùng đã ra lệnh BẬT -> Giữ đèn luôn BẬT!
            if (!currentLampState) {
                setRelay(true);
            }
        }
    } else {
        // Cảm biến không thấy người (vắng mặt)
        if (now - lastOccupiedMs >= AUTO_OFF_TIMEOUT_MS) {
            if (currentSittingState) {
                currentSittingState = false;
                Serial.println("[DESK] Nguoi dung da roi ban (het timeout)!");
            }

            if (currentMode == MODE_AUTO) {
                // Ở chế độ tự động: Vắng người quá timeout -> Tắt đèn
                if (currentLampState) {
                    setRelay(false);
                }
            }
        }

        // Hoàn nguyên an toàn sau khi rời bàn rất lâu (5 phút = 300,000 ms vắng mặt liên tục)
        // Khi người dùng đã rời bàn hẳn và không sử dụng, tự động trả về MODE_AUTO cho phiên sau
        if (now - lastOccupiedMs >= 300000UL) {
            if (currentMode != MODE_AUTO) {
                currentMode = MODE_AUTO;
                Serial.println("[DESK] Vang mat hon 5 phut, tu dong khoi phuc che do AUTO cho lan sau!");
            }
        }
    }

    // 3. Serial Command Interface for Testing & Calibration
    if (Serial.available()) {
        char c = Serial.read();
        if (c == '1') {
            Serial.println("[SERIAL] Manual Command: Turn ON");
            currentMode = MODE_MANUAL_ON;
            setRelay(true);
            lastOccupiedMs = now;
        } else if (c == '0') {
            Serial.println("[SERIAL] Manual Command: Turn OFF (Priority over sensor)");
            currentMode = MODE_MANUAL_OFF;
            setRelay(false);
        } else if (c == 'a' || c == 'A') {
            Serial.println("[SERIAL] Manual Command: Reset AUTO mode");
            currentMode = MODE_AUTO;
            if (debouncedOccupied) setRelay(true); else setRelay(false);
        } else if (c == 'p' || c == 'P') {
            relayActiveLow = !relayActiveLow;
            saveSettings();
            Serial.printf("[SERIAL] Toggled Relay Polarity: ActiveLow is now %s (Saved to EEPROM)\n", 
                          relayActiveLow ? "YES (Jumper L)" : "NO (Jumper H)");
            setRelay(currentLampState); // Re-apply with new polarity
        } else if (c == 'r' || c == 'R') {
            radarActiveHigh = !radarActiveHigh;
            saveSettings();
            Serial.printf("[SERIAL] Toggled Radar Logic: ActiveHigh is now %s (Saved to EEPROM)\n", 
                          radarActiveHigh ? "YES (HIGH=Occupied)" : "NO (LOW=Occupied)");
        } else if (c == 's' || c == 'S') {
            const char* modeStr = (currentMode == MODE_AUTO) ? "AUTO" : 
                                  ((currentMode == MODE_MANUAL_OFF) ? "MANUAL_OFF" : "MANUAL_ON");
            Serial.printf("[DIAG] Mode: %s | Sitting: %d | Lamp: %d | Time: %lus | Radar(D2): %d | Ch: %d | RelayActiveLow: %s | RadarActiveHigh: %s\n",
                          modeStr,
                          currentSittingState ? 1 : 0, currentLampState ? 1 : 0,
                          currentSittingState ? totalSittingSec : 0,
                          rawRadar, currentChannel,
                          relayActiveLow ? "YES (Jumper L)" : "NO (Jumper H)",
                          radarActiveHigh ? "YES (HIGH=Co nguoi)" : "NO (LOW=Co nguoi)");
        } else if (c == 'h' || c == 'H' || c == '?') {
            Serial.println("\n--- LENH DIEU KHIEN & HIEU CHINH ESP8266 ---");
            Serial.println(" '0' : Ep TAT den (Uu tien hon cam bien)");
            Serial.println(" '1' : Ep BAT den (Uu tien hon cam bien)");
            Serial.println(" 'a' : Chuyen ve che do TU DONG (AUTO)");
            Serial.println(" 'p' : Dao cuc Relay (Active-LOW <-> Active-HIGH) & Luu EEPROM");
            Serial.println(" 'r' : Dao cuc Radar (Active-HIGH <-> Active-LOW) & Luu EEPROM");
            Serial.println(" 's' : Xem chan doan trang thai chi tiet (Diagnostics)");
            Serial.println("----------------------------------------------\n");
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
