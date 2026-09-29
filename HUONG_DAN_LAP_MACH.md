# HƯỚNG DẪN LẮP RÁP & ĐẤU NỐI MẠCH CHI TIẾT
## DỰ ÁN: TRỢ LÝ BÀN LÀM VIỆC THÔNG MINH (SMART DESK ASSISTANT)

Tài liệu này hướng dẫn chi tiết cách đấu nối dây giữa các linh kiện, phân chia nguồn điện, sơ đồ chân và các lưu ý an toàn quan trọng khi thực hiện phần cứng trên bàn làm việc và chuẩn bị cho buổi báo cáo bài tập lớn.

---

## 1. TỔNG QUAN PHẦN CỨNG & BỐ TRÍ (PLACEMENT)

Hệ thống gồm 2 cụm mạch hoạt động độc lập, không dây nối giữa 2 cụm:

```text
┌────────────────────────────────────────────────────────┐
│                   MẶT BÀN LÀM VIỆC                     │
│  [ Cụm 1: Bo chính ESP32-S3 Tím ]                     │
│  - Tích hợp sẵn Mic + Loa I2S (Trợ lý AI giọng nói)    │
│  - Màn hình LCD hiển thị thời gian & trạng thái        │
│  - Cắm 1 cáp USB Type-C cấp nguồn (cắm củ sạc/laptop)   │
└────────────────────────────────────────────────────────┘
                           ▲
                           │  Sóng vô tuyến ESP-NOW (Không dây)
                           ▼
┌────────────────────────────────────────────────────────┐
│                   GẦM BÀN / HỘP ĐÈN                    │
│  [ Cụm 2: Bo phụ ESP8266 + Ngoại vi ]                  │
│  - NodeMCU ESP8266                                     │
│  - Cảm biến Radar mmWave HLK-LD2410                    │
│  - Module Relay 1 kênh (Kích đóng/ngắt đèn)            │
│  - Cắm 1 cáp Micro-USB cấp nguồn (5V/1A - 2A)          │
└────────────────────────────────────────────────────────┘
```

---

## 2. ĐẤU NỐI CỤM PHỤ: ESP8266 + LD2410 + RELAY

Đây là cụm mạch cần nối dây nhiều nhất. Hãy làm theo sơ đồ bên dưới.

### 2.1. Bảng nối chân chi tiết (Pinout Table)

| Linh kiện | Chân linh kiện | Chân trên NodeMCU ESP8266 | Màu dây khuyến nghị | Chức năng |
| :--- | :--- | :--- | :--- | :--- |
| **Cảm biến LD2410** | **VCC** | **VIN (hoặc VU)** | Đỏ | Cấp nguồn **5V** (BẮT BUỘC dùng 5V, không cắm 3V3) |
| | **GND** | **GND** | Đen | Nối mass chung |
| | **OUT** | **D2 (GPIO4)** | Vàng / Xanh lá | Tín hiệu phát hiện người (HIGH = có người, LOW = vắng) |
| **Module Relay 2 kênh** | **DC+** (tương đương VCC) | **VIN (hoặc VU)** | Đỏ | Cấp nguồn **5V** cho cuộn hút relay |
| | **DC-** (tương đương GND) | **GND** | Đen | Nối mass chung |
| | **IN1** | **D1 (GPIO5)** | Xanh dương | Tín hiệu điều khiển đóng ngắt Kênh 1 từ ESP8266 |
| | **IN2** | *(Bỏ trống)* | - | Kênh 2 dự phòng, không dùng |

> [!NOTE]
> **GIẢI THÍCH KÝ HIỆU CHÂN MODULE RELAY 2 KÊNH:**
> - Các module Relay 2 kênh thường in ký hiệu **`DC+`** và **`DC-`** thay vì `VCC` và `GND`:
>   + **`DC+`**: Cực dương nguồn nuôi (nối 5V từ chân `VIN`/`VU` của NodeMCU).
>   + **`DC-`**: Cực âm nguồn nuôi (nối mass `GND` của NodeMCU).
>   + **`IN1` / `IN2`**: Tín hiệu kích cho Kênh 1 và Kênh 2. Ở dự án này chúng ta nối **`IN1`** vào **`D1` (GPIO5)**.
> - **Jumper kích (H / L Trigger)**:
>   + Trên mạch có 2 jumper cắm ghi chữ **`H` (High)** và **`L` (Low)** cho từng kênh.
>   + Bạn hãy **cắm jumper ở vị trí `L` (Low Level Trigger)** vì code mẫu ESP8266 đã cấu hình xuất mức `LOW` để bật đèn (`#define RELAY_ON LOW`).

> [!WARNING]
> **ĐẶC BIỆT LƯU Ý VỀ NGUỒN CỦA LD2410:**
> - Cảm biến radar LD2410 khi phát sóng quét 24GHz tiêu thụ dòng tức thời lên tới **150mA - 200mA**.
> - **KHÔNG NỐI VCC CỦA LD2410 VÀO CHÂN 3V3 CỦA ESP8266**, vì chip hạ áp 3.3V trên NodeMCU sẽ bị quá tải, gây sụt áp làm ESP8266 bị khởi động lại (Reset liên tục).
> - Luôn nối chân `VCC` của LD2410 vào chân **`VIN`** (hoặc `VU`) để lấy nguồn trực tiếp từ cổng sạc USB 5V.

---

### 2.2. Sơ đồ nối tải điện vào Relay (Điều khiển đèn)

Module Relay có 3 cọc đấu dây đầu ra:
- **`COM` (Common)**: Chân chung.
- **`NO` (Normally Open)**: Thường mở (Mặc định ngắt mạch, khi kích relay thì đóng mạch ➔ Đèn sáng).
- **`NC` (Normally Closed)**: Thường đóng (Mặc định đóng mạch, khi kích thì ngắt).

```text
                     ┌──────────────────┐
     Nguồn Đèn ──────┤ COM              │
   (Dây nóng/Dương)  │      RELAY       │
                     │  NO ─────────────┼───────> [ Cực Dương Bóng Đèn ]
                     │  NC (Bỏ trống)   │
                     └──────────────────┘

     Nguồn Đèn ─────────────────────────────────> [ Cực Âm Bóng Đèn ]
   (Dây nguội/Âm)
```

> [!TIP]
> **LỜI KHUYÊN CHO BUỔI DEMO TRÊN LỚP (AN TOÀN TUYỆT ĐỐI):**
> - Khi chấm bài tập lớn trước mặt thầy cô, bạn **nên dùng đèn bàn LED 5V (cổng USB) hoặc 12V DC** thay vì dùng điện lưới 220V xoay chiều.
> - Dùng nguồn 5V/12V vừa an toàn chống điện giật, vừa không sợ cháy nổ khi mang vác di chuyển demo, trong khi nguyên lý điều khiển qua Relay hoàn toàn giống hệt 220V.

---

## 3. CỤM CHÍNH: ESP32-S3 TÍM (MASTER)

Bo ESP32-S3 tím của bạn đã tích hợp sẵn:
- **Microphone MEMS I2S** (chuyên dụng thu âm giọng nói).
- **IC khuếch đại âm thanh + Loa onboard** (đã đấu nối sẵn trên bo, chỉ cần cắm loa vào jack PH2.0).

### 3.1. Đấu nối Màn hình LCD hiển thị (Nếu gắn thêm)

Nếu bạn gắn thêm màn hình hiển thị thời gian ngồi làm việc (ST7789 hoặc GC9A01 tròn qua giao tiếp SPI):

| Chân Màn hình | Chân kết nối ESP32-S3 (Gợi ý) | Chức năng |
| :--- | :--- | :--- |
| **VCC** | **3V3 (hoặc 5V)** | Nguồn nuôi màn hình |
| **GND** | **GND** | Mass chung |
| **SCL / SCK** | **GPIO 12** | Chân xung nhịp SPI Clock |
| **SDA / MOSI**| **GPIO 11** | Chân truyền dữ liệu SPI Data |
| **RES / RST** | **GPIO 9** | Chân Reset màn hình |
| **DC** | **GPIO 8** | Chân chọn Data / Command |
| **CS** | **GPIO 10** | Chân Chip Select |
| **BLK / BL** | **GPIO 7 (hoặc 3V3)** | Chân điều khiển đèn nền màn hình (Backlight) |

*(Lưu ý: Firmware Xiaozhi cho phép bạn cấu hình lại các chân GPIO này trực tiếp qua giao diện Web Config `192.168.4.1` mà không cần sửa code).*

---

## 4. HƯỚNG DẪN CĂN CHỈNH VỊ TRÍ CẢM BIẾN RADAR (LD2410)

Cảm biến sóng milimet LD2410 có khả năng "xuyên thấu" vật liệu phi kim (gỗ, nhựa, vải mica), do đó:

```text
               [ MẶT BÀN GỖ ]
       ──────────────────────────────
               [ LD2410 ]  ▲
                   │       │ Góc quét 60°
                   ▼       │ Hướng vào vị trí ghế ngồi
              [ GHẾ NGỒI ]
```

1. **Vị trí lắp đặt**:
   - Dán hoặc cố định module LD2410 ở mép bàn phía trước, mặt có ăng-ten hướng thẳng vào ngực/bụng người ngồi ghế.
   - Khoảng cách lý tưởng từ cảm biến đến người ngồi: **0.5m – 1.2m**.
2. **Những điều cần tránh**:
   - **Không để vật kim loại che mặt cảm biến**: Kim loại chắn hoàn toàn sóng radar 24GHz.
   - **Tránh quạt bàn / quạt trần**: Cánh quạt quay tạo chuyển động liên tục khiến radar tưởng nhầm có người và không bao giờ tắt đèn.
   - **Tránh rèm cửa lay động**: Tránh hướng radar về phía cửa sổ có rèm đung đưa theo gió.

---

## 5. CHECKLIST KIỂM TRA MẠCH TRƯỚC KHI CẮM NGUỒN (PRE-FLIGHT CHECK)

Thực hiện tuần tự 5 bước kiểm tra sau bằng mắt và đồng hồ VOM (nếu có):

- [ ] **Bước 1 (Kiểm tra chạm chập)**: Đảm bảo chân `VCC/VIN` và `GND` không bị dính thiếc hoặc chạm vào nhau.
- [ ] **Bước 2 (Chân nguồn 5V)**: Xác nhận chân `VCC` của LD2410 và Relay cắm đúng chân `VIN` (5V), không cắm nhầm chân `3V3`.
- [ ] **Bước 3 (Kiểm tra Relay)**: Cấp nguồn cho ESP8266 qua cáp USB, nghe xem relay có phát ra tiếng "tách" dứt khoát khi kích hoạt hay không.
- [ ] **Bước 4 (Kiểm tra Radar)**: Khi có người ngồi trước cảm biến, đo chân `OUT` của LD2410 bằng đồng hồ vạn năng xem có lên mức logic ~3.3V (`HIGH`) hay không. Khi đứng dậy đi ra xa > 2m xem chân `OUT` có về 0V (`LOW`) hay không.
- [ ] **Bước 5 (Cố định dây)**: Dùng dây rút hoặc băng keo cách điện bó gọn các đường dây tín hiệu, tránh lỏng dây lúc di chuyển mang lên lớp thuyết trình.
