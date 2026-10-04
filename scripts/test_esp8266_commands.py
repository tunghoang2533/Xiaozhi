import serial
import time
import sys

def test_esp8266_commands(port='COM8', baudrate=115200):
    print(f"Connecting to ESP8266 on {port}...")
    ser = serial.Serial(port, baudrate, timeout=0.5)
    ser.dtr = False
    ser.rts = False
    
    # Wait for boot and WiFi sync sequence to complete
    print("Waiting for ESP8266 boot and WiFi channel synchronization...")
    boot_done = False
    t0 = time.time()
    while time.time() - t0 < 8:
        l = ser.readline().decode('ascii', errors='ignore').strip()
        if l:
            print(f"[BOOT] {l}")
            if "[ESP-NOW] Init Success" in l or "[STATUS]" in l:
                boot_done = True
                break

    time.sleep(0.5)
    ser.reset_input_buffer()

    try:
        # Step 1: Send '0' (Turn OFF)
        print("\n--> [TEST 1] Sending Command '0' (Turn OFF)...")
        ser.write(b'0\n')
        ser.flush()
        time.sleep(1)
        lines = []
        t0 = time.time()
        while time.time() - t0 < 2:
            l = ser.readline().decode('ascii', errors='ignore').strip()
            if l:
                print(f"[RECV] {l}")
                lines.append(l)

        off_success = any("OFF" in l for l in lines)
        assert off_success, "Failed: Lamp should report OFF state"
        print("[PASSED] Command '0' successfully turned OFF lamp!")

        # Step 2: Send '1' (Turn ON)
        print("\n--> [TEST 2] Sending Command '1' (Turn ON)...")
        ser.write(b'1\n')
        ser.flush()
        time.sleep(1)
        lines = []
        t0 = time.time()
        while time.time() - t0 < 2:
            l = ser.readline().decode('ascii', errors='ignore').strip()
            if l:
                print(f"[RECV] {l}")
                lines.append(l)

        on_success = any("ON" in l for l in lines)
        assert on_success, "Failed: Lamp should report ON state"
        print("[PASSED] Command '1' successfully turned ON lamp!")

        # Step 3: Send 's' (Status & Diagnostics)
        print("\n--> [TEST 3] Sending Command 's' (Diagnostics)...")
        ser.write(b's\n')
        ser.flush()
        time.sleep(1)
        lines = []
        t0 = time.time()
        while time.time() - t0 < 2:
            l = ser.readline().decode('ascii', errors='ignore').strip()
            if l:
                print(f"[RECV] {l}")
                lines.append(l)

        diag_success = any("[DIAG]" in l or "[STATUS]" in l for l in lines)
        assert diag_success, "Failed: Status diagnostics not received"
        print("[PASSED] Telemetry & channel info verified!")

        # Step 4: Send 'a' (Reset Auto Mode)
        print("\n--> [TEST 4] Sending Command 'a' (Reset AUTO)...")
        ser.write(b'a\n')
        ser.flush()
        time.sleep(1)
        lines = []
        t0 = time.time()
        while time.time() - t0 < 2:
            l = ser.readline().decode('ascii', errors='ignore').strip()
            if l:
                print(f"[RECV] {l}")
                lines.append(l)

        auto_success = any("AUTO" in l for l in lines)
        assert auto_success, "Failed: AUTO mode reset not confirmed"
        print("[PASSED] AUTO mode successfully restored!")

        print("\n==========================================")
        print(" ALL ESP8266 SLAVE HARDWARE TESTS PASSED!")
        print("==========================================")
        return True

    finally:
        ser.close()

if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM8'
    success = test_esp8266_commands(port)
    sys.exit(0 if success else 1)
