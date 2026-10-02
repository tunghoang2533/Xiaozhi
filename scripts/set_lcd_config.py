import os
import sys
import struct
import zlib
import subprocess

def update_nvs_lcd(bin_path, drv=3, w=80, h=160, off_x=26, off_y=0, mir_x=1, mir_y=1, swap_xy=0, inv_col=0, rgb_ord=1, spi_mode=0, p_cs=-1):
    with open(bin_path, 'rb') as f:
        data = bytearray(f.read())

    if len(data) != 16384:
        raise ValueError("NVS partition size must be 16384 bytes")

    page0 = data[0:4096]
    bitmap0 = page0[32:64]

    lcd_keys = {
        'drv': drv,
        'w': w,
        'h': h,
        'off_x': off_x,
        'off_y': off_y,
        'mir_x': mir_x,
        'mir_y': mir_y,
        'swap_xy': swap_xy,
        'inv_col': inv_col,
        'rgb_ord': rgb_ord,
        'spi_mode': spi_mode,
        'p_cs': p_cs,
    }

    entry_idx = 0
    updated_count = 0
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

        if raw_key in lcd_keys and val_type == 0x14: # int32
            new_val = lcd_keys[raw_key]
            # Build new entry
            # Payload = entry[:4] + entry[8:24] + struct.pack('<i', new_val) + entry[28:32]
            key_bytes = entry[8:24]
            desc_without_crc = entry[:4] + key_bytes + struct.pack('<i', new_val) + entry[28:32]
            new_crc = zlib.crc32(desc_without_crc, 0xFFFFFFFF)
            final_entry = entry[:4] + struct.pack('<I', new_crc) + key_bytes + struct.pack('<i', new_val) + entry[28:32]
            page0[offset : offset + 32] = final_entry
            updated_count += 1

        entry_idx += span

    data[0:4096] = page0

    with open(bin_path, 'wb') as f:
        f.write(data)
    print(f"Updated {updated_count} LCD keys in {bin_path} (drv={drv}, inv_col={inv_col}, off_x={off_x}, off_y={off_y}, spi_mode={spi_mode})")

def flash_nvs(bin_path, port='COM5'):
    cmd = [sys.executable, '-m', 'esptool', '--port', port, '--baud', '115200', 'write_flash', '0x9000', bin_path]
    print(f"Flashing NVS via command: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr)
        raise RuntimeError(f"esptool flash failed with return code {res.returncode}")

if __name__ == "__main__":
    target_bin = os.path.join(os.path.dirname(__file__), "..", "nvs_configured.bin")
    inv = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    ox = int(sys.argv[2]) if len(sys.argv) > 2 else 26
    oy = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    spi = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    drv_val = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    port_arg = sys.argv[6] if len(sys.argv) > 6 else "COM5"

    update_nvs_lcd(target_bin, drv=drv_val, off_x=ox, off_y=oy, inv_col=inv, spi_mode=spi)
    flash_nvs(target_bin, port_arg)
