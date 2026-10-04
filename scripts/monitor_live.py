import serial
import time
import sys
import threading

def read_port(name, port, duration=20):
    try:
        s = serial.Serial()
        s.port = port
        s.baudrate = 115200
        s.timeout = 0.1
        s.dtr = False
        s.rts = False
        s.open()
        t0 = time.time()
        while time.time() - t0 < duration:
            raw = s.readline()
            if raw:
                line = raw.decode('utf-8', errors='replace').strip()
                if line and "[STATUS]" not in line:
                    ts = time.strftime("%H:%M:%S")
                    msg = f"[{ts}] [{name}] {line}\n"
                    sys.stdout.buffer.write(msg.encode('utf-8', errors='replace'))
                    sys.stdout.flush()
        s.close()
    except Exception as e:
        print(f"[{name} ERROR]: {e}")

if __name__ == '__main__':
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    print(f"=== Monitoring ESP32 (COM5) & ESP8266 (COM8) for {duration}s ===")
    t1 = threading.Thread(target=read_port, args=('ESP32', 'COM5', duration))
    t2 = threading.Thread(target=read_port, args=('ESP8266', 'COM8', duration))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print("=== Monitoring finished ===")
