#include <ESP8266WiFi.h>
#include <espnow.h>
#include <EEPROM.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>

#define RADAR_PIN   D2 // GPIO4 - LD2410 OUT pin
#define RELAY_PIN   D1 // GPIO5 - Relay IN1 pin

#define EEPROM_MAGIC 0x5A

// Hardware Settings
bool relayActiveLow = false;
bool radarActiveHigh = true;
uint16_t autoOffTimeoutSec = 15;

// WiFi credentials in EEPROM
bool hasCustomWifi = false;
char customSsid[33] = {0};
char customPass[65] = {0};

void saveSettings() {
    EEPROM.write(0, EEPROM_MAGIC);
    EEPROM.write(1, relayActiveLow ? 1 : 0);
    EEPROM.write(2, radarActiveHigh ? 1 : 0);
    EEPROM.write(3, autoOffTimeoutSec & 0xFF);
    EEPROM.write(4, (autoOffTimeoutSec >> 8) & 0xFF);
    EEPROM.write(5, hasCustomWifi ? 1 : 0);
    for (int i = 0; i < 32; i++) EEPROM.write(6 + i, customSsid[i]);
    for (int i = 0; i < 64; i++) EEPROM.write(38 + i, customPass[i]);
    EEPROM.commit();
    Serial.printf("[CONFIG] Saved to EEPROM: RelayActiveLow=%d, RadarActiveHigh=%d, Timeout=%us, CustomWifi=%d\n",
                  relayActiveLow ? 1 : 0, radarActiveHigh ? 1 : 0, autoOffTimeoutSec, hasCustomWifi ? 1 : 0);
}

// Known SSIDs fallback
const char* KNOWN_SSIDS[] = {
    "TP-Link_C710",
    "Tung Quan",
    "Tp_LinkC6F2",
    "Xiaozhi-DD2D"
};
const char* KNOWN_PASSWORDS[] = {
    "49878080",
    "23101272005",
    "123456789",
    ""
};
const int KNOWN_NETWORKS_COUNT = 4;

// ESP-NOW Packets
struct __attribute__((packed)) DeskCommandPacket {
    uint8_t magic; // 0x5A
    uint8_t cmd;   // 0: Off, 1: On, 2: Auto
};

struct __attribute__((packed)) DeskStatusPacket {
    uint8_t  magic;             // 0xA5
    uint8_t  is_sitting;        // 1: sitting, 0: left
    uint8_t  lamp_state;        // 1: on, 0: off
    uint32_t sitting_time_sec; // sitting duration in seconds
};

enum ControlMode {
    MODE_AUTO = 0,       // Tự động bật/tắt theo cảm biến radar LD2410
    MODE_MANUAL_OFF = 1, // Ưu tiên ra lệnh TẮT: Đèn luôn TẮT
    MODE_MANUAL_ON = 2   // Ưu tiên ra lệnh BẬT: Đèn luôn BẬT
};

// Global variables
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
DeskStatusPacket statusPacket;
DeskCommandPacket rxPacket;

ControlMode currentMode = MODE_AUTO;
bool currentLampState = false;
bool currentSittingState = false;
unsigned long sittingStartMs = 0;
unsigned long totalSittingSec = 0;
unsigned long lastOccupiedMs = 0;
unsigned long lastStatusReportMs = 0;
int currentChannel = 1;

// Debounce filter for radar
int lastRawRadar = -1;
unsigned long rawRadarChangeMs = 0;
bool debouncedOccupied = false;

// Web Server
ESP8266WebServer server(80);

void setRelay(bool turnOn) {
    currentLampState = turnOn;
    int pinLevel = turnOn ? (relayActiveLow ? LOW : HIGH) : (relayActiveLow ? HIGH : LOW);
    digitalWrite(RELAY_PIN, pinLevel);
    Serial.printf("[RELAY] State set to: %s (Pin D1 = %s | ActiveLow: %s)\n", 
                  turnOn ? "ON (Lamp Sang)" : "OFF (Lamp Tat)", 
                  pinLevel == LOW ? "LOW" : "HIGH",
                  relayActiveLow ? "YES" : "NO");
}

void onDataRecv(uint8_t * mac, uint8_t *incomingData, uint8_t len) {
    if (len == sizeof(DeskCommandPacket)) {
        memcpy(&rxPacket, incomingData, sizeof(rxPacket));
        if (rxPacket.magic == 0x5A) {
            Serial.printf("[ESP-NOW] Received Cmd: %d (%s) from MAC %02X:%02X:%02X:%02X:%02X:%02X\n",
                          rxPacket.cmd,
                          rxPacket.cmd == 1 ? "FORCE ON" : (rxPacket.cmd == 0 ? "FORCE OFF" : "AUTO"),
                          mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
            if (rxPacket.cmd == 1) {
                currentMode = MODE_MANUAL_ON;
                setRelay(true);
                lastOccupiedMs = millis();
            } else if (rxPacket.cmd == 0) {
                currentMode = MODE_MANUAL_OFF;
                setRelay(false);
            } else if (rxPacket.cmd == 2) {
                currentMode = MODE_AUTO;
                if (debouncedOccupied) setRelay(true); else setRelay(false);
            }
        }
    }
}

// Embedded Web Page (Stored in Flash PROGMEM)
const char INDEX_HTML[] PROGMEM = R"rawliteral(<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Smart Desk Assistant - Web Controller</title>
<style>
:root{--bg:#0b0f19;--card:#141c2e;--card-border:#1e293b;--text:#f8fafc;--text-muted:#94a3b8;--primary:#3b82f6;--success:#10b981;--warning:#f59e0b;--danger:#ef4444;--accent:#8b5cf6;}
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
body{background:var(--bg);color:var(--text);padding:14px;min-height:100vh}
.container{max-width:960px;margin:0 auto}
header{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;padding:12px 18px;background:var(--card);border:1px solid var(--card-border);border-radius:14px;margin-bottom:16px;gap:10px}
.brand{display:flex;align-items:center;gap:10px}
.brand h1{font-size:17px;font-weight:700;letter-spacing:0.5px}
.brand span{font-size:11px;color:var(--text-muted);display:block}
.badges{display:flex;flex-wrap:wrap;gap:6px}
.badge{padding:4px 9px;border-radius:20px;font-size:11px;font-weight:600;background:#1e293b;color:#cbd5e1;display:flex;align-items:center;gap:6px}
.pulse{width:7px;height:7px;border-radius:50%;background:var(--success);box-shadow:0 0 8px var(--success);animation:blink 1.5s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}
.grid{display:grid;grid-template-columns:1fr;gap:16px}
@media(min-width:768px){.grid{grid-template-columns:repeat(2,1fr)}}
.card{background:var(--card);border:1px solid var(--card-border);border-radius:14px;padding:18px}
.card-title{font-size:13px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.8px;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.lamp-hero{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:12px 0}
.bulb-box{width:86px;height:86px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:40px;transition:all 0.3s;background:#1e293b;border:2px solid #334155}
.bulb-box.on{background:radial-gradient(circle,#fef08a 0%,#eab308 60%,#ca8a04 100%);box-shadow:0 0 35px #eab308;border-color:#fef08a;transform:scale(1.04)}
.lamp-status{margin-top:10px;font-size:15px;font-weight:700;letter-spacing:0.5px}
.lamp-status.on{color:#fef08a}
.lamp-status.off{color:var(--text-muted)}
.btn-group{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:14px}
.btn{padding:10px 6px;border-radius:8px;border:1px solid #334155;background:#1e293b;color:#e2e8f0;font-size:12px;font-weight:600;cursor:pointer;transition:all 0.2s;text-align:center}
.btn:hover{background:#334155}
.btn.active-auto{background:#065f46;border-color:var(--success);color:#ecfdf5}
.btn.active-on{background:#854d0e;border-color:var(--warning);color:#fefce8}
.btn.active-off{background:#991b1b;border-color:var(--danger);color:#fef2f2}
.timer-hero{text-align:center;padding:6px 0}
.timer-val{font-size:38px;font-weight:800;font-variant-numeric:tabular-nums;color:#38bdf8;letter-spacing:2px}
.timer-lbl{font-size:11px;color:var(--text-muted);margin-top:2px}
.presence-box{display:flex;align-items:center;justify-content:center;gap:10px;padding:10px;background:#0f172a;border-radius:10px;margin-top:10px;font-size:13px;font-weight:600}
.presence-box.occupied{color:var(--success);border:1px solid #065f46}
.presence-box.empty{color:var(--text-muted);border:1px solid #1e293b}
.alert-banner{background:#7c2d12;border:1px solid #ea580c;color:#ffedd5;padding:10px 14px;border-radius:10px;margin-top:12px;font-size:12px;font-weight:600;display:none;align-items:center;gap:8px}
.form-group{margin-bottom:12px}
.form-group label{display:block;font-size:12px;color:var(--text-muted);margin-bottom:6px;font-weight:600}
.form-group select,.form-group input{width:100%;padding:8px 12px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#fff;font-size:13px}
.btn-primary{background:var(--primary);color:#fff;border:none;padding:10px 16px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;width:100%;transition:background 0.2s}
.btn-primary:hover{background:#2563eb}
.btn-secondary{background:#334155;color:#fff;border:none;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;transition:background 0.2s}
.btn-secondary:hover{background:#475569}
.telemetry-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1e293b;font-size:12px}
.telemetry-row:last-child{border-bottom:none}
.telemetry-label{color:var(--text-muted)}
.telemetry-value{font-weight:600;color:#f1f5f9}
#toast{position:fixed;bottom:20px;right:20px;background:#1e293b;border:1px solid var(--success);color:#fff;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:600;opacity:0;transition:opacity 0.3s;pointer-events:none;z-index:99}
#toast.show{opacity:1}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="brand">
      <div style="font-size:24px">⚡</div>
      <div>
        <h1>SMART DESK ASSISTANT</h1>
        <span>ESP32-S3 Master & ESP8266 Slave Controller</span>
      </div>
    </div>
    <div class="badges">
      <div class="badge"><div class="pulse"></div>ONLINE</div>
      <div class="badge" id="b-ch">KÊNH: --</div>
      <div class="badge" id="b-ip">IP: --</div>
      <div class="badge" id="b-rssi">WIFI: -- dBm</div>
    </div>
  </header>

  <div class="grid">
    <!-- Card 1: Điều khiển đèn -->
    <div class="card">
      <div class="card-title">💡 ĐIỀU KHIỂN ĐÈN BÀN</div>
      <div class="lamp-hero">
        <div id="bulb" class="bulb-box">💡</div>
        <div id="lamp-text" class="lamp-status off">ĐÈN ĐANG TẮT</div>
      </div>
      <div class="btn-group">
        <button id="btn-auto" class="btn" onclick="setMode('auto')">🟢 TỰ ĐỘNG</button>
        <button id="btn-on" class="btn" onclick="setMode('on')">💡 BẬT ĐÈN</button>
        <button id="btn-off" class="btn" onclick="setMode('off')">🌑 TẮT ĐÈN</button>
      </div>
      <div style="margin-top:12px;font-size:11px;color:var(--text-muted)">
        • <b>TỰ ĐỘNG</b>: Cảm biến radar tự động bật khi có người, tự tắt khi rời bàn.<br>
        • <b>BẬT/TẮT</b>: Ép đèn giữ trạng thái cố định (Ưu tiên người dùng).
      </div>
    </div>

    <!-- Card 2: Công thái học & Radar -->
    <div class="card">
      <div class="card-title">🪑 CÔNG THÁI HỌC & CẢM BIẾN RADAR</div>
      <div class="presence-box empty" id="presence-box">
        <span id="presence-icon">⚪</span>
        <span id="presence-text">ĐÃ RỜI BÀN LÀM VIỆC</span>
      </div>
      <div class="timer-hero">
        <div class="timer-val" id="sitting-timer">00:00:00</div>
        <div class="timer-lbl">THỜI GIAN NGỒI LÀM VIỆC LIÊN TỤC</div>
      </div>
      <div id="health-alert" class="alert-banner">
        ⚠️ <b>CẢNH BÁO SỨC KHỎE:</b> Bạn đã ngồi liên tục hơn 45 phút! Hãy đứng dậy vận động và uống nước.
      </div>
      <div style="margin-top:10px">
        <div class="telemetry-row">
          <span class="telemetry-label">Cảm biến Radar LD2410 (D2)</span>
          <span class="telemetry-value" id="val-d2">LOW (Trống)</span>
        </div>
        <div class="telemetry-row">
          <span class="telemetry-label">Thời gian chờ tắt (Timeout)</span>
          <span class="telemetry-value" id="val-timeout">15s</span>
        </div>
      </div>
    </div>

    <!-- Card 3: Cấu hình phần cứng -->
    <div class="card">
      <div class="card-title">⚙️ CẤU HÌNH PHẦN CỨNG (EEPROM)</div>
      <div class="form-group">
        <label>Cực kích hoạt Relay (IN1 - D1)</label>
        <select id="cfg-relay">
          <option value="0">Active-HIGH (Jumper H - Mức HIGH kích bật)</option>
          <option value="1">Active-LOW (Jumper L - Mức LOW kích bật)</option>
        </select>
      </div>
      <div class="form-group">
        <label>Logic ngõ ra Radar LD2410 (OUT - D2)</label>
        <select id="cfg-radar">
          <option value="1">Active-HIGH (Mặc định: Có người = HIGH)</option>
          <option value="0">Active-LOW (Đảo ngược: Có người = LOW)</option>
        </select>
      </div>
      <div class="form-group">
        <label>Thời gian chờ tự tắt đèn khi rời bàn (giây)</label>
        <input type="number" id="cfg-timeout" min="5" max="600" value="15">
      </div>
      <button class="btn-primary" onclick="saveConfig()">💾 LƯU CẤU HÌNH VÀO EEPROM</button>
    </div>

    <!-- Card 4: ESP-NOW & Trợ lý Xiaozhi -->
    <div class="card">
      <div class="card-title">📡 KẾT NỐI ESP-NOW & ESP32-S3</div>
      <div class="telemetry-row">
        <span class="telemetry-label">Kênh sóng ESP-NOW (Channel)</span>
        <span class="telemetry-value" id="val-ch">Kênh --</span>
      </div>
      <div class="telemetry-row">
        <span class="telemetry-label">Broadcast Peer</span>
        <span class="telemetry-value">FF:FF:FF:FF:FF:FF</span>
      </div>
      <div class="telemetry-row">
        <span class="telemetry-label">Độ trễ truyền nhận</span>
        <span class="telemetry-value">&lt; 5ms</span>
      </div>
      <div style="margin-top:14px">
        <button class="btn-secondary" style="width:100%" onclick="pingS3()">📡 BẮN GÓI TIN TEST SANG ESP32-S3</button>
      </div>
    </div>

    <!-- Card 5: Cấu hình WiFi (Toàn chiều rộng) -->
    <div class="card" style="grid-column:1 / -1">
      <div class="card-title">📶 CẤU HÌNH WIFI & ĐỒNG BỘ KÊNH ROUTER</div>
      <div style="display:flex;gap:10px;margin-bottom:12px;align-items:center">
        <button class="btn-secondary" onclick="scanWifi()">🔍 Quét mạng WiFi xung quanh</button>
        <span id="scan-status" style="font-size:12px;color:var(--text-muted)"></span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div class="form-group">
          <label>Tên mạng WiFi (SSID)</label>
          <input type="text" id="wifi-ssid" placeholder="Chọn từ danh sách hoặc nhập tên WiFi">
        </div>
        <div class="form-group">
          <label>Mật khẩu WiFi</label>
          <input type="password" id="wifi-pass" placeholder="Nhập mật khẩu WiFi">
        </div>
      </div>
      <div id="wifi-list" style="margin-bottom:12px;display:flex;flex-wrap:wrap;gap:6px"></div>
      <button class="btn-primary" onclick="connectWifi()">🔗 LƯU & KẾT NỐI WIFI</button>
      <div style="margin-top:8px;font-size:11px;color:var(--text-muted)">
        💡 Mẹo: Khi ESP8266 và ESP32-S3 cùng kết nối vào một mạng WiFi, kênh sóng sẽ tự động khớp 100%, giúp ESP-NOW hoạt động siêu nhạy.
      </div>
    </div>
  </div>
</div>

<div id="toast">Thông báo</div>

<script>
function showToast(msg, isErr=false){
  var t=document.getElementById('toast');
  t.innerText=msg;
  t.style.borderColor=isErr?'var(--danger)':'var(--success)';
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3000);
}

function fmtTime(sec){
  var h=Math.floor(sec/3600);
  var m=Math.floor((sec%3600)/60);
  var s=sec%60;
  return (h<10?'0':'')+h+':'+(m<10?'0':'')+m+':'+(s<10?'0':'')+s;
}

function updateUI(d){
  document.getElementById('b-ch').innerText='KÊNH: '+d.channel;
  document.getElementById('b-ip').innerText='IP: '+d.ip;
  document.getElementById('b-rssi').innerText='WIFI: '+(d.rssi?d.rssi+' dBm':'AP Mode');
  document.getElementById('val-ch').innerText='Kênh '+d.channel;
  document.getElementById('val-timeout').innerText=d.timeout_sec+'s';

  var bulb=document.getElementById('bulb');
  var lampTxt=document.getElementById('lamp-text');
  if(d.lamp===1){
    bulb.classList.add('on');
    lampTxt.innerText='ĐÈN ĐANG BẬT';
    lampTxt.className='lamp-status on';
  }else{
    bulb.classList.remove('on');
    lampTxt.innerText='ĐÈN ĐANG TẮT';
    lampTxt.className='lamp-status off';
  }

  document.getElementById('btn-auto').className='btn'+(d.mode==='AUTO'?' active-auto':'');
  document.getElementById('btn-on').className='btn'+(d.mode==='MANUAL_ON'?' active-on':'');
  document.getElementById('btn-off').className='btn'+(d.mode==='MANUAL_OFF'?' active-off':'');

  var presBox=document.getElementById('presence-box');
  var presIcon=document.getElementById('presence-icon');
  var presTxt=document.getElementById('presence-text');
  if(d.sitting===1){
    presBox.className='presence-box occupied';
    presIcon.innerText='🟢';
    presTxt.innerText='ĐANG NGỒI TẠI BÀN LÀM VIỆC';
  }else{
    presBox.className='presence-box empty';
    presIcon.innerText='⚪';
    presTxt.innerText='ĐÃ RỜI BÀN LÀM VIỆC';
  }
  document.getElementById('sitting-timer').innerText=fmtTime(d.sitting_time);

  var alertBox=document.getElementById('health-alert');
  if(d.sitting_time>=2700){
    alertBox.style.display='flex';
  }else{
    alertBox.style.display='none';
  }

  document.getElementById('val-d2').innerText=(d.radar_raw===1?'HIGH':'LOW')+' ('+(d.debounced===1?'Có người':'Trống')+')';
}

function fetchStatus(){
  fetch('/api/status')
    .then(r=>r.json())
    .then(d=>{
      updateUI(d);
      if(!window.configLoaded){
        document.getElementById('cfg-relay').value=d.relay_low;
        document.getElementById('cfg-radar').value=d.radar_high;
        document.getElementById('cfg-timeout').value=d.timeout_sec;
        window.configLoaded=true;
      }
    })
    .catch(e=>console.error('Fetch error:',e));
}

function setMode(m){
  fetch('/api/control?mode='+m,{method:'POST'})
    .then(r=>r.json())
    .then(d=>{
      showToast('Đã chuyển sang chế độ: '+m.toUpperCase());
      fetchStatus();
    })
    .catch(e=>showToast('Lỗi gửi lệnh điều khiển!',true));
}

function saveConfig(){
  var rLow=document.getElementById('cfg-relay').value;
  var radHigh=document.getElementById('cfg-radar').value;
  var timeout=document.getElementById('cfg-timeout').value;
  var body='relay_low='+rLow+'&radar_high='+radHigh+'&timeout_sec='+timeout;

  fetch('/api/config',{
    method:'POST',
    headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:body
  })
  .then(r=>r.json())
  .then(d=>{
    showToast('Đã lưu cấu hình vào EEPROM thành công!');
    fetchStatus();
  })
  .catch(e=>showToast('Lỗi lưu cấu hình!',true));
}

function pingS3(){
  fetch('/api/ping-s3',{method:'POST'})
    .then(r=>r.json())
    .then(d=>showToast(d.message||'Đã gửi gói tin test ESP-NOW!'))
    .catch(e=>showToast('Lỗi gửi gói tin!',true));
}

function scanWifi(){
  var st=document.getElementById('scan-status');
  st.innerText='Đang quét WiFi...';
  fetch('/api/wifi/scan')
    .then(r=>r.json())
    .then(list=>{
      st.innerText='Tìm thấy '+list.length+' mạng WiFi:';
      var box=document.getElementById('wifi-list');
      box.innerHTML='';
      list.forEach(w=>{
        var b=document.createElement('div');
        b.className='badge';
        b.style.cursor='pointer';
        b.innerHTML='📶 <b>'+w.ssid+'</b> (Ch '+w.ch+', '+w.rssi+'dBm)';
        b.onclick=function(){
          document.getElementById('wifi-ssid').value=w.ssid;
          document.getElementById('wifi-pass').focus();
        };
        box.appendChild(b);
      });
    })
    .catch(e=>{st.innerText='Lỗi quét WiFi!';});
}

function connectWifi(){
  var s=document.getElementById('wifi-ssid').value;
  var p=document.getElementById('wifi-pass').value;
  if(!s){showToast('Vui lòng nhập tên WiFi!',true);return;}
  var body='ssid='+encodeURIComponent(s)+'&pass='+encodeURIComponent(p);
  fetch('/api/wifi/save',{
    method:'POST',
    headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:body
  })
  .then(r=>r.json())
  .then(d=>{
    showToast('Đã lưu WiFi! Thiết bị đang kết nối...');
  })
  .catch(e=>showToast('Lỗi gửi thông tin WiFi!',true));
}

setInterval(fetchStatus, 1500);
fetchStatus();
</script>
</body>
</html>
)rawliteral";

// Web API Handlers
void handleRoot() {
    server.send_P(200, "text/html", INDEX_HTML);
}

void handleApiStatus() {
    char json[420];
    String ipStr = (WiFi.status() == WL_CONNECTED) ? WiFi.localIP().toString() : WiFi.softAPIP().toString();
    snprintf(json, sizeof(json),
        "{\"mode\":\"%s\",\"mode_code\":%d,\"lamp\":%d,\"sitting\":%d,\"sitting_time\":%lu,"
        "\"radar_raw\":%d,\"debounced\":%d,\"channel\":%d,\"rssi\":%d,\"ip\":\"%s\","
        "\"relay_low\":%d,\"radar_high\":%d,\"timeout_sec\":%u,\"uptime\":%lu}",
        (currentMode == MODE_AUTO) ? "AUTO" : ((currentMode == MODE_MANUAL_OFF) ? "MANUAL_OFF" : "MANUAL_ON"),
        (int)currentMode,
        currentLampState ? 1 : 0,
        currentSittingState ? 1 : 0,
        currentSittingState ? totalSittingSec : 0,
        lastRawRadar,
        debouncedOccupied ? 1 : 0,
        currentChannel,
        WiFi.status() == WL_CONNECTED ? (int)WiFi.RSSI() : 0,
        ipStr.c_str(),
        relayActiveLow ? 1 : 0,
        radarActiveHigh ? 1 : 0,
        autoOffTimeoutSec,
        millis() / 1000
    );
    server.send(200, "application/json", json);
}

void handleApiControl() {
    if (server.hasArg("mode")) {
        String m = server.arg("mode");
        if (m == "auto" || m == "0") {
            currentMode = MODE_AUTO;
            setRelay(debouncedOccupied);
            Serial.println("[WEB] Switched to MODE_AUTO");
        } else if (m == "on" || m == "1") {
            currentMode = MODE_MANUAL_ON;
            setRelay(true);
            lastOccupiedMs = millis();
            Serial.println("[WEB] Switched to MODE_MANUAL_ON");
        } else if (m == "off" || m == "2") {
            currentMode = MODE_MANUAL_OFF;
            setRelay(false);
            Serial.println("[WEB] Switched to MODE_MANUAL_OFF");
        }
    }
    server.send(200, "application/json", "{\"success\":true}");
}

void handleApiConfig() {
    if (server.hasArg("relay_low")) {
        relayActiveLow = (server.arg("relay_low") == "1");
    }
    if (server.hasArg("radar_high")) {
        radarActiveHigh = (server.arg("radar_high") == "1");
    }
    if (server.hasArg("timeout_sec")) {
        int t = server.arg("timeout_sec").toInt();
        if (t >= 5 && t <= 3600) {
            autoOffTimeoutSec = t;
        }
    }
    saveSettings();
    setRelay(currentLampState);
    server.send(200, "application/json", "{\"success\":true}");
}

void handleApiWifiScan() {
    int n = WiFi.scanNetworks();
    String json = "[";
    for (int i = 0; i < n; i++) {
        if (i > 0) json += ",";
        json += "{\"ssid\":\"" + WiFi.SSID(i) + "\",\"rssi\":" + String(WiFi.RSSI(i)) + ",\"ch\":" + String(WiFi.channel(i)) + "}";
    }
    json += "]";
    server.send(200, "application/json", json);
}

void handleApiWifiSave() {
    if (server.hasArg("ssid")) {
        String s = server.arg("ssid");
        String p = server.hasArg("pass") ? server.arg("pass") : "";
        memset(customSsid, 0, sizeof(customSsid));
        memset(customPass, 0, sizeof(customPass));
        s.toCharArray(customSsid, sizeof(customSsid));
        p.toCharArray(customPass, sizeof(customPass));
        hasCustomWifi = true;
        saveSettings();
        server.send(200, "application/json", "{\"success\":true,\"message\":\"Saved WiFi! Reconnecting...\"}");
        Serial.printf("[WIFI] Connecting to new WiFi: %s\n", customSsid);
        WiFi.begin(customSsid, customPass);
    } else {
        server.send(400, "application/json", "{\"error\":\"Missing ssid\"}");
    }
}

void handleApiPingS3() {
    statusPacket.magic = 0xA5;
    statusPacket.is_sitting = currentSittingState ? 1 : 0;
    statusPacket.lamp_state = currentLampState ? 1 : 0;
    statusPacket.sitting_time_sec = currentSittingState ? totalSittingSec : 0;
    esp_now_send(broadcastAddress, (uint8_t *)&statusPacket, sizeof(statusPacket));
    Serial.println("[WEB] Sent broadcast ping to ESP32-S3 via ESP-NOW");
    server.send(200, "application/json", "{\"success\":true,\"message\":\"Đã gửi gói tin ESP-NOW sang ESP32-S3!\"}");
}

void handleNotFound() {
    server.send(404, "text/plain", "Not Found");
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n==========================================");
    Serial.println(" SMART DESK ASSISTANT - ESP8266 SLAVE ");
    Serial.println("==========================================");

    EEPROM.begin(128);
    if (EEPROM.read(0) == EEPROM_MAGIC) {
        relayActiveLow = (EEPROM.read(1) == 1);
        radarActiveHigh = (EEPROM.read(2) == 1);
        uint16_t savedTimeout = EEPROM.read(3) | (EEPROM.read(4) << 8);
        if (savedTimeout >= 5 && savedTimeout <= 3600) {
            autoOffTimeoutSec = savedTimeout;
        } else {
            autoOffTimeoutSec = 15;
        }
        hasCustomWifi = (EEPROM.read(5) == 1);
        if (hasCustomWifi) {
            for (int i = 0; i < 32; i++) customSsid[i] = (char)EEPROM.read(6 + i);
            customSsid[32] = '\0';
            for (int i = 0; i < 64; i++) customPass[i] = (char)EEPROM.read(38 + i);
            customPass[64] = '\0';
        }
        Serial.printf("[CONFIG] Loaded from EEPROM: RelayActiveLow=%s, RadarActiveHigh=%s, Timeout=%us, CustomWifi=%s\n",
                      relayActiveLow ? "YES (Jumper L)" : "NO (Jumper H)",
                      radarActiveHigh ? "YES (HIGH=Occupied)" : "NO (LOW=Occupied)",
                      autoOffTimeoutSec,
                      hasCustomWifi ? customSsid : "NONE");
    } else {
        relayActiveLow = false;
        radarActiveHigh = true;
        autoOffTimeoutSec = 15;
        hasCustomWifi = false;
        memset(customSsid, 0, sizeof(customSsid));
        memset(customPass, 0, sizeof(customPass));
        saveSettings();
        Serial.println("[CONFIG] Initialized default settings to EEPROM (15s timeout, Active-HIGH)");
    }

    pinMode(RADAR_PIN, INPUT);
    pinMode(RELAY_PIN, OUTPUT);
    setRelay(false);

    // Initialize SoftAP + Station mode so web dashboard is ALWAYS reachable
    WiFi.mode(WIFI_AP_STA);
    WiFi.softAP("SmartDesk-Assistant", "12345678");
    Serial.printf("[WIFI] SoftAP started: 'SmartDesk-Assistant' (Pass: 12345678) | IP: %s\n",
                  WiFi.softAPIP().toString().c_str());

    // Auto-discover router WiFi channel or connect to configured network
    Serial.println("[WIFI] Scanning networks to synchronize channel with ESP32...");
    int n = WiFi.scanNetworks();
    int targetChannel = 10;
    int matchedIdx = -1;
    bool matchCustom = false;

    for (int i = 0; i < n; i++) {
        String ssid = WiFi.SSID(i);
        int ch = WiFi.channel(i);
        Serial.printf("[WIFI] Found SSID: %-25s | Ch: %2d | RSSI: %3d dBm\n", ssid.c_str(), ch, (int)WiFi.RSSI(i));

        if (hasCustomWifi && strlen(customSsid) > 0 && ssid == String(customSsid)) {
            targetChannel = ch;
            matchCustom = true;
            Serial.printf("[WIFI] >>> MATCHED Custom EEPROM Network: %s on Channel %d!\n", ssid.c_str(), ch);
            break;
        }

        for (int k = 0; k < KNOWN_NETWORKS_COUNT; k++) {
            if (ssid == KNOWN_SSIDS[k]) {
                targetChannel = ch;
                matchedIdx = k;
                Serial.printf("[WIFI] >>> MATCHED Known Network: %s on Channel %d!\n", ssid.c_str(), ch);
                break;
            }
        }
        if (matchedIdx >= 0) break;
    }

    currentChannel = targetChannel;

    // Connect to WiFi if matched
    if (matchCustom) {
        Serial.printf("[WIFI] Connecting to Custom '%s' on Channel %d (Timeout: 10s)...\n", customSsid, targetChannel);
        WiFi.begin(customSsid, customPass);
    } else if (matchedIdx >= 0) {
        Serial.printf("[WIFI] Connecting to '%s' on Channel %d (Timeout: 10s)...\n", KNOWN_SSIDS[matchedIdx], targetChannel);
        WiFi.begin(KNOWN_SSIDS[matchedIdx], KNOWN_PASSWORDS[matchedIdx]);
    }

    if (matchCustom || matchedIdx >= 0) {
        unsigned long startConnect = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - startConnect < 10000) {
            delay(250);
            Serial.print(".");
        }
        Serial.println();
        if (WiFi.status() == WL_CONNECTED) {
            currentChannel = WiFi.channel();
            Serial.printf("[WIFI] Connected! Router IP: %s | Locked Channel: %d\n", 
                          WiFi.localIP().toString().c_str(), currentChannel);
        } else {
            Serial.printf("[WIFI] Router connect timeout, keeping SoftAP on Channel %d\n", targetChannel);
        }
    }

    // Disable WiFi sleep for 100% responsive ESP-NOW and Web Server
    wifi_set_sleep_type(NONE_SLEEP_T);

    // Initialize ESP-NOW
    if (esp_now_init() != 0) {
        Serial.println("[ESP-NOW] Init Failed!");
    } else {
        Serial.printf("[ESP-NOW] Init Success on Channel %d!\n", currentChannel);
        esp_now_set_self_role(ESP_NOW_ROLE_COMBO);
        esp_now_register_recv_cb(onDataRecv);
        esp_now_add_peer(broadcastAddress, ESP_NOW_ROLE_COMBO, currentChannel, NULL, 0);
    }

    // Initialize Web Server routes
    server.on("/", HTTP_GET, handleRoot);
    server.on("/api/status", HTTP_GET, handleApiStatus);
    server.on("/api/control", HTTP_POST, handleApiControl);
    server.on("/api/config", HTTP_POST, handleApiConfig);
    server.on("/api/wifi/scan", HTTP_GET, handleApiWifiScan);
    server.on("/api/wifi/save", HTTP_POST, handleApiWifiSave);
    server.on("/api/ping-s3", HTTP_POST, handleApiPingS3);
    server.onNotFound(handleNotFound);
    server.begin();
    Serial.println("[HTTP] Web Server started on port 80!");

    if (MDNS.begin("smartdesk")) {
        Serial.println("[mDNS] Responder started at http://smartdesk.local");
        MDNS.addService("http", "tcp", 80);
    }
}

void loop() {
    unsigned long now = millis();

    // 0. Handle Web Server & mDNS
    server.handleClient();
    MDNS.update();

    // 1. Debounce Radar Input (D2)
    int rawRadar = digitalRead(RADAR_PIN);
    if (rawRadar != lastRawRadar) {
        lastRawRadar = rawRadar;
        rawRadarChangeMs = now;
    }

    if (now - rawRadarChangeMs >= 100) {
        bool newOccupied = radarActiveHigh ? (rawRadar == HIGH) : (rawRadar == LOW);
        if (newOccupied != debouncedOccupied) {
            debouncedOccupied = newOccupied;
            if (debouncedOccupied) {
                Serial.printf("[RADAR] Phat hien nguoi ngoi vao ban! (D2=%s, Logic=%s)\n",
                              rawRadar == HIGH ? "HIGH" : "LOW",
                              radarActiveHigh ? "Active-HIGH" : "Active-LOW");
            } else {
                Serial.printf("[RADAR] Phat hien roi ban (D2=%s, Logic=%s)\n",
                              rawRadar == HIGH ? "HIGH" : "LOW",
                              radarActiveHigh ? "Active-HIGH" : "Active-LOW");
            }
        }
    }

    // 2. Desk Automation Logic
    unsigned long timeoutMs = ((unsigned long)autoOffTimeoutSec) * 1000UL;

    if (debouncedOccupied) {
        lastOccupiedMs = now;
        if (!currentSittingState) {
            currentSittingState = true;
            sittingStartMs = now;
            Serial.println("[DESK] Bat dau dem thoi gian ngoi ban lam viec!");
        }
        totalSittingSec = (now - sittingStartMs) / 1000;

        if (currentMode == MODE_AUTO) {
            if (!currentLampState) setRelay(true);
        } else if (currentMode == MODE_MANUAL_OFF) {
            if (currentLampState) setRelay(false);
        } else if (currentMode == MODE_MANUAL_ON) {
            if (!currentLampState) setRelay(true);
        }
    } else {
        if (now - lastOccupiedMs >= timeoutMs) {
            if (currentSittingState) {
                currentSittingState = false;
                Serial.println("[DESK] Nguoi dung da roi ban (het timeout)!");
            }
            if (currentMode == MODE_AUTO) {
                if (currentLampState) setRelay(false);
            }
        }

        // Long absence restore to AUTO mode
        if (now - lastOccupiedMs >= 300000UL) {
            if (currentMode != MODE_AUTO) {
                currentMode = MODE_AUTO;
                Serial.println("[DESK] Vang mat hon 5 phut, tu dong khoi phuc che do AUTO cho lan sau!");
            }
        }
    }

    // 3. Serial Command Interface
    if (Serial.available()) {
        char c = Serial.read();
        if (c == '1') {
            Serial.println("[SERIAL] Manual Command: Turn ON");
            currentMode = MODE_MANUAL_ON;
            setRelay(true);
            lastOccupiedMs = now;
        } else if (c == '0') {
            Serial.println("[SERIAL] Manual Command: Turn OFF (Priority over sensor)");
            currentMode = MODE_MANUAL_OFF;
            setRelay(false);
        } else if (c == 'a' || c == 'A') {
            Serial.println("[SERIAL] Manual Command: Reset AUTO mode");
            currentMode = MODE_AUTO;
            if (debouncedOccupied) setRelay(true); else setRelay(false);
        } else if (c == 'p' || c == 'P') {
            relayActiveLow = !relayActiveLow;
            saveSettings();
            Serial.printf("[SERIAL] Toggled Relay Polarity: ActiveLow is now %s (Saved to EEPROM)\n", 
                          relayActiveLow ? "YES (Jumper L)" : "NO (Jumper H)");
            setRelay(currentLampState);
        } else if (c == 'r' || c == 'R') {
            radarActiveHigh = !radarActiveHigh;
            saveSettings();
            Serial.printf("[SERIAL] Toggled Radar Logic: ActiveHigh is now %s (Saved to EEPROM)\n", 
                          radarActiveHigh ? "YES (HIGH=Occupied)" : "NO (LOW=Occupied)");
        } else if (c == 's' || c == 'S') {
            const char* modeStr = (currentMode == MODE_AUTO) ? "AUTO" : 
                                  ((currentMode == MODE_MANUAL_OFF) ? "MANUAL_OFF" : "MANUAL_ON");
            String ipStr = (WiFi.status() == WL_CONNECTED) ? WiFi.localIP().toString() : WiFi.softAPIP().toString();
            Serial.printf("[DIAG] Mode: %s | Sitting: %d | Lamp: %d | Time: %lus | Radar(D2): %d | Ch: %d | IP: %s\n",
                          modeStr,
                          currentSittingState ? 1 : 0, currentLampState ? 1 : 0,
                          currentSittingState ? totalSittingSec : 0,
                          rawRadar, currentChannel, ipStr.c_str());
        } else if (c == 'h' || c == 'H' || c == '?') {
            Serial.println("\n--- LENH DIEU KHIEN & HIEU CHINH ESP8266 ---");
            Serial.println(" '0' : Ep TAT den (Uu tien hon cam bien)");
            Serial.println(" '1' : Ep BAT den (Uu tien hon cam bien)");
            Serial.println(" 'a' : Chuyen ve che do TU DONG (AUTO)");
            Serial.println(" 'p' : Dao cuc Relay (Active-LOW <-> Active-HIGH) & Luu EEPROM");
            Serial.println(" 'r' : Dao cuc Radar (Active-HIGH <-> Active-LOW) & Luu EEPROM");
            Serial.println(" 's' : Xem chan doan trang thai chi tiet (Diagnostics)");
            Serial.println("----------------------------------------------\n");
        }
    }

    // 4. Send Status Report Every 1 Second via ESP-NOW Broadcast
    if (now - lastStatusReportMs >= 1000) {
        lastStatusReportMs = now;
        statusPacket.magic = 0xA5;
        statusPacket.is_sitting = currentSittingState ? 1 : 0;
        statusPacket.lamp_state = currentLampState ? 1 : 0;
        statusPacket.sitting_time_sec = currentSittingState ? totalSittingSec : 0;

        esp_now_send(broadcastAddress, (uint8_t *) &statusPacket, sizeof(statusPacket));

        Serial.printf("[STATUS] Sitting: %d | Lamp: %d | Time: %lus | Radar (D2): %s (raw=%d) | Ch: %d\n",
                      statusPacket.is_sitting,
                      statusPacket.lamp_state,
                      statusPacket.sitting_time_sec,
                      debouncedOccupied ? "HIGH" : "LOW",
                      rawRadar,
                      currentChannel);
    }

    delay(10);
}
