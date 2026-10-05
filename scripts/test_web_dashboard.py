"""
Unit and Integration Test for Web Dashboard & ESP API
Verifies HTTP endpoints, JSON structure, control commands, and all-in-one dual WiFi sync.
"""

import sys
import time
import json
import threading
import urllib.request
import urllib.error
from urllib.parse import urlencode

# Import web_dashboard components
import web_dashboard

def run_tests():
    print("==================================================")
    print(" STARTING WEB DASHBOARD & API INTEGRATION TESTS")
    print("==================================================")
    
    # 1. Start Web Server on test port 8888
    TEST_PORT = 8888
    web_dashboard.HTTP_PORT = TEST_PORT
    
    server_thread = threading.Thread(target=web_dashboard.run_server, args=(TEST_PORT,), daemon=True)
    server_thread.start()
    time.sleep(1) # Allow server to bind
    
    base_url = f"http://127.0.0.1:{TEST_PORT}"
    
    # Test 1: GET / (HTML Page)
    print("\n--> [TEST 1] Testing GET / (HTML Dashboard)...")
    req = urllib.request.Request(f"{base_url}/")
    with urllib.request.urlopen(req, timeout=3) as res:
        assert res.status == 200, f"Expected 200, got {res.status}"
        html = res.read().decode('utf-8')
        assert "SMART DESK ASSISTANT" in html, "Page title/header missing"
        assert "ĐIỀU KHIỂN ĐÈN BÀN" in html, "Lamp control card missing"
        assert "CÔNG THÁI HỌC" in html, "Ergonomics card missing"
        assert "ĐỒNG BỘ CẤU HÌNH WIFI CHO CẢ 2 ESP" in html, "Dual WiFi sync card missing"
    print("[PASSED] HTML Dashboard successfully served with 200 OK!")
    
    # Test 2: GET /api/status (JSON Telemetry)
    print("\n--> [TEST 2] Testing GET /api/status (Telemetry JSON)...")
    req = urllib.request.Request(f"{base_url}/api/status")
    with urllib.request.urlopen(req, timeout=3) as res:
        assert res.status == 200, f"Expected 200, got {res.status}"
        data = json.loads(res.read().decode('utf-8'))
        required_keys = ["mode", "lamp", "sitting", "sitting_time", "channel", "ip"]
        for k in required_keys:
            assert k in data, f"Missing key in JSON: {k}"
        print(f"[STATUS RECV] Mode={data['mode']}, Lamp={data['lamp']}, Sitting={data['sitting']}, Channel={data['channel']}")
    print("[PASSED] /api/status returns valid schema and real-time state!")
    
    # Test 3: POST /api/control?mode=on
    print("\n--> [TEST 3] Testing POST /api/control?mode=on...")
    req = urllib.request.Request(f"{base_url}/api/control?mode=on", data=b'', method='POST')
    with urllib.request.urlopen(req, timeout=3) as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        assert data.get("success") is True
    assert web_dashboard.state["mode"] == "MANUAL_ON"
    assert web_dashboard.state["lamp"] == 1
    print("[PASSED] Manual ON mode command accepted and state updated!")
    
    # Test 4: POST /api/control?mode=off
    print("\n--> [TEST 4] Testing POST /api/control?mode=off...")
    req = urllib.request.Request(f"{base_url}/api/control?mode=off", data=b'', method='POST')
    with urllib.request.urlopen(req, timeout=3) as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        assert data.get("success") is True
    assert web_dashboard.state["mode"] == "MANUAL_OFF"
    assert web_dashboard.state["lamp"] == 0
    print("[PASSED] Manual OFF mode command accepted and state updated!")
    
    # Test 5: POST /api/control?mode=auto
    print("\n--> [TEST 5] Testing POST /api/control?mode=auto...")
    req = urllib.request.Request(f"{base_url}/api/control?mode=auto", data=b'', method='POST')
    with urllib.request.urlopen(req, timeout=3) as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        assert data.get("success") is True
    assert web_dashboard.state["mode"] == "AUTO"
    print("[PASSED] AUTO mode command accepted and state restored!")
    
    # Test 6: POST /api/cmd?c=s (Diagnostics Command)
    print("\n--> [TEST 6] Testing POST /api/cmd?c=s...")
    req = urllib.request.Request(f"{base_url}/api/cmd?c=s", data=b'', method='POST')
    with urllib.request.urlopen(req, timeout=3) as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        assert data.get("success") is True
    print("[PASSED] Hardware serial command forwarding verified!")
    
    # Test 7: POST /api/wifi/dual-sync
    print("\n--> [TEST 7] Testing POST /api/wifi/dual-sync (All-in-One Dual WiFi)...")
    payload = urlencode({'ssid': 'MyDesk_WiFi', 'pass': '123456789'}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/api/wifi/dual-sync", data=payload, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        assert data.get("success") is True
        assert "esp8266" in data
        assert "esp32" in data
        print(f"[DUAL-SYNC RECV] ESP8266: {data['esp8266'].encode('ascii', 'replace').decode('ascii')}")
        print(f"[DUAL-SYNC RECV] ESP32: {data['esp32'].encode('ascii', 'replace').decode('ascii')}")
    print("[PASSED] Dual WiFi synchronization endpoint executed successfully!")
    
    print("\n==================================================")
    print(" ALL WEB DASHBOARD TESTS COMPLETED SUCCESSFULLY!")
    print("==================================================")
    return True

if __name__ == '__main__':
    ok = run_tests()
    sys.exit(0 if ok else 1)
