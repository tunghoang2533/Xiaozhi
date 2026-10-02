import os
import sys
import unittest
import zlib
import struct

sys.path.insert(0, os.path.dirname(__file__))
from set_lcd_config import update_nvs_lcd

class TestSetLcdConfig(unittest.TestCase):
    def test_update_nvs_lcd(self):
        bin_path = os.path.join(os.path.dirname(__file__), "..", "nvs_configured.bin")
        with open(bin_path, 'rb') as f:
            backup = f.read()

        try:
            update_nvs_lcd(bin_path, drv=3, off_x=25, off_y=1, inv_col=0, spi_mode=0)

            with open(bin_path, 'rb') as f:
                data = f.read()

            page0 = data[0:4096]
            bitmap0 = page0[32:64]

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
                raw_key = entry[8:24].split(b'\x00')[0].decode('latin1', errors='replace')
                val_type = entry[1]
                if val_type == 0x14:
                    val = struct.unpack('<i', entry[24:28])[0]
                    found_keys[raw_key] = val
                entry_idx += entry[2]

            self.assertEqual(found_keys.get('drv'), 3)
            self.assertEqual(found_keys.get('off_x'), 25)
            self.assertEqual(found_keys.get('off_y'), 1)
            self.assertEqual(found_keys.get('inv_col'), 0)
            self.assertEqual(found_keys.get('spi_mode'), 0)

        finally:
            with open(bin_path, 'wb') as f:
                f.write(backup)

if __name__ == '__main__':
    unittest.main()
