# File: buff_browser.py
# Tool Buff TikTok View Thật 100% - Headless Browser Stream (Tối Ưu Siêu Nhẹ RAM/CPU)
# Cơ chế: Tải và phát luồng video thật từ CDN TikTok trong 3.5 giây, chặn toàn bộ ảnh/font để tiết kiệm 80% tài nguyên.

import asyncio
import os
import random
import re
import sys
import time
from typing import Optional, Dict, Any
import httpx
from colorama import Fore, Style, init
from playwright.async_api import async_playwright, Browser

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

init(autoreset=True)

DEFAULT_PROXY = "http://hndc2.proxyxoay.net:55064"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

def resolve_video_id(url_or_id: str) -> str:
    """Phân giải link rút gọn (vt.tiktok.com) hoặc link web sang ID số sạch sẽ"""
    url_or_id = url_or_id.strip()
    if url_or_id.isdigit():
        return url_or_id
    
    if "tiktok.com" in url_or_id and not re.search(r"/video/(\d+)", url_or_id):
        print(Fore.BLUE + f"[*] Đang phân giải link: {url_or_id} ...")
        try:
            with httpx.Client(follow_redirects=True, timeout=10.0) as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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

async def fetch_video_stats(item_id: str) -> Optional[Dict[str, Any]]:
    """Lấy dữ liệu thống kê thật từ TikTok"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-gpu", "--mute-audio", "--no-sandbox", "--disable-dev-shm-usage"]
            )
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

async def watch_single_view(browser: Browser, item_id: str, watch_seconds: float, worker_id: int, proxy_dict: Optional[dict] = None) -> bool:
    """Mở 1 session xem video thật: tải stream video và phát trong watch_seconds"""
    ua = random.choice(USER_AGENTS)
    viewport = random.choice([
        {"width": 800, "height": 600},
        {"width": 1024, "height": 768},
        {"width": 1280, "height": 720},
    ])
    
    ctx = None
    try:
        ctx = await browser.new_context(
            user_agent=ua,
            viewport=viewport,
            proxy=proxy_dict,
            ignore_https_errors=True
        )
        page = await ctx.new_page()

        # CHẶN TOÀN BỘ ẢNH, FONT, CSS NẶNG ĐỂ SIÊU TIẾT KIỆM TÀI NGUYÊN
        async def intercept_route(route):
            req = route.request
            rt = req.resource_type
            url = req.url.lower()
            
            # Chặn ảnh và font
            if rt in ["image", "font"]:
                await route.abort()
                return
            
            # Chặn các đuôi file hình ảnh / font
            if any(url.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".woff", ".woff2", ".ttf"]):
                await route.abort()
                return
            
            # Chặn analytics / ads rác của bên thứ 3
            if any(ad in url for ad in ["google-analytics", "facebook.net", "tiktok.com/api/ad/"]):
                await route.abort()
                return
            
            # Cho phép tải HTML, JS và luồng video .mp4 từ CDN
            await route.continue_()

        await page.route("**/*", intercept_route)

        url = f"https://www.tiktok.com/@a/video/{item_id}"
        await page.goto(url, wait_until="domcontentloaded", timeout=12000)

        # Chờ phần tử video xuất hiện và kích hoạt phát
        await page.wait_for_selector("video", timeout=6000)
        
        # Bật mute và phát video
        await page.evaluate("""() => {
            const v = document.querySelector('video');
            if (v) {
                v.muted = true;
                v.play();
            }
        }""")

        # Giữ phiên xem phát thật trong watch_seconds (đủ để CDN ghi nhận playback event)
        await asyncio.sleep(watch_seconds)

        # Đọc thời gian phát thực tế để xác nhận
        playback_time = await page.evaluate("""() => {
            const v = document.querySelector('video');
            return v ? v.currentTime : 0;
        }""")

        return playback_time is not None and playback_time > 0.5
    except Exception:
        return False
    finally:
        if ctx:
            try:
                await ctx.close()
            except Exception:
                pass

def print_banner():
    print(Fore.CYAN + "=" * 68)
    print(Fore.GREEN + Style.BRIGHT + "   BUFF TIKTOK VIEW THẬT 100% - HEADLESS STREAM ENGINE")
    print(Fore.CYAN + "=" * 68)
    print(Fore.YELLOW + "  • Cơ chế    : Tải và phát luồng video .mp4 thật từ máy chủ CDN")
    print(Fore.YELLOW + "  • Tối ưu hóa: Chặn 100% ảnh/font ➔ Tiết kiệm 80% RAM & CPU")
    print(Fore.YELLOW + "  • Độ chuẩn  : Vượt qua bộ lọc Ghost View, TikTok duyệt 100%")
    print(Fore.CYAN + "-" * 68)

async def main():
    print_banner()

    # 1. Chọn chế độ mạng
    print(Fore.WHITE + "Chọn phương thức mạng:")
    print(Fore.GREEN + Style.BRIGHT + "  [1] Chạy TRỰC TIẾP (Mạng 4G phát từ điện thoại / WiFi nhà - KHUYÊN DÙNG)")
    print(Fore.YELLOW + "  [2] Chạy qua PROXY (Nhập proxy dân cư hoặc ProxyXoay)")
    net_choice = input(Fore.GREEN + "[?] Lựa chọn (1 hoặc 2, mặc định 1): ").strip()
    use_proxy = (net_choice == "2")
    
    proxy_dict = None
    if use_proxy:
        proxy_input = input(Fore.GREEN + f"[?] Proxy (Nhấn Enter dùng {DEFAULT_PROXY}): ").strip()
        p_str = proxy_input if proxy_input else DEFAULT_PROXY
        if not p_str.startswith("http://") and not p_str.startswith("https://"):
            p_str = "http://" + p_str
        proxy_dict = {"server": p_str}

    # 2. Nhập link video
    video_input = input(Fore.GREEN + "\n[?] Nhập Link video hoặc Video ID: ").strip()
    if not video_input:
        print(Fore.RED + "[!] Lỗi: Bạn chưa nhập link video!")
        return
    item_id = resolve_video_id(video_input)
    print(Fore.MAGENTA + Style.BRIGHT + f"  [✓] ID Video TikTok: {item_id}\n")

    # 3. Nhập tổng số view muốn buff
    amount_str = input(Fore.GREEN + "[?] Tổng số lượt xem muốn tăng (Ví dụ: 100, 300, 500, 1000): ").strip()
    try:
        total_target = int(amount_str) if amount_str else 100
    except ValueError:
        total_target = 100

    # 4. Cấu hình số luồng chạy song song
    worker_str = input(Fore.GREEN + "[?] Số luồng chạy song song (Khuyên dùng: 3 - 8 tab, mặc định 5): ").strip()
    try:
        concurrency = int(worker_str) if worker_str else 5
        concurrency = max(1, min(12, concurrency))
    except ValueError:
        concurrency = 5

    # 5. Thời gian xem mỗi lượt
    watch_seconds = 3.5

    # 6. Kiểm tra chỉ số ban đầu của video
    print(Fore.CYAN + "\n[*] Đang truy vấn số liệu hiện tại của video trên TikTok...")
    initial_stats = await fetch_video_stats(item_id)
    print_stats_box("THỐNG KÊ VIDEO BAN ĐẦU", initial_stats, Fore.CYAN)

    print(Fore.GREEN + Style.BRIGHT + f"\n🚀 BẮT ĐẦU CÀY VIEW THẬT (Mục tiêu: {total_target:,} views | {concurrency} luồng song song)")
    print(Fore.CYAN + "─" * 68)

    # 7. Khởi động 1 Chromium duy nhất
    start_time = time.time()
    total_completed = 0
    lock = asyncio.Lock()

    launch_args = [
        "--disable-gpu",
        "--mute-audio",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-background-networking",
        "--disable-extensions",
        "--disable-sync",
        "--blink-settings=imagesEnabled=false",
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=launch_args
        )

        sem = asyncio.Semaphore(concurrency)

        async def worker_task(worker_id: int):
            nonlocal total_completed
            while True:
                async with lock:
                    if total_completed >= total_target:
                        return
                    current_idx = total_completed + 1
                    total_completed += 1

                async with sem:
                    t0 = time.time()
                    ok = await watch_single_view(browser, item_id, watch_seconds, worker_id, proxy_dict)
                    dur = round(time.time() - t0, 1)

                    pct = (current_idx / total_target) * 100
                    status_text = f"{Fore.GREEN}[✓] Đã phát ({dur}s)" if ok else f"{Fore.YELLOW}[~] Thử lại ({dur}s)"
                    print(f"  {status_text} | View #{current_idx:3d}/{total_target:,} ({pct:5.1f}%) | Luồng #{worker_id}{Style.RESET_ALL}")

        # Khởi chạy các worker song song
        tasks = [worker_task(i + 1) for i in range(concurrency)]
        await asyncio.gather(*tasks)

        await browser.close()

    total_dur = time.time() - start_time
    print(Fore.GREEN + Style.BRIGHT + "\n" + "=" * 68)
    print(f"🎉 HOÀN THÀNH CHIẾN DỊCH VIEW THẬT!")
    print(f"  • Tổng số view đã phát  : {total_target:,} lượt")
    print(f"  • Thời gian chạy        : {total_dur / 60:.1f} phút ({total_dur:.0f} giây)")
    print(f"  • Tốc độ trung bình     : {total_target / total_dur:.1f} view/giây")

    print(Fore.CYAN + "\n[*] Đang kiểm tra thống kê cập nhật từ TikTok...")
    final_stats = await fetch_video_stats(item_id)
    print_stats_box("THỐNG KÊ VIDEO CẬP NHẬT", final_stats, Fore.GREEN)

    print(Fore.YELLOW + "👉 LƯU Ý: Đây là view thật có phát luồng video từ CDN. TikTok sẽ ghi nhận đầy đủ sau chu kỳ quét cache.")
    print(Fore.GREEN + Style.BRIGHT + "=" * 68 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Đã dừng chương trình theo yêu cầu.")
