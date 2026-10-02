import os
import struct
import zlib
import unittest

class TestNVSConfiguration(unittest.TestCase):
    def setUp(self):
        self.bin_path = os.path.join(os.path.dirname(__file__), "..", "nvs_configured.bin")
        self.assertTrue(os.path.exists(self.bin_path), "nvs_configured.bin must exist")
        with open(self.bin_path, "rb") as f:
            self.data = bytearray(f.read())
        self.assertEqual(len(self.data), 16384, "NVS partition must be 16KB")

    def test_nvs_crc_and_entries(self):
        page0 = self.data[0:4096]
        page1 = self.data[4096:8192]
        bitmap0 = page0[32:64]

        expected_lcd = {
            'scr_type': 0,
            'drv': 3,
            'w': 80,
            'h': 160,
            'off_x': 25,
            'off_y': 0,
            'mir_x': 1,
            'mir_y': 1,
            'swap_xy': 0,
            'inv_col': 0,
            'rgb_ord': 1,
            'spi_mode': 0,
            'p_mosi': 41,
            'p_clk': 42,
            'p_dc': 43,
            'p_rst': 44,
            'p_cs': -1,
            'p_bl': -1,
            'oled_sda': -1,
            'oled_scl': -1,
            'p_boot': 0,
        }

        found_keys = {}
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
                found_keys[raw_key] = val
            entry_idx += span

        for k, v in expected_lcd.items():
            self.assertIn(k, found_keys, f"Missing key {k}")
            self.assertEqual(found_keys[k], v, f"Value mismatch for {k}")

        # Check SSID on Page 0
        ssid_entry = page0[0x0FA0 : 0x0FA0 + 32]
        ssid_crc = struct.unpack('<I', ssid_entry[4:8])[0]
        self.assertEqual(ssid_crc, zlib.crc32(ssid_entry[:4] + ssid_entry[8:32], 0xFFFFFFFF))
        ssid_len = struct.unpack('<H', ssid_entry[24:26])[0]
        ssid_str_crc = struct.unpack('<I', ssid_entry[28:32])[0]
        ssid_str_bytes = page0[0x0FC0 : 0x0FC0 + ssid_len]
        self.assertEqual(ssid_str_bytes, b"Tung Quan\x00")
        self.assertEqual(ssid_str_crc, zlib.crc32(ssid_str_bytes, 0xFFFFFFFF))

        # Check Password on Page 1
        pwd_entry = page1[0x0040 : 0x0040 + 32]
        pwd_crc = struct.unpack('<I', pwd_entry[4:8])[0]
        self.assertEqual(pwd_crc, zlib.crc32(pwd_entry[:4] + pwd_entry[8:32], 0xFFFFFFFF))
        pwd_len = struct.unpack('<H', pwd_entry[24:26])[0]
        pwd_str_crc = struct.unpack('<I', pwd_entry[28:32])[0]
        pwd_str_bytes = page1[0x0060 : 0x0060 + pwd_len]
        self.assertEqual(pwd_str_bytes, b"23101272005\x00")
        self.assertEqual(pwd_str_crc, zlib.crc32(pwd_str_bytes, 0xFFFFFFFF))

if __name__ == '__main__':
    unittest.main()
