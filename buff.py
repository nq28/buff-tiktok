#!/usr/bin/env python3
# BuffK$ - TikTok View & Share Tool (1:1 Exact Match with BuffK$.exe)
# Hoạt động 100% bằng thư viện chuẩn của Python, chạy được trên mọi máy Android/Termux/PC

import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request

DEVICES = [
    {"brand": "Google", "model": "Pixel 8 Pro", "os": "14"},
    {"brand": "Google", "model": "Pixel 7", "os": "13"},
    {"brand": "Samsung", "model": "SM-G998B", "os": "13"},
    {"brand": "Samsung", "model": "SM-S918B", "os": "14"},
    {"brand": "OnePlus", "model": "OnePlus 12", "os": "14"},
    {"brand": "OnePlus", "model": "OnePlus 11", "os": "13"},
    {"brand": "Xiaomi", "model": "POCO F6", "os": "14"},
    {"brand": "Xiaomi", "model": "POCO F5", "os": "13"},
    {"brand": "OPPO", "model": "OPPO Reno 8", "os": "13"},
    {"brand": "Nothing", "model": "Nothing Phone (2)", "os": "14"},
]

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    print("""
    kenh4x self leak
""")

def resolve_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()
    if url_or_id.isdigit():
        return url_or_id
    
    if "tiktok.com" in url_or_id and not re.search(r"/video/(\d+)", url_or_id):
        try:
            req = urllib.request.Request(
                url_or_id,
                headers={"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                url_or_id = resp.geturl()
        except Exception:
            pass

    match = re.search(r"/video/(\d+)", url_or_id)
    if match:
        return match.group(1)
    
    match_num = re.search(r"(\d{15,22})", url_or_id)
    if match_num:
        return match_num.group(1)
        
    return url_or_id

def send_request(item_id: str, is_share: bool = False) -> bool:
    dev = random.choice(DEVICES)
    device_id = str(random.randint(7000000000000000000, 7999999999999999999))
    iid = str(random.randint(7000000000000000000, 7999999999999999999))
    
    delta_param = "share_delta" if is_share else "play_delta"
    
    params = {
        "item_id": item_id,
        delta_param: "1",
        "aweme_type": "0",
        "action_time": str(int(time.time())),
        "device_id": device_id,
        "iid": iid,
        "device_type": dev["model"],
        "device_brand": dev["brand"],
        "os_version": dev["os"],
        "channel": "googleplay",
        "app_name": "musical_ly",
        "version_code": "340502",
        "aid": "1233",
    }
    
    # Máy chủ chính xác của BuffK$.exe
    url = f"https://api19.tiktokv.com/aweme/v1/aweme/stats/?{urllib.parse.urlencode(params)}"
    
    req = urllib.request.Request(
        url,
        data=b"",
        headers={
            "User-Agent": f"com.zhiliaoapp.musically/340502 (Linux; U; Android {dev['os']}; vi_VN; {dev['model']})",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "X-SS-REQ-TICKET": str(int(time.time() * 1000)),
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def run_worker(item_id: str, target: int, is_share: bool = False):
    label = "shares" if is_share else "views"
    print(f"\n  [*] sending {target} {label}")
    
    completed = 0
    start_time = time.time()
    
    while completed < target:
        ok = send_request(item_id, is_share)
        if ok:
            completed += 1
            
        elapsed = time.time() - start_time
        rate = int(completed / elapsed) if elapsed > 0 else 0
        pct = int((completed / target) * 100) if target > 0 else 0
        
        sys.stdout.write(f"\r  {label}: {completed}/{target} ({pct}%)  rate: {rate}/s    ")
        sys.stdout.flush()
        
        # Nhịp độ tự nhiên giống BuffK$.exe để TikTok không chặn rate-limit
        time.sleep(random.uniform(0.7, 1.2))

    print(f"\n\n  [✓] Hoàn thành {completed}/{target} {label}!\n")

def main():
    while True:
        clear_screen()
        banner()
        print("  [1] TikTok Viewer")
        print("  [2] TikTok Sharer")
        print("  [3] Exit\n")
        
        choice = input("  [?] select: ").strip()
        if choice == "3" or choice.lower() == "exit":
            print("\n  Goodbye!")
            break
            
        if choice not in ["1", "2"]:
            continue
            
        is_share = (choice == "2")
        
        clear_screen()
        banner()
        url_input = input("  [?] url/id: ").strip()
        if not url_input:
            continue
            
        item_id = resolve_id(url_input)
        
        views_str = input("  [?] views: ").strip()
        try:
            target = int(views_str) if views_str else 100
        except ValueError:
            target = 100
            
        run_worker(item_id, target, is_share=is_share)
        input("  Nhấn Enter để quay lại menu...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  [!] Exiting...")
