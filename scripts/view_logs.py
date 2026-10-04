import serial
import serial.tools.list_ports
import sys
import time
import threading

def find_esp8266_port():
    ports = list(serial.tools.list_ports.comports())
    # Priority: CH340 or CP210x on COM8, or ports with USB
    for p in ports:
        if p.device == 'COM8':
            return p.device
    for p in ports:
        if 'CH340' in p.description or 'USB' in p.description:
            return p.device
    return 'COM8'

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_esp8266_port()
    baud = 115200

    print("=" * 65)
    print("      TRÌNH THEO DÕI LOG & ĐIỀU KHIỂN ESP8266 SLAVE")
    print("=" * 65)
    print(f"[*] Đang kết nối tới cổng: {port} (Baudrate: {baud})...")

    try:
        ser = serial.Serial()
        ser.port = port
        ser.baudrate = baud
        ser.timeout = 0.5
        ser.dtr = False
        ser.rts = False
        ser.open()
    except Exception as e:
        print(f"[!] Không thể mở cổng {port}: {e}")
        print("    Vui lòng kiểm tra cáp cắm USB hoặc đóng Arduino Serial Monitor nếu đang mở.")
        sys.exit(1)

    print(f"[+] Kết nối thành công!")
    print("\n--- PHÍM TẮT ĐIỀU KHIỂN & HIỆU CHỈNH TRỰC TIẾP ---")
    print(" [0] : Ép TẮT đèn (Đèn tắt, cảm biến không tự bật lại)")
    print(" [1] : Ép BẬT đèn (Đèn bật liên tục)")
    print(" [a] : Chuyển về chế độ TỰ ĐỘNG (AUTO - theo cảm biến)")
    print(" [p] : Đảo cực Relay (Active-LOW <-> Active-HIGH) & Lưu EEPROM")
    print(" [r] : Đảo cực Radar (Active-HIGH <-> Active-LOW) & Lưu EEPROM")
    print(" [s] : Xem trạng thái chi tiết (Diagnostics)")
    print(" [h] : Hiển thị bảng trợ giúp")
    print(" [q] : Thoát chương trình")
    print("=" * 65)
    print("[*] Đang đọc log thời gian thực từ ESP8266...\n")

    stop_event = threading.Event()

    def reader_thread():
        while not stop_event.is_set():
            try:
                line = ser.readline()
                if line:
                    sys.stdout.buffer.write(line)
                    sys.stdout.flush()
            except Exception:
                break

    t = threading.Thread(target=reader_thread, daemon=True)
    t.start()

    # Request initial status
    time.sleep(0.5)
    ser.write(b's\n')
    ser.flush()

    try:
        while not stop_event.is_set():
            user_input = input()
            cmd = user_input.strip().lower()
            if cmd == 'q':
                break
            elif cmd in ['0', '1', 'a', 'p', 'r', 's', 'h']:
                ser.write((cmd + '\n').encode('ascii'))
                ser.flush()
            elif len(cmd) > 0:
                print(f"[?] Lệnh '{cmd}' không hợp lệ. Gõ 'h' để xem trợ giúp hoặc 'q' để thoát.")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        stop_event.set()
        ser.close()
        print("\n[*] Đã ngắt kết nối cổng Serial. Tạm biệt!")

if __name__ == '__main__':
    main()
