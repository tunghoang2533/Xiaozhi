#ifndef __LAMP_CONTROLLER_H__
#define __LAMP_CONTROLLER_H__

#include "mcp_server.h"
#include <esp_log.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <string.h>

#define TAG_LAMP "LampController"

struct __attribute__((packed)) DeskCommandPacket {
    uint8_t magic; // 0x5A
    uint8_t cmd;   // 0: Off, 1: On, 2: Auto
};

class LampController {
private:
    bool power_ = false;
    gpio_num_t gpio_num_;
    bool esp_now_initialized_ = false;
    uint8_t broadcast_mac_[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

    void InitEspNow() {
        if (esp_now_initialized_) return;
        esp_err_t err = esp_now_init();
        if (err != ESP_OK && err != ESP_ERR_ESPNOW_EXIST) {
            ESP_LOGW(TAG_LAMP, "ESP-NOW init failed: %s", esp_err_to_name(err));
            return;
        }
        esp_now_peer_info_t peer = {};
        memcpy(peer.peer_addr, broadcast_mac_, 6);
        peer.channel = 0; // 0 = auto-follow STA channel (Channel 10)
        peer.ifidx = WIFI_IF_STA;
        peer.encrypt = false;
        err = esp_now_add_peer(&peer);
        if (err != ESP_OK && err != ESP_ERR_ESPNOW_EXIST) {
            ESP_LOGW(TAG_LAMP, "ESP-NOW add broadcast peer: %s", esp_err_to_name(err));
        }
        esp_now_initialized_ = true;
        ESP_LOGI(TAG_LAMP, "ESP-NOW broadcast peer registered (channel 0 auto-follow STA)");
    }

    void SendEspNowCommand(uint8_t cmd) {
        InitEspNow();
        // Fully wake WiFi modem to ensure RF transmitter is 100% active
        esp_wifi_set_ps(WIFI_PS_NONE);
        DeskCommandPacket pkt = {0x5A, cmd};
        for (int i = 0; i < 6; i++) {
            esp_err_t err = esp_now_send(broadcast_mac_, (uint8_t*)&pkt, sizeof(pkt));
            ESP_LOGI(TAG_LAMP, "Sent ESP-NOW command: %d (%s) burst %d/6, err=%d", 
                     cmd, cmd == 1 ? "ON" : (cmd == 0 ? "OFF" : "AUTO"), i + 1, (int)err);
            vTaskDelay(pdMS_TO_TICKS(15));
        }
        // Restore modem power save after burst
        esp_wifi_set_ps(WIFI_PS_MAX_MODEM);
    }

public:
    LampController(gpio_num_t gpio_num) : gpio_num_(gpio_num) {
        if (gpio_num_ != GPIO_NUM_NC) {
            gpio_config_t config = {
                .pin_bit_mask = (1ULL << gpio_num_),
                .mode = GPIO_MODE_OUTPUT,
                .pull_up_en = GPIO_PULLUP_DISABLE,
                .pull_down_en = GPIO_PULLDOWN_DISABLE,
                .intr_type = GPIO_INTR_DISABLE,
            };
            gpio_config(&config);
            gpio_set_level(gpio_num_, 0);
        }

        auto& mcp_server = McpServer::GetInstance();

        // 1. Official Lamp MCP tools
        mcp_server.AddTool("self.lamp.get_state", "Get the power state of the lamp", PropertyList(), [this](const PropertyList& properties) -> ReturnValue {
            return power_ ? "{\"power\": true}" : "{\"power\": false}";
        });

        mcp_server.AddTool("self.lamp.turn_on", "Turn on the lamp / Bat den ban / Bat den / Bat thiet bi", PropertyList(), [this](const PropertyList& properties) -> ReturnValue {
            ESP_LOGI(TAG_LAMP, "MCP Tool called: self.lamp.turn_on");
            power_ = true;
            if (gpio_num_ != GPIO_NUM_NC) {
                gpio_set_level(gpio_num_, 1);
            }
            SendEspNowCommand(1);
            return true;
        });

        mcp_server.AddTool("self.lamp.turn_off", "Turn off the lamp / Tat den ban / Tat den / Tat thiet bi", PropertyList(), [this](const PropertyList& properties) -> ReturnValue {
            ESP_LOGI(TAG_LAMP, "MCP Tool called: self.lamp.turn_off");
            power_ = false;
            if (gpio_num_ != GPIO_NUM_NC) {
                gpio_set_level(gpio_num_, 0);
            }
            SendEspNowCommand(0);
            return true;
        });

        mcp_server.AddTool("self.lamp.set_auto", "Chuyen den ban ve che do tu dong theo cam bien radar / Reset auto mode", PropertyList(), [this](const PropertyList& properties) -> ReturnValue {
            ESP_LOGI(TAG_LAMP, "MCP Tool called: self.lamp.set_auto");
            SendEspNowCommand(2);
            return true;
        });

        // 1b. Light aliases
        mcp_server.AddTool("self.light.get_state", "Get the power state of the light", PropertyList(), [this](const PropertyList& properties) -> ReturnValue {
            return power_ ? "{\"power\": true}" : "{\"power\": false}";
        });

        mcp_server.AddTool("self.light.turn_on", "Turn on the light / Bat den", PropertyList(), [this](const PropertyList& properties) -> ReturnValue {
            ESP_LOGI(TAG_LAMP, "MCP Tool called: self.light.turn_on");
            power_ = true;
            if (gpio_num_ != GPIO_NUM_NC) {
                gpio_set_level(gpio_num_, 1);
            }
            SendEspNowCommand(1);
            return true;
        });

        mcp_server.AddTool("self.light.turn_off", "Turn off the light / Tat den", PropertyList(), [this](const PropertyList& properties) -> ReturnValue {
            ESP_LOGI(TAG_LAMP, "MCP Tool called: self.light.turn_off");
            power_ = false;
            if (gpio_num_ != GPIO_NUM_NC) {
                gpio_set_level(gpio_num_, 0);
            }
            SendEspNowCommand(0);
            return true;
        });

        // 2. Xiaozhi Vietnamese cloud C3 switch tool (bật/tắt đèn smarthome)
        mcp_server.AddTool("self.c3.switch", "Dieu khien bat tat den hoac thiet bi", PropertyList({
            Property("value", kPropertyTypeInteger, 1),
            Property("label", kPropertyTypeString, std::string("")),
            Property("nodeId", kPropertyTypeString, std::string(""))
        }), [this](const PropertyList& properties) -> ReturnValue {
            int val = properties["value"].value<int>();
            ESP_LOGI(TAG_LAMP, "MCP Tool called: self.c3.switch, value=%d", val);
            if (val == 1) {
                power_ = true;
                if (gpio_num_ != GPIO_NUM_NC) {
                    gpio_set_level(gpio_num_, 1);
                }
                SendEspNowCommand(1);
            } else {
                power_ = false;
                if (gpio_num_ != GPIO_NUM_NC) {
                    gpio_set_level(gpio_num_, 0);
                }
                SendEspNowCommand(0);
            }
            return std::string("{\"ok\":true}");
        });

        // 3. Xiaozhi Relay control tool
        mcp_server.AddTool("self.relay.control", "Dieu khien relay hoac cong tac", PropertyList({
            Property("relay", kPropertyTypeInteger, 1),
            Property("action", kPropertyTypeString, std::string("turn_on")),
            Property("duration_ms", kPropertyTypeInteger, 0)
        }), [this](const PropertyList& properties) -> ReturnValue {
            std::string action = properties["action"].value<std::string>();
            ESP_LOGI(TAG_LAMP, "MCP Tool called: self.relay.control, action=%s", action.c_str());
            if (action == "turn_on" || action == "1" || action == "on") {
                power_ = true;
                if (gpio_num_ != GPIO_NUM_NC) {
                    gpio_set_level(gpio_num_, 1);
                }
                SendEspNowCommand(1);
            } else if (action == "turn_off" || action == "0" || action == "off") {
                power_ = false;
                if (gpio_num_ != GPIO_NUM_NC) {
                    gpio_set_level(gpio_num_, 0);
                }
                SendEspNowCommand(0);
            } else if (action == "toggle") {
                power_ = !power_;
                if (gpio_num_ != GPIO_NUM_NC) {
                    gpio_set_level(gpio_num_, power_ ? 1 : 0);
                }
                SendEspNowCommand(power_ ? 1 : 0);
            }
            return std::string("{\"ok\":true}");
        });
    }
};

#endif // __LAMP_CONTROLLER_H__
