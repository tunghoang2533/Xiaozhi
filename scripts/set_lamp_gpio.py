import os
import sys
import struct
import zlib
import subprocess

def set_nvs_p_lamp(bin_path, p_lamp_gpio=15):
    with open(bin_path, 'rb') as f:
        data = bytearray(f.read())

    if len(data) != 16384:
        raise ValueError("NVS partition size must be 16384 bytes")

    page0 = data[0:4096]
    bitmap0 = page0[32:64]

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

        if raw_key == 'p_lamp' and val_type == 0x14: # int32
            key_bytes = entry[8:24]
            desc_without_crc = entry[:4] + key_bytes + struct.pack('<i', p_lamp_gpio) + entry[28:32]
            new_crc = zlib.crc32(desc_without_crc, 0xFFFFFFFF)
            final_entry = entry[:4] + struct.pack('<I', new_crc) + key_bytes + struct.pack('<i', p_lamp_gpio) + entry[28:32]
            page0[offset : offset + 32] = final_entry
            updated_count += 1

        entry_idx += span

    data[0:4096] = page0

    with open(bin_path, 'wb') as f:
        f.write(data)
    print(f"Updated p_lamp = {p_lamp_gpio} in {bin_path} ({updated_count} entry updated)")

def flash_nvs(bin_path, port='COM5'):
    cmd = [sys.executable, '-m', 'esptool', '--port', port, '--baud', '115200', 'write_flash', '0x9000', bin_path]
    print(f"Flashing updated NVS to {port}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr)
        raise RuntimeError(f"esptool flash failed with return code {res.returncode}")

if __name__ == "__main__":
    target_bin = os.path.join(os.path.dirname(__file__), "..", "nvs_configured.bin")
    gpio_val = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    port_val = sys.argv[2] if len(sys.argv) > 2 else "COM5"

    set_nvs_p_lamp(target_bin, gpio_val)
    flash_nvs(target_bin, port_val)
