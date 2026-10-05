import os
import struct
import zlib
import unittest

class TestFirmwareIntegrity(unittest.TestCase):
    def setUp(self):
        self.repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.firmware_bin = os.path.join(self.repo_dir, "s3timtft096b.bin")
        self.nvs_bin = os.path.join(self.repo_dir, "nvs_configured.bin")

    def test_firmware_psram_mode(self):
        self.assertTrue(os.path.exists(self.firmware_bin), "s3timtft096b.bin must exist")
        with open(self.firmware_bin, 'rb') as f:
            data = f.read()
        self.assertIn(b'octal_psram', data, "Firmware must support Octal PSRAM for ESP32-S3 N16R8")
        self.assertNotIn(b'quad_psram', data, "Firmware must not use Quad PSRAM mode which crashes N16R8")

    def test_nvs_speaker_lamp_conflict(self):
        self.assertTrue(os.path.exists(self.nvs_bin), "nvs_configured.bin must exist")
        with open(self.nvs_bin, 'rb') as f:
            data = bytearray(f.read())
        self.assertEqual(len(data), 16384, "NVS partition must be 16KB")

        page0 = data[0:4096]
        bitmap0 = page0[32:64]

        keys = {}
        entry_idx = 0
        while entry_idx < 126:
            byte_idx = (entry_idx * 2) // 8
            bit_offset = (entry_idx * 2) % 8
            state_bits = (bitmap0[byte_idx] >> bit_offset) & 0x03
            if state_bits != 0x02:
                entry_idx += 1
                continue

            offset = 64 + entry_idx * 32
            entry = page0[offset : offset + 32]
            ns_idx, val_type, span, chunk_idx, crc = struct.unpack('<BBBB I', entry[:8])
            raw_key = entry[8:24].split(b'\x00')[0].decode('latin1', errors='replace')
            payload = entry[:4] + entry[8:32]
            self.assertEqual(crc, zlib.crc32(payload, 0xFFFFFFFF), f"CRC mismatch for {raw_key}")

            if val_type == 0x14:
                val = struct.unpack('<i', entry[24:28])[0]
                keys[raw_key] = val
            entry_idx += span

        self.assertEqual(keys.get('spk_bclk'), 15, "Speaker BCLK must be GPIO 15 on S3 Tim")
        self.assertEqual(keys.get('p_lamp'), -1, "p_lamp must be -1 to prevent conflict with spk_bclk")

    def test_esp32_master_firmware_structure(self):
        ino_path = os.path.join(self.repo_dir, "firmware", "esp32_master", "esp32_master.ino")
        self.assertTrue(os.path.exists(ino_path), "esp32_master.ino must exist")
        with open(ino_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("ESP32-S3 MASTER", content)
        self.assertIn("struct __attribute__((packed)) DeskCommandPacket", content)
        self.assertIn("struct __attribute__((packed)) DeskStatusPacket", content)
        self.assertIn("esp_now_init()", content)
        self.assertIn("sendEspNowCommand", content)
        self.assertIn("TRỢ LÝ BÀN LÀM VIỆC THÔNG MINH", content)

    def test_esp8266_slave_firmware_structure(self):
        ino_path = os.path.join(self.repo_dir, "firmware", "esp8266_slave", "esp8266_slave.ino")
        self.assertTrue(os.path.exists(ino_path), "esp8266_slave.ino must exist")
        with open(ino_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("#define RADAR_PIN   D2", content)
        self.assertIn("#define RELAY_PIN   D1", content)
        self.assertIn("setRelay", content)
        self.assertIn("onDataRecv", content)
        self.assertIn("saveSettings", content)
        self.assertIn("debouncedOccupied", content)
        self.assertIn("autoOffTimeoutSec", content)
        self.assertIn("TRỢ LÝ BÀN LÀM VIỆC THÔNG MINH", content)
        self.assertIn("VBUS", content)

if __name__ == '__main__':
    unittest.main()
