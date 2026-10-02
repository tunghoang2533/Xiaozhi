import os
import sys
import struct
import zlib
import subprocess

def update_nvs_wifi(bin_path, ssid, password):
    with open(bin_path, 'rb') as f:
        data = bytearray(f.read())

    if len(data) != 16384:
        raise ValueError("NVS partition size must be 16384 bytes")

    # Update SSID at Page 0
    # Entry descriptor at 0x0FA0
    # String payload at 0x0FC0 (32 bytes slot)
    ssid_bytes = ssid.encode('utf-8') + b'\x00'
    if len(ssid_bytes) > 32:
        raise ValueError("SSID too long (max 31 characters)")
    
    ssid_len = len(ssid_bytes)
    ssid_str_crc = zlib.crc32(ssid_bytes, 0xFFFFFFFF)

    # Pad payload slot to 32 bytes
    ssid_payload = ssid_bytes.ljust(32, b'\xff')
    data[0x0FC0 : 0x0FC0 + 32] = ssid_payload

    # Update Entry descriptor
    # Struct fields: ns_idx(B), val_type(B), span(B), chunk_idx(B), crc(I), key(16s), len(H), res(H), data_crc(I)
    entry_before = data[0x0FA0 : 0x0FA0 + 32]
    # Keep ns_idx, val_type, span, chunk_idx, key
    ns_idx, val_type, span, chunk_idx = entry_before[0], entry_before[1], entry_before[2], entry_before[3]
    key_bytes = entry_before[8:24]
    
    desc_without_crc = bytearray(struct.pack('<BBBB', ns_idx, val_type, span, chunk_idx))
    desc_without_crc += key_bytes
    desc_without_crc += struct.pack('<HH', ssid_len, 0xFFFF)
    desc_without_crc += struct.pack('<I', ssid_str_crc)

    entry_crc = zlib.crc32(desc_without_crc, 0xFFFFFFFF)
    final_ssid_entry = desc_without_crc[:4] + struct.pack('<I', entry_crc) + desc_without_crc[4:]
    data[0x0FA0 : 0x0FA0 + 32] = final_ssid_entry

    # Update Password at Page 1 (offset 4096)
    # Entry descriptor at 4096 + 0x0040 = 0x1040
    # String payload at 4096 + 0x0060 = 0x1060 (32 bytes slot)
    pwd_bytes = password.encode('utf-8') + b'\x00'
    if len(pwd_bytes) > 32:
        raise ValueError("Password too long (max 31 characters)")

    pwd_len = len(pwd_bytes)
    pwd_str_crc = zlib.crc32(pwd_bytes, 0xFFFFFFFF)

    pwd_payload = pwd_bytes.ljust(32, b'\xff')
    data[0x1060 : 0x1060 + 32] = pwd_payload

    entry_before = data[0x1040 : 0x1040 + 32]
    ns_idx, val_type, span, chunk_idx = entry_before[0], entry_before[1], entry_before[2], entry_before[3]
    key_bytes = entry_before[8:24]

    desc_without_crc = bytearray(struct.pack('<BBBB', ns_idx, val_type, span, chunk_idx))
    desc_without_crc += key_bytes
    desc_without_crc += struct.pack('<HH', pwd_len, 0xFFFF)
    desc_without_crc += struct.pack('<I', pwd_str_crc)

    entry_crc = zlib.crc32(desc_without_crc, 0xFFFFFFFF)
    final_pwd_entry = desc_without_crc[:4] + struct.pack('<I', entry_crc) + desc_without_crc[4:]
    data[0x1040 : 0x1040 + 32] = final_pwd_entry

    with open(bin_path, 'wb') as f:
        f.write(data)
    print(f"Successfully updated WiFi configuration in {bin_path}: SSID='{ssid}'")

def flash_nvs(bin_path, port='COM5'):
    cmd = [sys.executable, '-m', 'esptool', '--port', port, '--baud', '115200', 'write_flash', '0x9000', bin_path]
    print(f"Flashing NVS via command: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr)
        raise RuntimeError(f"esptool flash failed with return code {res.returncode}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python set_wifi_config.py <SSID> <PASSWORD> [PORT]")
        print("Example: python set_wifi_config.py MyWiFi 12345678 COM5")
        sys.exit(1)
    
    ssid_arg = sys.argv[1]
    pwd_arg = sys.argv[2]
    port_arg = sys.argv[3] if len(sys.argv) > 3 else "COM5"

    target_bin = os.path.join(os.path.dirname(__file__), "..", "nvs_configured.bin")
    update_nvs_wifi(target_bin, ssid_arg, pwd_arg)
    flash_nvs(target_bin, port_arg)
