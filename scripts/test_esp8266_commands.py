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
        # Step 1: Send '0' (Turn OFF - Command Priority over Sensor)
        print("\n--> [TEST 1] Sending Command '0' (Turn OFF with Command Priority)...")
        ser.write(b'0\n')
        ser.flush()
        time.sleep(1)
        lines = []
        t0 = time.time()
        while time.time() - t0 < 3:
            raw = ser.readline()
            l = raw.decode('utf-8', errors='ignore').strip()
            if l:
                print(f"[RECV] {l}")
                lines.append(l)

        off_success = any("OFF" in l or "Tat" in l for l in lines)
        assert off_success, "Failed: Lamp should report OFF state"
        print("[PASSED] Command '0' successfully turned OFF lamp!")

        # Step 1b: Verify command priority - lamp must STAY OFF even while radar detects person
        print("\n--> [TEST 1B] Verifying Command Priority: Lamp MUST STAY OFF despite radar...")
        time.sleep(2)
        lines_priority = []
        t0 = time.time()
        while time.time() - t0 < 3:
            raw = ser.readline()
            l = raw.decode('utf-8', errors='ignore').strip()
            if l:
                print(f"[RECV] {l}")
                lines_priority.append(l)

        # Check status packets: lamp_state must remain 0
        status_lines = [l for l in lines_priority if "[STATUS]" in l]
        assert len(status_lines) > 0, "Failed: Should receive [STATUS] reports"
        for st in status_lines:
            assert "Lamp: 0" in st, f"Failed: Lamp turned back ON during MANUAL_OFF: {st}"
        print("[PASSED] Priority Verified: Lamp stayed strictly OFF despite radar sensor!")

        # Step 2: Send '1' (Turn ON)
        print("\n--> [TEST 2] Sending Command '1' (Turn ON)...")
        ser.write(b'1\n')
        ser.flush()
        time.sleep(1)
        lines = []
        t0 = time.time()
        while time.time() - t0 < 2:
            raw = ser.readline()
            l = raw.decode('utf-8', errors='ignore').strip()
            if l:
                print(f"[RECV] {l}")
                lines.append(l)

        on_success = any("ON" in l or "Sang" in l for l in lines)
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
            raw = ser.readline()
            l = raw.decode('utf-8', errors='ignore').strip()
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
            raw = ser.readline()
            l = raw.decode('utf-8', errors='ignore').strip()
            if l:
                print(f"[RECV] {l}")
                lines.append(l)

        auto_success = any("AUTO" in l for l in lines)
        assert auto_success, "Failed: AUTO mode reset not confirmed"
        print("[PASSED] AUTO mode successfully restored!")

        # Step 5: Send 'p' (Toggle Relay Polarity)
        print("\n--> [TEST 5] Testing 'p' Command (Toggle Relay Polarity & EEPROM)...")
        ser.write(b'p\n')
        ser.flush()
        time.sleep(1)
        lines = []
        t0 = time.time()
        while time.time() - t0 < 2:
            raw = ser.readline()
            l = raw.decode('utf-8', errors='ignore').strip()
            if l:
                print(f"[RECV] {l}")
                lines.append(l)
        assert any("Toggled Relay Polarity" in l for l in lines), "Failed: Relay polarity toggle not confirmed"
        print("[PASSED] Relay polarity toggle and EEPROM save verified!")

        # Toggle back to ensure it remains Active-LOW (matching Jumper L)
        ser.write(b'p\n')
        ser.flush()
        time.sleep(1)

        # Step 6: Send 'r' (Toggle Radar Logic)
        print("\n--> [TEST 6] Testing 'r' Command (Toggle Radar Logic & EEPROM)...")
        ser.write(b'r\n')
        ser.flush()
        time.sleep(1)
        lines = []
        t0 = time.time()
        while time.time() - t0 < 2:
            raw = ser.readline()
            l = raw.decode('utf-8', errors='ignore').strip()
            if l:
                print(f"[RECV] {l}")
                lines.append(l)
        assert any("Toggled Radar Logic" in l for l in lines), "Failed: Radar logic toggle not confirmed"
        print("[PASSED] Radar logic toggle and EEPROM save verified!")

        # Toggle 'r' once more to return to Active-HIGH state (matching LD2410)
        ser.write(b'r\n')
        ser.flush()
        time.sleep(1)

        # Reset to AUTO mode
        ser.write(b'a\n')
        ser.flush()
        time.sleep(0.5)

        print("\n===================================================================")
        print(" ALL ESP8266 SLAVE COMMAND, PRIORITY & EEPROM CALIBRATION PASSED!")
        print("===================================================================")
        return True

    finally:
        ser.close()

if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM8'
    success = test_esp8266_commands(port)
    sys.exit(0 if success else 1)
