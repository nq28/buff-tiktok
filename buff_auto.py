# File: buff_auto.py
# Tool Buff TikTok Siêu Tốc (TURBO) + Tự Động Xoay ProxyXoay Dân Cư + Kiểm Tra Stats Live

import asyncio
import json
import random
import re
import sys
import time
from typing import Optional, Dict, Any
import httpx
from colorama import Fore, Style, init

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

init(autoreset=True)

DEFAULT_API_KEY = "d5df6276-0e55-4961-8c2f-6b4fa70a13cc"
DEFAULT_PROXY = "http://hndc2.proxyxoay.net:55064"

DEVICES = [
    {"brand": "samsung", "model": "SM-G998B", "dpi": "560", "res": "1440x3200", "os": "13"},
    {"brand": "samsung", "model": "SM-F926B", "dpi": "480", "res": "1080x2400", "os": "12"},
    {"brand": "samsung", "model": "SM-G991B", "dpi": "480", "res": "1080x2400", "os": "13"},
    {"brand": "google", "model": "Pixel 7", "dpi": "420", "res": "1080x2400", "os": "13"},
    {"brand": "google", "model": "Pixel 8", "dpi": "420", "res": "1080x2400", "os": "14"},
    {"brand": "xiaomi", "model": "POCO F5", "dpi": "440", "res": "1080x2400", "os": "13"},
    {"brand": "xiaomi", "model": "POCO F6", "dpi": "440", "res": "1220x2712", "os": "14"},
    {"brand": "oneplus", "model": "OnePlus 11", "dpi": "525", "res": "1440x3216", "os": "13"},
    {"brand": "oneplus", "model": "OnePlus 12", "dpi": "510", "res": "1440x3168", "os": "14"},
]

def resolve_video_id(url_or_id: str) -> str:
    """Tự động phân giải link rút gọn (vt.tiktok.com / vm.tiktok.com) sang ID số"""
    url_or_id = url_or_id.strip()
    if url_or_id.isdigit():
        return url_or_id
    
    if "tiktok.com" in url_or_id and not re.search(r"/video/(\d+)", url_or_id):
        print(Fore.BLUE + f"[*] Đang phân giải link TikTok: {url_or_id} ...")
        try:
            with httpx.Client(follow_redirects=True, timeout=10.0) as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp = client.get(url_or_id, headers=headers)
                url_or_id = str(resp.url)
                print(Fore.GREEN + f"  [✓] Link gốc: {url_or_id}")
        except Exception:
            pass

    match = re.search(r"/video/(\d+)", url_or_id)
    if match:
        return match.group(1)
    
    match_num = re.search(r"(\d{15,22})", url_or_id)
    if match_num:
        return match_num.group(1)
        
    return url_or_id

def generate_device_payload():
    dev = random.choice(DEVICES)
    device_id = str(random.randint(7000000000000000000, 7999999999999999999))
    install_id = str(random.randint(7000000000000000000, 7999999999999999999))
    openudid = "".join(random.choices("0123456789abcdef", k=16))
    cdid = f"{openudid[:8]}-{openudid[8:12]}-4{openudid[12:15]}-a{openudid[15:]}-{openudid[:12]}"
    ua = f"com.zhiliaoapp.musically/2022300804 (Linux; U; Android {dev['os']}; vi_VN; {dev['model']}; Build/TQ3A.230805.001; Cronet/58.0.2991.0)"
    return {
        "device_id": device_id,
        "iid": install_id,
        "openudid": openudid,
        "cdid": cdid,
        "brand": dev["brand"],
        "model": dev["model"],
        "os": dev["os"],
        "ua": ua
    }

async def fetch_video_stats(item_id: str) -> Optional[Dict[str, Any]]:
    """Lấy số view, like, comment, share chính xác từ TikTok qua Playwright"""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            url = f"https://www.tiktok.com/@a/video/{item_id}"
            await page.goto(url, wait_until="domcontentloaded", timeout=12000)
            stats = await page.evaluate("""() => {
                try {
                    const el = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
                    if (el) {
                        const data = JSON.parse(el.innerText);
                        return data['__DEFAULT_SCOPE__']['webapp.video-detail'].itemInfo.itemStruct.stats;
                    }
                } catch(e) {}
                return null;
            }""")
            await browser.close()
            return stats
    except Exception:
        return None

def print_stats_box(title: str, stats: Optional[Dict[str, Any]], color=Fore.CYAN):
    print(color + "┌" + "─" * 62 + "┐")
    print(color + f"│ {title:<60} │")
    print(color + "├" + "─" * 62 + "┤")
    if stats:
        play = f"{int(stats.get('playCount', 0)):,}"
        digg = f"{int(stats.get('diggCount', 0)):,}"
        share = f"{int(stats.get('shareCount', 0)):,}"
        comment = f"{int(stats.get('commentCount', 0)):,}"
        print(color + f"│  ▶ Lượt xem (Views)    : {play:<37} │")
        print(color + f"│  ♥ Lượt thích (Likes)  : {digg:<37} │")
        print(color + f"│  💬 Bình luận (Comments): {comment:<37} │")
        print(color + f"│  ↗ Chia sẻ (Shares)    : {share:<37} │")
    else:
        print(color + f"│  (Không lấy được dữ liệu chi tiết từ TikTok)               │")
    print(color + "└" + "─" * 62 + "┘")

async def get_current_proxy_ip(proxy: str) -> str:
    """Kiểm tra IP hiện tại của proxy"""
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=5.0) as client:
            resp = await client.get("http://api.ipify.org?format=json")
            if resp.status_code == 200:
                return resp.json().get("ip", "Chưa xác định")
    except Exception:
        pass
    return "Không kết nối được"

async def rotate_proxy_ip(api_key: str, proxy: str, old_ip: str = "") -> str:
    """Gọi API ProxyXoay để đổi IP, đếm ngược cooldown nếu có, và đợi IP mới hoạt động"""
    print(Fore.YELLOW + "\n" + "=" * 64)
    print(Fore.YELLOW + "  🔄 ĐÃ HOÀN THÀNH HẠN MỨC CỦA IP HIỆN TẠI. ĐANG TIẾN HÀNH ĐỔI IP...")
    print(Fore.YELLOW + "=" * 64)

    change_url = f"https://proxyxoay.net/api/rotating-proxy/change-key-ip/{api_key}"
    
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(change_url)
                data = resp.json()
        except Exception as e:
            print(Fore.RED + f"  [!] Lỗi kết nối API ProxyXoay: {e}. Thử lại sau 5s...")
            await asyncio.sleep(5)
            continue

        status = data.get("status")
        msg = data.get("message", "")

        # Nếu đổi thành công
        if status == 200:
            print(Fore.GREEN + Style.BRIGHT + "  [✓] Lệnh đổi IP đã được gửi thành công đến ProxyXoay!")
            break

        # Nếu còn vướng cooldown (Status 500: Đợi X giây...)
        m = re.search(r"(\d+)\s*gi[aâ]y", msg, re.IGNORECASE)
        cooldown = int(m.group(1)) if m else 15
        
        print(Fore.CYAN + f"  [⏳] Cooldown xoay IP: Cần chờ {cooldown}s trước lần đổi tiếp theo.")
        for remaining in range(cooldown, 0, -1):
            sys.stdout.write(f"\r{Fore.YELLOW}  [⏳] Đang chờ cooldown đổi IP: còn {remaining:3d}s...{Style.RESET_ALL}")
            sys.stdout.flush()
            await asyncio.sleep(1)
        sys.stdout.write("\r" + " " * 65 + "\r")
        sys.stdout.flush()

    # Sau khi gửi lệnh đổi IP, chờ modem ProxyXoay khởi động lại và kết nối WAN mới
    print(Fore.CYAN + "  [*] Đang chờ ProxyXoay cấp phát IP WAN mới (thường mất 15-25s)...")
    t0 = time.time()
    new_ip = ""
    while time.time() - t0 < 60:
        await asyncio.sleep(3)
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=5.0) as client:
                r = await client.get("http://api.ipify.org?format=json")
                if r.status_code == 200:
                    cand_ip = r.json().get("ip", "")
                    if cand_ip:
                        new_ip = cand_ip
                        break
        except Exception:
            pass

    if new_ip:
        print(Fore.GREEN + Style.BRIGHT + f"  [✓] IP MỚI ĐÃ SẴN SÀNG: {new_ip} (Đổi từ {old_ip})\n")
    else:
        print(Fore.YELLOW + "  [!] Proxy đã phản hồi nhưng chưa đọc được IP mới, tiếp tục đợt mới.\n")
    
    return new_ip or old_ip

async def send_single_view(client: httpx.AsyncClient, sem: asyncio.Semaphore, item_id: str, action: str = "view") -> bool:
    async with sem:
        dev = generate_device_payload()
        delta_param = "play_delta=1" if action == "view" else "share_delta=1"
        url = (
            f"https://api19.tiktokv.com/aweme/v1/aweme/stats/?"
            f"item_id={item_id}&"
            f"{delta_param}&"
            f"device_id={dev['device_id']}&"
            f"iid={dev['iid']}&"
            f"openudid={dev['openudid']}&"
            f"cdid={dev['cdid']}&"
            f"aid=1233&"
            f"channel=googleplay&"
            f"device_platform=android&"
            f"device_type={dev['model']}&"
            f"device_brand={dev['brand']}&"
            f"os_version={dev['os']}&"
            f"version_code=300804&"
            f"app_name=musical_ly&"
            f"app_language=vi&"
            f"carrier_region=VN&"
            f"sys_region=VN&"
            f"timezone_name=Asia%2FHo_Chi_Minh&"
            f"timezone_offset=25200"
        )
        headers = {
            "User-Agent": dev["ua"],
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            resp = await client.post(url, headers=headers, timeout=6.0)
            return resp.status_code == 200
        except Exception:
            return False

def print_banner():
    print(Fore.CYAN + "=" * 68)
    print(Fore.GREEN + Style.BRIGHT + "   BUFF TIKTOK SIÊU TỐC - TỰ ĐỘNG XOAY PROXY THEO MỨC MAX/IP")
    print(Fore.CYAN + "=" * 68)
    print(Fore.YELLOW + f"  • Proxy mặc định : {DEFAULT_PROXY}")
    print(Fore.YELLOW + f"  • Cơ chế         : Buff tối đa view trên 1 IP ➔ Tự xoay ➔ Bắn tiếp")
    print(Fore.YELLOW + f"  • Tốc độ         : 50 - 70 view/giây | Tự động kiểm tra Stats Live")
    print(Fore.CYAN + "-" * 68)

async def main():
    print_banner()

    # 1. Chọn chế độ mạng
    print(Fore.WHITE + "Chọn phương thức mạng:")
    print(Fore.GREEN + Style.BRIGHT + "  [1] Chạy TRỰC TIẾP (Mạng 4G phát từ điện thoại / WiFi nhà - SIÊU TỐC KHUYÊN DÙNG)")
    print(Fore.YELLOW + "  [2] Chạy qua PROXY XOAY (hndc2.proxyxoay.net:55064)")
    net_choice = input(Fore.GREEN + "[?] Lựa chọn phương thức mạng (1 hoặc 2, mặc định 1): ").strip()
    use_proxy = (net_choice == "2")

    # 2. Chọn loại buff
    print(Fore.WHITE + "\nChọn loại buff:")
    print("  [1] Tăng Lượt Xem (TikTok Views - Khuyên dùng)")
    print("  [2] Tăng Lượt Chia Sẻ (TikTok Shares)")
    choice = input(Fore.GREEN + "[?] Lựa chọn (1 hoặc 2, mặc định 1): ").strip()
    action = "share" if choice == "2" else "view"
    action_name = "lượt share" if action == "share" else "lượt view"

    # 3. Nhập link video
    video_input = input(Fore.GREEN + "\n[?] Nhập Link video hoặc Video ID: ").strip()
    if not video_input:
        print(Fore.RED + "[!] Lỗi: Bạn chưa nhập link video!")
        return
    item_id = resolve_video_id(video_input)
    print(Fore.MAGENTA + Style.BRIGHT + f"  [✓] ID Video TikTok: {item_id}\n")

    # 4. Nhập tổng số view muốn buff
    amount_str = input(Fore.GREEN + f"[?] Tổng số {action_name} cần buff (Ví dụ: 1000, 3000, 10000): ").strip()
    try:
        total_target = int(amount_str) if amount_str else 1000
    except ValueError:
        total_target = 1000

    # 5. Cấu hình chi tiết theo chế độ mạng
    if use_proxy:
        max_ip_str = input(Fore.GREEN + f"[?] Số {action_name} tối đa trên 1 IP trước khi đổi (Khuyên dùng: 200-500, mặc định 300): ").strip()
        try:
            max_views_per_ip = int(max_ip_str) if max_ip_str else 300
        except ValueError:
            max_views_per_ip = 300

        proxy_input = input(Fore.GREEN + f"[?] Proxy (Nhấn Enter dùng {DEFAULT_PROXY}): ").strip()
        proxy = proxy_input if proxy_input else DEFAULT_PROXY
        if not proxy.startswith("http://") and not proxy.startswith("https://"):
            proxy = "http://" + proxy

        key_input = input(Fore.GREEN + f"[?] API Key ProxyXoay (Nhấn Enter dùng key mặc định): ").strip()
        api_key = key_input if key_input else DEFAULT_API_KEY
    else:
        proxy = None
        max_views_per_ip = total_target
        api_key = None

    # 6. Kiểm tra chỉ số ban đầu của video
    print(Fore.CYAN + "\n[*] Đang truy vấn số liệu hiện tại của video trên TikTok...")
    initial_stats = await fetch_video_stats(item_id)
    print_stats_box("THỐNG KÊ VIDEO BAN ĐẦU", initial_stats, Fore.CYAN)

    # 7. Kiểm tra IP ban đầu
    if use_proxy:
        current_ip = await get_current_proxy_ip(proxy)
        print(Fore.GREEN + f"[*] IP Proxy hiện tại: {Style.BRIGHT}{current_ip}\n")
    else:
        try:
            async with httpx.AsyncClient(timeout=4.0) as cl:
                r_ip = await cl.get("http://api.ipify.org?format=json")
                current_ip = r_ip.json().get("ip", "4G/Direct")
        except Exception:
            current_ip = "4G/Direct"
        print(Fore.GREEN + f"[*] IP Mạng máy (4G/WiFi): {Style.BRIGHT}{current_ip}\n")

    # 8. Bắt đầu vòng lặp bắn theo IP
    total_sent = 0
    batch_index = 1
    start_total_time = time.time()
    sem = asyncio.Semaphore(35)
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=35)

    while total_sent < total_target:
        # Số lượng cần gửi cho IP hiện tại
        views_this_ip = min(max_views_per_ip, total_target - total_sent)
        print(Fore.CYAN + f"► ĐỢT #{batch_index} | IP: {current_ip} | Mục tiêu IP này: {views_this_ip:,} {action_name}")
        
        t_batch_start = time.time()
        sent_this_ip = 0
        chunk_step = 100  # Chia nhỏ mỗi lần bắn 100 view để hiển thị tiến độ mượt

        async with httpx.AsyncClient(proxy=proxy, limits=limits, timeout=8.0) as client:
            while sent_this_ip < views_this_ip:
                current_chunk = min(chunk_step, views_this_ip - sent_this_ip)
                t0 = time.time()
                tasks = [send_single_view(client, sem, item_id, action) for _ in range(current_chunk)]
                results = await asyncio.gather(*tasks)
                success = sum(1 for r in results if r)
                
                sent_this_ip += success
                total_sent += success
                dur = time.time() - t0
                spd = success / dur if dur > 0 else 0
                
                pct = (total_sent / total_target) * 100
                print(Fore.GREEN + f"   [+] Tiến độ tổng: {total_sent:,} / {total_target:,} ({pct:.1f}%) | Đợt này: {sent_this_ip}/{views_this_ip} | Tốc độ: {spd:.0f} view/s")
                
                if total_sent >= total_target:
                    break
                await asyncio.sleep(0.3)

        dur_batch = time.time() - t_batch_start
        print(Fore.GREEN + Style.BRIGHT + f"  [✓] Hoàn thành đợt #{batch_index}: Đã bắn {sent_this_ip:,} view qua IP {current_ip} trong {dur_batch:.1f}s")

        # Kiểm tra stats cập nhật sau mỗi đợt
        print(Fore.CYAN + "  [*] Đang kiểm tra thống kê video cập nhật...")
        new_stats = await fetch_video_stats(item_id)
        if new_stats:
            old_play = int(initial_stats.get('playCount', 0)) if initial_stats else 0
            curr_play = int(new_stats.get('playCount', 0))
            delta = curr_play - old_play
            delta_str = f"+{delta:,}" if delta >= 0 else f"{delta:,}"
            print_stats_box(f"CẬP NHẬT THỐNG KÊ (Đợt #{batch_index} - Tăng {delta_str} view)", new_stats, Fore.MAGENTA)
        
        if total_sent >= total_target:
            break

        # Tự động xoay sang IP mới cho đợt tiếp theo nếu dùng proxy
        if use_proxy:
            current_ip = await rotate_proxy_ip(api_key, proxy, old_ip=current_ip)
            batch_index += 1
        else:
            break

    # Tổng kết
    total_elapsed = time.time() - start_total_time
    print(Fore.GREEN + Style.BRIGHT + "\n" + "=" * 68)
    print(f"🎉 HOÀN THÀNH TOÀN BỘ CHIẾN DỊCH!")
    print(f"  • Tổng số {action_name} đã bắn: {total_sent:,} lượt")
    print(f"  • Tổng thời gian           : {total_elapsed / 60:.1f} phút ({total_elapsed:.0f} giây)")
    print(f"  • Số IP đã sử dụng        : {batch_index} địa chỉ IP khác nhau")
    
    final_stats = await fetch_video_stats(item_id)
    print_stats_box("THỐNG KÊ VIDEO CUỐI CÙNG", final_stats, Fore.GREEN)

    print(Fore.YELLOW + "👉 LƯU Ý QUAN TRỌNG:")
    print("   1. Hãy tắt app TikTok trên điện thoại và mở lại để xóa cache.")
    print("   2. Máy chủ CDN của TikTok sẽ đồng bộ số view đầy đủ trong vòng 1-5 phút.")
    print(Fore.GREEN + Style.BRIGHT + "=" * 68 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Đã dừng chương trình theo yêu cầu của bạn.")
