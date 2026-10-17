# File: buff.py
# Tool Buff TikTok View Chạy Trực Tiếp Trên Điện Thoại Android / Ugphone (Qua Termux)
# Kết nối mạng 4G trực tiếp từ SIM để đạt tốc độ cao và vượt bộ lọc IP

import asyncio
import json
import os
import random
import re
import sys
import time
from typing import Optional, Dict, Any
import httpx
from colorama import Fore, Style, init

init(autoreset=True)

DEVICES = [
    {"brand": "samsung", "model": "SM-G998B", "os": "13"},
    {"brand": "samsung", "model": "SM-F926B", "os": "12"},
    {"brand": "google", "model": "Pixel 7", "os": "13"},
    {"brand": "google", "model": "Pixel 8", "os": "14"},
    {"brand": "xiaomi", "model": "POCO F5", "os": "13"},
    {"brand": "xiaomi", "model": "POCO F6", "os": "14"},
]

def resolve_video_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()
    if url_or_id.isdigit():
        return url_or_id
    
    if "tiktok.com" in url_or_id and not re.search(r"/video/(\d+)", url_or_id):
        print(Fore.BLUE + "[*] Đang phân giải link rút gọn...")
        try:
            with httpx.Client(follow_redirects=True, timeout=10.0) as client:
                headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
                resp = client.get(url_or_id, headers=headers)
                url_or_id = str(resp.url)
        except Exception:
            pass

    match = re.search(r"/video/(\d+)", url_or_id)
    if match:
        return match.group(1)
    
    match_num = re.search(r"(\d{15,22})", url_or_id)
    if match_num:
        return match_num.group(1)
        
    return url_or_id

def fetch_stats(item_id: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://www.tiktok.com/@a/video/{item_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>({.*?})<\/script>', resp.text)
                if match:
                    data = json.loads(match.group(1))
                    return data['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']['stats']
    except Exception:
        pass
    return None

def print_banner():
    print(Fore.CYAN + "=" * 48)
    print(Fore.GREEN + Style.BRIGHT + "   TIKTOK VIEW MOBILE (TERMUX / UGPHONE 4G)")
    print(Fore.CYAN + "=" * 48)
    print(Fore.YELLOW + " • Nền tảng : Android / Ugphone / Termux")
    print(Fore.YELLOW + " • Kết nối  : 4G SIM trực tiếp (Tốc độ tối đa)")
    print(Fore.YELLOW + " • Đổi IP   : Bật/Tắt Chế độ máy bay (Airplane)")
    print(Fore.CYAN + "-" * 48)

async def send_view_request(client: httpx.AsyncClient, item_id: str, view_idx: int) -> bool:
    dev = random.choice(DEVICES)
    device_id = str(random.randint(7000000000000000000, 7999999999999999999))
    install_id = str(random.randint(7000000000000000000, 7999999999999999999))
    
    url = "https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/aweme/stats/"
    params = {
        "item_id": item_id,
        "play_delta": "1",
        "action_time": str(int(time.time())),
        "device_id": device_id,
        "iid": install_id,
        "device_type": dev["model"],
        "device_brand": dev["brand"],
        "os_version": dev["os"],
        "channel": "googleplay",
        "app_name": "musical_ly",
        "version_code": "340502",
        "aid": "1233",
    }
    
    headers = {
        "User-Agent": f"com.zhiliaoapp.musically/340502 (Linux; U; Android {dev['os']}; vi_VN; {dev['model']})",
        "Accept-Encoding": "gzip, deflate",
        "X-SS-REQ-TICKET": str(int(time.time() * 1000)),
    }
    
    try:
        resp = await client.post(url, params=params, headers=headers, timeout=6.0)
        return resp.status_code == 200
    except Exception:
        return False

async def main():
    print_banner()
    
    video_input = input(Fore.GREEN + "[?] Nhập Link video hoặc Video ID: ").strip()
    if not video_input:
        print(Fore.RED + "[!] Lỗi: Chưa nhập link!")
        return
        
    item_id = resolve_video_id(video_input)
    print(Fore.MAGENTA + Style.BRIGHT + f"  [✓] ID Video: {item_id}\n")
    
    amount_str = input(Fore.GREEN + "[?] Số lượt xem muốn buff (Mặc định 100): ").strip()
    try:
        target = int(amount_str) if amount_str else 100
    except ValueError:
        target = 100
        
    batch_str = input(Fore.GREEN + "[?] Số view mỗi đợt đổi 4G (Khuyên dùng 50): ").strip()
    try:
        batch_size = int(batch_str) if batch_str else 50
    except ValueError:
        batch_size = 50

    print(Fore.CYAN + "\n[*] Kiểm tra số liệu ban đầu...")
    stats = fetch_stats(item_id)
    if stats:
        print(Fore.CYAN + f"  ▶ Lượt xem hiện tại: {stats.get('playCount', 0):,}")
    
    print(Fore.GREEN + Style.BRIGHT + f"\n🚀 Bắt đầu gửi {target} views qua 4G...")
    
    total_sent = 0
    t0 = time.time()
    
    async with httpx.AsyncClient(http2=True, verify=False) as client:
        while total_sent < target:
            current_batch = min(batch_size, target - total_sent)
            tasks = []
            for _ in range(current_batch):
                total_sent += 1
                tasks.append(send_view_request(client, item_id, total_sent))
                
            results = await asyncio.gather(*tasks)
            success_count = sum(1 for r in results if r)
            print(Fore.GREEN + f"  [✓] Đã gửi đợt {total_sent}/{target} views ({success_count}/{current_batch} thành công)")
            
            if total_sent < target:
                print(Fore.YELLOW + "\n👉 MẸO: Vuốt thanh thông báo BẬT rồi TẮT Chế độ máy bay (Airplane) để đổi IP 4G mới.")
                choice = input(Fore.GREEN + "[?] Nhấn Enter để chạy đợt tiếp theo (hoặc gõ 'q' để dừng): ").strip()
                if choice.lower() == 'q':
                    break

    dur = time.time() - t0
    print(Fore.CYAN + "\n" + "=" * 48)
    print(Fore.GREEN + Style.BRIGHT + f"🎉 Hoàn tất! Đã gửi: {total_sent} views trong {dur:.1f}s")
    print(Fore.CYAN + "=" * 48)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Đã dừng chương trình.")
