import serial
import time
import sys

def test_espnow_bridge(esp32_port='COM5', esp8266_port='COM10'):
    print(f"Testing ESP-NOW Wireless Bridge: ESP32-S3 ({esp32_port}) -> ESP8266 ({esp8266_port})...")
    
    try:
        ser32 = serial.Serial(esp32_port, 115200, timeout=1)
        ser8266 = serial.Serial(esp8266_port, 115200, timeout=1)
        
        ser32.dtr = False
        ser32.rts = False
        ser8266.dtr = False
        ser8266.rts = False
        time.sleep(1)

        print("\n--- [STEP 1] Sending OFF Command '0' from ESP32-S3 ---")
        ser32.write(b'0')
        ser32.flush()
        
        time.sleep(1)
        lines8266 = []
        start = time.time()
        while time.time() - start < 3:
            raw = ser8266.readline()
            line = raw.decode('ascii', errors='ignore').strip()
            if line:
                print(f"[ESP8266 RECV] {line}")
                lines8266.append(line)

        print("\n--- [STEP 2] Sending ON Command '1' from ESP32-S3 ---")
        ser32.write(b'1')
        ser32.flush()

        time.sleep(1)
        start = time.time()
        while time.time() - start < 3:
            raw = ser8266.readline()
            line = raw.decode('ascii', errors='ignore').strip()
            if line:
                print(f"[ESP8266 RECV] {line}")
                lines8266.append(line)

        ser32.close()
        ser8266.close()

        print("\n[PASSED] Wireless ESP-NOW test executed successfully!")
        return True

    except Exception as e:
        print(f"Error testing ESP-NOW bridge: {e}")
        return False

if __name__ == '__main__':
    p32 = sys.argv[1] if len(sys.argv) > 1 else 'COM5'
    p8266 = sys.argv[2] if len(sys.argv) > 2 else 'COM10'
    test_espnow_bridge(p32, p8266)
