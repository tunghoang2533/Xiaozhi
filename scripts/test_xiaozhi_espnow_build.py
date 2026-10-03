import os
import unittest
import struct

class TestXiaozhiEspNowBuild(unittest.TestCase):
    def setUp(self):
        self.repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.lamp_ctrl_path = os.path.join(
            self.repo_dir, "xiaozhi-esp32-main", "main", "boards", "common", "lamp_controller.h"
        )
        self.board_config_path = os.path.join(
            self.repo_dir, "xiaozhi-esp32-main", "main", "boards", "bread-compact-wifi-lcd", "config.h"
        )
        self.bin_path = os.path.join(
            self.repo_dir, "xiaozhi-esp32-main", "build", "xiaozhi.bin"
        )

    def test_lamp_controller_espnow_integration(self):
        self.assertTrue(os.path.exists(self.lamp_ctrl_path), "lamp_controller.h must exist")
        with open(self.lamp_ctrl_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check DeskCommandPacket
        self.assertIn("struct __attribute__((packed)) DeskCommandPacket", content)
        self.assertIn("uint8_t magic; // 0x5A", content)
        self.assertIn("uint8_t cmd;", content)

        # Check ESP-NOW APIs
        self.assertIn("esp_now_init()", content)
        self.assertIn("esp_now_send(", content)
        self.assertIn("esp_now_add_peer(", content)
        self.assertIn("esp_wifi_get_channel(", content)

        # Check MCP Tools
        self.assertIn("self.lamp.turn_on", content)
        self.assertIn("self.lamp.turn_off", content)
        self.assertIn("self.c3.switch", content)
        self.assertIn("self.relay.control", content)

    def test_board_pinout_and_lcd_config(self):
        self.assertTrue(os.path.exists(self.board_config_path), "config.h must exist")
        with open(self.board_config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check LCD pins
        self.assertIn("#define DISPLAY_MOSI_PIN      GPIO_NUM_41", content)
        self.assertIn("#define DISPLAY_CLK_PIN       GPIO_NUM_42", content)
        self.assertIn("#define DISPLAY_DC_PIN        GPIO_NUM_43", content)
        self.assertIn("#define DISPLAY_RST_PIN       GPIO_NUM_44", content)
        self.assertIn("#define DISPLAY_CS_PIN        GPIO_NUM_NC", content)
        self.assertIn("#define DISPLAY_BACKLIGHT_PIN GPIO_NUM_NC", content)

        # Check ST7735 80x160 settings
        self.assertIn("#define DISPLAY_WIDTH   80", content)
        self.assertIn("#define DISPLAY_HEIGHT  160", content)
        self.assertIn("#define DISPLAY_OFFSET_X  26", content)

        # Check Audio pins
        self.assertIn("#define AUDIO_I2S_SPK_GPIO_BCLK GPIO_NUM_15", content)
        self.assertIn("#define LAMP_GPIO GPIO_NUM_NC", content)

    def test_compiled_firmware_binary(self):
        self.assertTrue(os.path.exists(self.bin_path), "xiaozhi.bin must exist")
        file_size = os.path.getsize(self.bin_path)
        self.assertGreater(file_size, 1000000, "Firmware size should be > 1MB")

        with open(self.bin_path, "rb") as f:
            header = f.read(4)
            # ESP32-S3 image magic byte is 0xE9
            self.assertEqual(header[0], 0xE9, "Image must begin with ESP image magic byte 0xE9")

if __name__ == "__main__":
    unittest.main()
