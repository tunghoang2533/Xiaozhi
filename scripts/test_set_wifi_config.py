import os
import sys
import unittest
import zlib
import struct

sys.path.insert(0, os.path.dirname(__file__))
from set_wifi_config import update_nvs_wifi
from test_nvs_configuration import TestNVSConfiguration

class TestSetWifiConfig(unittest.TestCase):
    def test_update_nvs_wifi(self):
        bin_path = os.path.join(os.path.dirname(__file__), "..", "nvs_configured.bin")
        # Save backup
        with open(bin_path, 'rb') as f:
            backup = f.read()

        try:
            test_ssid = "TestWiFi_123"
            test_pwd = "PassWord_456"
            update_nvs_wifi(bin_path, test_ssid, test_pwd)

            # Read and verify
            with open(bin_path, 'rb') as f:
                data = f.read()

            page0 = data[0:4096]
            page1 = data[4096:8192]

            # Verify SSID
            ssid_entry = page0[0x0FA0 : 0x0FA0 + 32]
            ssid_crc = struct.unpack('<I', ssid_entry[4:8])[0]
            self.assertEqual(ssid_crc, zlib.crc32(ssid_entry[:4] + ssid_entry[8:32], 0xFFFFFFFF))
            ssid_len = struct.unpack('<H', ssid_entry[24:26])[0]
            ssid_str_crc = struct.unpack('<I', ssid_entry[28:32])[0]
            ssid_str_bytes = page0[0x0FC0 : 0x0FC0 + ssid_len]
            self.assertEqual(ssid_str_bytes, (test_ssid + "\x00").encode('utf-8'))
            self.assertEqual(ssid_str_crc, zlib.crc32(ssid_str_bytes, 0xFFFFFFFF))

            # Verify PWD
            pwd_entry = page1[0x0040 : 0x0040 + 32]
            pwd_crc = struct.unpack('<I', pwd_entry[4:8])[0]
            self.assertEqual(pwd_crc, zlib.crc32(pwd_entry[:4] + pwd_entry[8:32], 0xFFFFFFFF))
            pwd_len = struct.unpack('<H', pwd_entry[24:26])[0]
            pwd_str_crc = struct.unpack('<I', pwd_entry[28:32])[0]
            pwd_str_bytes = page1[0x0060 : 0x0060 + pwd_len]
            self.assertEqual(pwd_str_bytes, (test_pwd + "\x00").encode('utf-8'))
            self.assertEqual(pwd_str_crc, zlib.crc32(pwd_str_bytes, 0xFFFFFFFF))

        finally:
            # Restore backup (Tp_LinkC6F2)
            with open(bin_path, 'wb') as f:
                f.write(backup)

if __name__ == '__main__':
    unittest.main()
