import serial
import time
import sys

def test_esp8266_serial(port='COM10', baudrate=115200, timeout_sec=8):
    print(f"Connecting to {port} at {baudrate} baud...")
    try:
        ser = serial.Serial(port, baudrate, timeout=0.5)
        ser.dtr = False
        ser.rts = False
        time.sleep(0.1)
        
        # Pulse RTS to trigger clean hard reset
        ser.rts = True
        time.sleep(0.1)
        ser.rts = False
        time.sleep(0.5)

        start_time = time.time()
        lines = []
        
        while time.time() - start_time < timeout_sec:
            raw_line = ser.readline()
            line = raw_line.decode('ascii', errors='ignore').strip()
            if line:
                print(f"[SERIAL OUT] {line}")
                lines.append(line)
        
        ser.close()
        
        # Verification
        status_lines = [l for l in lines if "[STATUS]" in l or "[RELAY]" in l or "[ESP-NOW]" in l or "SMART DESK" in l]
        if status_lines:
            print("\n[PASSED] TEST SUCCESS: ESP8266 is running and outputting telemetry!")
            return True
        else:
            print("\n[FAILED] TEST FAILED: No telemetry lines received.")
            return False
            
    except Exception as e:
        print(f"Error connecting to serial port {port}: {e}")
        return False

if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM10'
    success = test_esp8266_serial(port)
    sys.exit(0 if success else 1)
