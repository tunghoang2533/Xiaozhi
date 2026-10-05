"""
Smart Desk Assistant - Web Dashboard Server (PC Bridge)
Allows controlling and configuring both ESP8266 and ESP32-S3 from a local browser.
Supports nearby WiFi scanning & one-click dual WiFi synchronization for both ESPs.
"""

import os
import sys
import time
import json
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import serial
import serial.tools.list_ports

SERIAL_PORT = 'COM8'
BAUD_RATE = 115200
HTTP_PORT = 8080

ser_lock = threading.Lock()
ser = None

scanned_lock = threading.Lock()
scanned_networks = []

# Cached telemetry state
state = {
    "mode": "AUTO",
    "mode_code": 0,
    "lamp": 0,
    "sitting": 0,
    "sitting_time": 0,
    "radar_raw": 0,
    "debounced": 0,
    "channel": 10,
    "rssi": -60,
    "ip": "192.168.4.1",
    "relay_low": 0,
    "radar_high": 1,
    "timeout_sec": 15,
    "uptime": 0,
    "esp32_connected": False
}

def scan_all_wifi():
    global scanned_networks
    # 1. Trigger ESP8266 2.4GHz scan
    send_serial("c\n")

    # 2. Query Windows netsh for instant nearby APs
    try:
        out = subprocess.check_output("netsh wlan show networks mode=bssid", shell=True).decode('cp1252', errors='ignore')
        current_ssid = None
        current_signal = ""
        current_channel = ""
        for l in out.splitlines():
            l = l.strip()
            if l.startswith("SSID ") and not l.startswith("BSSID"):
                parts = l.split(":", 1)
                if len(parts) > 1:
                    current_ssid = parts[1].strip()
            elif l.startswith("Signal"):
                parts = l.split(":", 1)
                if len(parts) > 1:
                    current_signal = parts[1].strip()
            elif l.startswith("Channel"):
                parts = l.split(":", 1)
                if len(parts) > 1:
                    current_channel = parts[1].strip()
                    if current_ssid:
                        with scanned_lock:
                            if not any(item["ssid"] == current_ssid for item in scanned_networks):
                                sig_pct = int(current_signal.replace("%", "")) if "%" in current_signal else 70
                                rssi_val = -100 + (sig_pct // 2)
                                scanned_networks.append({
                                    "ssid": current_ssid,
                                    "channel": current_channel,
                                    "rssi": rssi_val,
                                    "signal": current_signal,
                                    "source": "PC Wi-Fi"
                                })
    except Exception as e:
        pass

    # 3. Add default known networks if not present
    known_defaults = ["Tung Quan", "TP-Link_C710", "Tp_LinkC6F2", "Xiaozhi-DD2D"]
    with scanned_lock:
        for k in known_defaults:
            if not any(item["ssid"] == k for item in scanned_networks):
                scanned_networks.append({
                    "ssid": k,
                    "channel": 10,
                    "rssi": -65,
                    "signal": "75%",
                    "source": "Đã lưu"
                })
        return list(scanned_networks)

def serial_worker():
    global ser, state, scanned_networks
    while True:
        try:
            if ser is None or not ser.is_open:
                try:
                    new_ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.2)
                    new_ser.dtr = False
                    new_ser.rts = False
                    time.sleep(0.1)
                    new_ser.reset_input_buffer()
                    with ser_lock:
                        ser = new_ser
                    print(f"[SERIAL] Connected to ESP on {SERIAL_PORT} (DTR=False, RTS=False)")
                    state["esp32_connected"] = True
                except Exception as e:
                    state["esp32_connected"] = False
                    time.sleep(1.5)
                    continue

            line = None
            with ser_lock:
                if ser and ser.is_open:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()

            if not line:
                time.sleep(0.02)
                continue

            # Parse [STATUS] line: Sitting: 0 | Lamp: 0 | Time: 0s | Radar (D2): LOW (raw=0) | Ch: 10
            if "[STATUS]" in line:
                try:
                    parts = line.split("|")
                    for p in parts:
                        p = p.strip()
                        if "Sitting:" in p:
                            state["sitting"] = int(p.split(":")[1].strip())
                        elif "Lamp:" in p:
                            state["lamp"] = int(p.split(":")[1].strip())
                        elif "Time:" in p:
                            t_str = p.split(":")[1].strip().replace("s", "")
                            state["sitting_time"] = int(t_str)
                        elif "Ch:" in p:
                            state["channel"] = int(p.split(":")[1].strip())
                        elif "Radar (D2):" in p:
                            state["debounced"] = 1 if "HIGH" in p else 0
                            if "raw=" in p:
                                raw_val = p.split("raw=")[1].replace(")", "").strip()
                                state["radar_raw"] = int(raw_val)
                except Exception as e:
                    pass

            # Parse [WIFI] Found SSID: ... from ESP8266 scan
            elif "[WIFI] Found SSID:" in line:
                try:
                    parts = line.split("|")
                    s = parts[0].split("Found SSID:")[1].strip()
                    c = int(parts[1].split("Ch:")[1].strip())
                    r = int(parts[2].split("RSSI:")[1].replace("dBm", "").strip())
                    if s:
                        with scanned_lock:
                            existing = [item for item in scanned_networks if item["ssid"] == s]
                            if not existing:
                                sig_pct = max(0, min(100, 2 * (r + 100)))
                                scanned_networks.append({
                                    "ssid": s,
                                    "channel": c,
                                    "rssi": r,
                                    "signal": f"{sig_pct}%",
                                    "source": "ESP8266 (2.4GHz)"
                                })
                except Exception as e:
                    pass

            # Parse [RELAY] line: State set to: ON (Lamp Sang) / OFF (Lamp Tat)
            elif "[RELAY]" in line:
                if "ON" in line or "Sang" in line:
                    state["lamp"] = 1
                elif "OFF" in line or "Tat" in line:
                    state["lamp"] = 0

            # Parse [DIAG] line
            elif "[DIAG]" in line:
                try:
                    parts = line.split("|")
                    for p in parts:
                        p = p.strip()
                        if "Mode:" in p:
                            m = p.split(":")[1].strip()
                            state["mode"] = m
                            state["mode_code"] = 0 if m == "AUTO" else (1 if m == "MANUAL_OFF" else 2)
                        elif "IP:" in p:
                            state["ip"] = p.split(":")[1].strip()
                except Exception as e:
                    pass

            # Parse [MODE] line
            elif "[MODE]" in line:
                if "MANUAL_ON" in line:
                    state["mode"] = "MANUAL_ON"
                    state["mode_code"] = 2
                    state["lamp"] = 1
                elif "MANUAL_OFF" in line:
                    state["mode"] = "MANUAL_OFF"
                    state["mode_code"] = 1
                    state["lamp"] = 0
                elif "AUTO" in line:
                    state["mode"] = "AUTO"
                    state["mode_code"] = 0

        except Exception as e:
            state["esp32_connected"] = False
            with ser_lock:
                if ser:
                    try:
                        ser.close()
                    except:
                        pass
                    ser = None
            time.sleep(1)

def send_serial(cmd_str):
    global ser
    with ser_lock:
        if ser and ser.is_open:
            ser.write(cmd_str.encode('utf-8'))
            ser.flush()
            print(f"[SERIAL-TX] Sent command: {cmd_str.strip()}")
            return True
    return False

# HTML Dashboard
HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Smart Desk Assistant - PC Dashboard</title>
<style>
:root{--bg:#0b0f19;--card:#141c2e;--card-border:#1e293b;--text:#f8fafc;--text-muted:#94a3b8;--primary:#3b82f6;--success:#10b981;--warning:#f59e0b;--danger:#ef4444;--accent:#8b5cf6;}
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
body{background:var(--bg);color:var(--text);padding:14px;min-height:100vh}
.container{max-width:960px;margin:0 auto}
header{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;padding:12px 18px;background:var(--card);border:1px solid var(--card-border);border-radius:14px;margin-bottom:16px;gap:10px}
.brand{display:flex;align-items:center;gap:10px}
.brand h1{font-size:17px;font-weight:700}
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
.btn-primary{background:var(--primary);color:#fff;border:none;padding:10px 16px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;width:100%;transition:background 0.2s}
.btn-primary:hover{background:#2563eb}
.btn-secondary{background:#334155;color:#fff;border:none;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;transition:background 0.2s}
.btn-secondary:hover{background:#475569}
.telemetry-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1e293b;font-size:12px}
.telemetry-row:last-child{border-bottom:none}
.telemetry-label{color:var(--text-muted)}
.telemetry-value{font-weight:600;color:#f1f5f9}
.wifi-tag{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;background:#1e293b;border:1px solid #334155;border-radius:20px;font-size:12px;cursor:pointer;transition:all 0.2s;color:#f1f5f9;user-select:none}
.wifi-tag:hover{background:#3b82f6;border-color:#60a5fa;transform:translateY(-1px);box-shadow:0 4px 12px rgba(59,130,246,0.3)}
.wifi-tag b{font-weight:600}
.wifi-tag small{color:#94a3b8;font-size:11px}
.wifi-tag:hover small{color:#e0e7ff}
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
        <span>Desktop Web Dashboard (ESP32-S3 & ESP8266)</span>
      </div>
    </div>
    <div class="badges">
      <div class="badge" id="b-online"><div class="pulse"></div>ONLINE (COM8)</div>
      <div class="badge" id="b-ch">KÊNH: --</div>
      <div class="badge" id="b-ip">IP: 192.168.4.1</div>
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
        • <b>TỰ ĐỘNG</b>: Cảm biến radar tự bật khi ngồi vào, tự tắt khi rời bàn.<br>
        • <b>BẬT/TẮT</b>: Ép đèn giữ trạng thái cố định.
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
      </div>
    </div>

    <!-- Card 3: Cấu hình phần cứng -->
    <div class="card">
      <div class="card-title">⚙️ CẤU HÌNH PHẦN CỨNG & HIỆU CHỈNH</div>
      <div style="display:flex;gap:10px;margin-bottom:10px">
        <button class="btn-secondary" style="flex:1" onclick="sendCmd('p')">🔄 Đảo Cực Relay (Jumper L/H)</button>
        <button class="btn-secondary" style="flex:1" onclick="sendCmd('r')">🔄 Đảo Cực Radar (D2)</button>
      </div>
      <button class="btn-secondary" style="width:100%" onclick="sendCmd('s')">📊 Yêu Cầu Chẩn Đoán Chi Tiết</button>
    </div>

    <!-- Card 4: ESP-NOW -->
    <div class="card">
      <div class="card-title">📡 KẾT NỐI ESP-NOW & ESP32-S3</div>
      <div class="telemetry-row">
        <span class="telemetry-label">Kênh sóng ESP-NOW (Channel)</span>
        <span class="telemetry-value" id="val-ch">Kênh --</span>
      </div>
      <div class="telemetry-row">
        <span class="telemetry-label">Trạng thái ESP32-S3 Master</span>
        <span class="telemetry-value" style="color:var(--success)">Sẵn Sàng</span>
      </div>
      <div style="margin-top:14px">
        <button class="btn-primary" onclick="sendCmd('s')">📡 ĐỒNG BỘ TELEMETRY</button>
      </div>
    </div>

    <!-- Card 5: Cấu hình WiFi đồng bộ cho cả 2 ESP (ALL-IN-ONE) -->
    <div class="card" style="grid-column:1 / -1">
      <div class="card-title">📶 ĐỒNG BỘ CẤU HÌNH WIFI CHO CẢ 2 ESP (ALL-IN-ONE WIFI SETUP)</div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:12px">
        Chọn mạng WiFi từ danh sách quét gần đây bên dưới hoặc nhập thủ công — Hệ thống sẽ tự động cấu hình và kết nối đồng thời cả <b>ESP32-S3 Master</b> (qua NVS COM5) và <b>ESP8266 Slave</b> (qua EEPROM COM8).
      </div>

      <!-- Khu vực quét WiFi gần đây -->
      <div style="margin-bottom:14px;padding:14px;background:#0f172a;border:1px solid #334155;border-radius:10px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <span style="font-size:12px;font-weight:700;color:#38bdf8">📶 CÁC MẠNG WIFI GẦN ĐÂY ĐƯỢC TÌM THẤY (BẤM ĐỂ CHỌN NHANH):</span>
          <button class="btn-secondary" style="padding:4px 10px;font-size:11px" onclick="refreshWifiList()">🔄 Quét lại WiFi</button>
        </div>
        <div id="wifi-chips" style="display:flex;flex-wrap:wrap;gap:8px">
          <span style="font-size:12px;color:var(--text-muted)">⏳ Đang quét các mạng WiFi xung quanh...</span>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
        <div>
          <label style="display:block;font-size:12px;color:var(--text-muted);margin-bottom:6px;font-weight:600">Tên WiFi đã chọn (SSID)</label>
          <input type="text" id="dual-ssid" placeholder="Bấm chọn từ danh sách ở trên hoặc tự nhập" style="width:100%;padding:10px 12px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#fff;font-size:13px">
        </div>
        <div>
          <label style="display:block;font-size:12px;color:var(--text-muted);margin-bottom:6px;font-weight:600">Mật khẩu WiFi (Password)</label>
          <input type="password" id="dual-pass" placeholder="Nhập mật khẩu WiFi" style="width:100%;padding:10px 12px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#fff;font-size:13px">
        </div>
      </div>
      <button class="btn-primary" id="btn-sync-wifi" onclick="syncDualWifi()">🚀 ĐỒNG BỘ & CÀI ĐẶT CHO CẢ 2 ESP</button>
      <div id="sync-result" style="margin-top:12px;display:none;padding:12px;border-radius:8px;background:#0f172a;border:1px solid #334155;font-size:13px;line-height:1.6"></div>
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
  var bOnline=document.getElementById('b-online');
  if(bOnline){
    if(d.esp32_connected){
      bOnline.innerHTML='<div class="pulse"></div>ONLINE (COM8)';
    }else{
      bOnline.innerHTML='<div class="pulse" style="background:var(--danger);box-shadow:0 0 8px var(--danger)"></div>MẤT KẾT NỐI';
    }
  }

  document.getElementById('b-ch').innerText='KÊNH: '+d.channel;
  document.getElementById('b-ip').innerText='IP: '+d.ip;
  document.getElementById('val-ch').innerText='Kênh '+d.channel;

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
    .then(d=>updateUI(d))
    .catch(e=>console.error(e));
}

function setMode(m){
  fetch('/api/control?mode='+m,{method:'POST'})
    .then(r=>r.json())
    .then(d=>{showToast('Chuyển chế độ: '+m.toUpperCase());fetchStatus();});
}

function sendCmd(c){
  fetch('/api/cmd?c='+c,{method:'POST'})
    .then(r=>r.json())
    .then(d=>{showToast('Đã gửi lệnh: '+c);fetchStatus();});
}

function selectWifi(ssid){
  document.getElementById('dual-ssid').value = ssid;
  document.getElementById('dual-pass').focus();
  showToast('Đã chọn WiFi: ' + ssid);
}

function refreshWifiList(){
  var box = document.getElementById('wifi-chips');
  box.innerHTML = '<span style="font-size:12px;color:var(--text-muted)">⏳ Đang quét sóng WiFi xung quanh...</span>';
  fetch('/api/wifi/scan')
    .then(r => r.json())
    .then(list => {
      box.innerHTML = '';
      if(!list || list.length === 0){
        box.innerHTML = '<span style="font-size:12px;color:var(--text-muted)">Không tìm thấy mạng WiFi nào. Hãy bấm "Quét lại WiFi".</span>';
        return;
      }
      list.forEach(w => {
        var tag = document.createElement('div');
        tag.className = 'wifi-tag';
        tag.innerHTML = '📶 <b>' + w.ssid + '</b> <small>(' + (w.signal || '--') + ' | Kênh ' + (w.channel || '--') + ')</small>';
        tag.onclick = function(){ selectWifi(w.ssid); };
        box.appendChild(tag);
      });
    })
    .catch(e => {
      box.innerHTML = '<span style="font-size:12px;color:var(--danger)">Lỗi quét WiFi! Bấm "Quét lại" để thử lại.</span>';
    });
}

function syncDualWifi(){
  var s=document.getElementById('dual-ssid').value.trim();
  var p=document.getElementById('dual-pass').value.trim();
  if(!s){showToast('Vui lòng nhập tên WiFi (SSID)!', true);return;}
  var btn=document.getElementById('btn-sync-wifi');
  var resBox=document.getElementById('sync-result');
  btn.disabled=true;
  btn.innerText='⏳ Đang đồng bộ cấu hình sang cả 2 ESP...';
  resBox.style.display='block';
  resBox.innerHTML='⏳ Đang cấu hình ESP8266 (COM8) và nạp NVS cho ESP32-S3 (COM5)...';

  var body='ssid='+encodeURIComponent(s)+'&pass='+encodeURIComponent(p);
  fetch('/api/wifi/dual-sync',{
    method:'POST',
    headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:body
  })
  .then(r=>r.json())
  .then(d=>{
    btn.disabled=false;
    btn.innerText='🚀 ĐỒNG BỘ & CÀI ĐẶT CHO CẢ 2 ESP';
    if(d.success){
      showToast('Đồng bộ WiFi thành công!');
      resBox.innerHTML='<b style="color:var(--success)">✅ ĐỒNG BỘ HOÀN TẤT!</b><br>'+
                       '• <b>ESP8266 (COM8):</b> '+d.esp8266+'<br>'+
                       '• <b>ESP32-S3 (COM5):</b> '+d.esp32+'<br>'+
                       '<small style="color:var(--text-muted)">Cả 2 thiết bị sẽ tự động kết nối và khớp chung kênh WiFi để liên lạc ESP-NOW.</small>';
    }else{
      showToast('Đồng bộ thất bại!', true);
      resBox.innerHTML='<b style="color:var(--danger)">❌ LỖI:</b> '+(d.error||'Không xác định');
    }
  })
  .catch(e=>{
    btn.disabled=false;
    btn.innerText='🚀 ĐỒNG BỘ & CÀI ĐẶT CHO CẢ 2 ESP';
    showToast('Lỗi kết nối máy chủ!', true);
    resBox.innerHTML='<b style="color:var(--danger)">❌ LỖI:</b> Không thể kết nối tới máy chủ Web.';
  });
}

setInterval(fetchStatus, 1000);
fetchStatus();
refreshWifiList();
</script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif url.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(state).encode('utf-8'))
        elif url.path == '/api/wifi/scan':
            nets = scan_all_wifi()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(nets, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        qs = parse_qs(url.query)
        if url.path == '/api/control':
            mode = qs.get('mode', [''])[0]
            if mode == 'on' or mode == '1':
                send_serial('1\n')
                state["mode"] = "MANUAL_ON"
                state["mode_code"] = 2
                state["lamp"] = 1
            elif mode == 'off' or mode == '0':
                send_serial('0\n')
                state["mode"] = "MANUAL_OFF"
                state["mode_code"] = 1
                state["lamp"] = 0
            elif mode == 'auto':
                send_serial('a\n')
                state["mode"] = "AUTO"
                state["mode_code"] = 0
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success":true}')
        elif url.path == '/api/cmd':
            c = qs.get('c', [''])[0]
            if c:
                send_serial(c + '\n')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success":true}')
        elif url.path == '/api/wifi/dual-sync':
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len).decode('utf-8')
            params = parse_qs(post_body)
            ssid = params.get('ssid', [''])[0]
            password = params.get('pass', [''])[0]

            if not ssid:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"success":false,"error":"Missing SSID"}')
                return

            esp8266_msg = ""
            esp32_msg = ""
            success = True

            # 1. Update ESP8266 via Serial (COM8)
            try:
                cmd_w = f"w {ssid} {password}\n"
                if send_serial(cmd_w):
                    esp8266_msg = f"Đã lưu SSID '{ssid}' vào EEPROM và bắt đầu kết nối!"
                else:
                    esp8266_msg = "Không thể gửi qua Serial COM8 (Cổng bận hoặc chưa mở)"
            except Exception as e:
                esp8266_msg = f"Lỗi ESP8266: {str(e)}"

            # 2. Update ESP32-S3 via NVS partition (COM5)
            try:
                scripts_dir = os.path.dirname(os.path.abspath(__file__))
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)
                import set_wifi_config
                target_bin = os.path.join(scripts_dir, "..", "nvs_configured.bin")
                target_bin = os.path.abspath(target_bin)
                set_wifi_config.update_nvs_wifi(target_bin, ssid, password)

                available_ports = [p.device for p in serial.tools.list_ports.comports()]
                if 'COM5' in available_ports:
                    set_wifi_config.flash_nvs(target_bin, port='COM5')
                    esp32_msg = f"Đã nạp NVS WiFi ('{ssid}') vào ESP32-S3 qua cổng COM5 thành công!"
                else:
                    esp32_msg = f"Đã cập nhật file nvs_configured.bin ('{ssid}'), nhưng không tìm thấy cổng COM5 cắm máy."
            except Exception as e:
                esp32_msg = f"Lỗi nạp ESP32-S3: {str(e)}"

            res_payload = {
                "success": success,
                "esp8266": esp8266_msg,
                "esp32": esp32_msg
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res_payload, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_server(port=HTTP_PORT):
    t = threading.Thread(target=serial_worker, daemon=True)
    t.start()

    server = HTTPServer(('0.0.0.0', port), RequestHandler)
    print(f"\n=======================================================")
    print(f" [WEB DASHBOARD] Started at: http://localhost:{port}")
    print(f" Connecting to ESP on {SERIAL_PORT} (DTR=False, RTS=False)...")
    print(f" Nearby WiFi Scanner & Dual Sync is active!")
    print(f"=======================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        with ser_lock:
            if ser and ser.is_open:
                ser.close()

if __name__ == '__main__':
    p = int(sys.argv[1]) if len(sys.argv) > 1 else HTTP_PORT
    run_server(p)
