import serial
import time
import sys

def monitor_esp8266_espnow(port='COM10', baudrate=115200, duration=15):
    print("==================================================")
    print(f" MONITORING ESP8266 TELEMETRY & ESP-NOW ({duration}s)")
    print("==================================================")
    try:
        ser = serial.Serial(port, baudrate, timeout=0.5)
        ser.dtr = False
        ser.rts = False
        time.sleep(0.5)
        
        start_time = time.time()
        rx_count = 0
        radar_events = 0
        espnow_cmds = 0
        
        while time.time() - start_time < duration:
            raw_line = ser.readline()
            line = raw_line.decode('ascii', errors='ignore').strip()
            if line:
                print(f"[COM10] {line}")
                rx_count += 1
                if "[RADAR]" in line:
                    radar_events += 1
                if "[ESP-NOW]" in line:
                    espnow_cmds += 1
                    
        ser.close()
        print("\n--------------------------------------------------")
        print(f"Summary: Read {rx_count} lines. Radar events: {radar_events}, ESP-NOW logs: {espnow_cmds}")
        print("--------------------------------------------------")
        return True
    except Exception as e:
        print(f"Error opening port {port}: {e}")
        return False

if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM10'
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    monitor_esp8266_espnow(port, 115200, duration)
