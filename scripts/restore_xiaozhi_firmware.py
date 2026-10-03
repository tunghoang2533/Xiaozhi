import os
import sys
import subprocess

def restore_firmware(port='COM5'):
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    firmware_bin = os.path.join(repo_dir, "s3timtft096b.bin")
    nvs_bin = os.path.join(repo_dir, "nvs_configured.bin")

    if not os.path.exists(firmware_bin):
        raise FileNotFoundError(f"Firmware binary not found: {firmware_bin}")
    if not os.path.exists(nvs_bin):
        raise FileNotFoundError(f"NVS binary not found: {nvs_bin}")

    print(f"Flashing full Xiaozhi firmware to {port}...")
    cmd1 = [sys.executable, "-m", "esptool", "--port", port, "--baud", "921600", "write_flash", "0x0", firmware_bin]
    res1 = subprocess.run(cmd1)
    if res1.returncode != 0:
        raise RuntimeError(f"esptool failed flashing firmware with code {res1.returncode}")

    print(f"Flashing NVS configuration to {port}...")
    cmd2 = [sys.executable, "-m", "esptool", "--port", port, "--baud", "115200", "write_flash", "0x9000", nvs_bin]
    res2 = subprocess.run(cmd2)
    if res2.returncode != 0:
        raise RuntimeError(f"esptool failed flashing NVS with code {res2.returncode}")

    print(f"Successfully restored Xiaozhi AI assistant firmware on {port}!")

if __name__ == "__main__":
    port_arg = sys.argv[1] if len(sys.argv) > 1 else "COM5"
    restore_firmware(port_arg)
