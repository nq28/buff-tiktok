# File: tiktok_all_in_one.py
# Runtime: Python 3.11+ | Dependencies: playwright, httpx[http2,socks]
# Note: httpx[socks] required via 'socksio' when routing socks4/socks5 proxies through async checker.

import asyncio
import random
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import httpx
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

PROXY_SOURCES = [
    # Ưu tiên lọc trực tiếp quốc gia VN từ API
    ("http", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=VN&ssl=all&anonymity=all"),
    ("socks4", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=5000&country=VN"),
    ("socks5", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=VN"),
    ("http", "https://www.proxy-list.download/api/v1/get?type=http&country=VN"),
    ("socks4", "https://www.proxy-list.download/api/v1/get?type=socks4&country=VN"),
    ("socks5", "https://www.proxy-list.download/api/v1/get?type=socks5&country=VN"),
    # Nguồn tổng hợp cập nhật mỗi 5-15 phút (sẽ lọc GeoIP VN/SEA ở bước 2)
    ("http", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=4000&country=SG,TH,VN,TW,HK,MY&ssl=all&anonymity=all"),
    ("socks5", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=4000&country=SG,TH,VN,TW,HK,MY"),
    ("http", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    ("socks4", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt"),
    ("socks5", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt"),
    ("http", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
    ("socks5", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt"),
    ("http", "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt"),
]

IP_PORT_REGEX = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{2,5}\b")

VN_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Redmi Note 12 Pro 5G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.118 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

VN_VIEWPORTS = [
    {"width": 390, "height": 844, "is_mobile": True, "has_touch": True, "device_scale_factor": 3},
    {"width": 412, "height": 915, "is_mobile": True, "has_touch": True, "device_scale_factor": 2.625},
    {"width": 393, "height": 873, "is_mobile": True, "has_touch": True, "device_scale_factor": 2.75},
    {"width": 1920, "height": 1080, "is_mobile": False, "has_touch": False, "device_scale_factor": 1},
]

VN_REFERERS = [
    "https://www.google.com.vn/",
    "https://m.facebook.com/",
    "https://zalo.me/",
    "https://www.tiktok.com/explore",
    "https://www.tiktok.com/foryou",
]

STEALTH_INIT_SCRIPT = """
(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'language', { get: () => 'vi-VN' });
    Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi', 'en-US', 'en'] });
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => %d });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => %d });

    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return 'Google Inc. (ARM)';
        if (param === 37446) return 'ANGLE (ARM, Mali-G78 MP20, OpenGL ES 3.2)';
        return getParameter.apply(this, arguments);
    };

    const toDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function() {
        const ctx = this.getContext('2d');
        if (ctx) {
            const shift = %d;
            const imgData = ctx.getImageData(0, 0, Math.min(this.width, 10), Math.min(this.height, 10));
            for (let i = 0; i < imgData.data.length; i += 4) {
                imgData.data[i] = (imgData.data[i] + shift) %% 256;
            }
            ctx.putImageData(imgData, 0, 0);
        }
        return toDataURL.apply(this, arguments);
    };

    if (window.RTCPeerConnection) {
        const OrigPeerConnection = window.RTCPeerConnection;
        window.RTCPeerConnection = function(config) {
            if (config && config.iceServers) {
                config.iceServers = [];
            }
            return new OrigPeerConnection(config);
        };
    }

    Object.defineProperty(document, 'hidden', { get: () => false });
    Object.defineProperty(document, 'visibilityState', { get: () => 'visible' });
})();
"""


@dataclass(order=True)
class VerifiedProxy:
    score: float
    scheme: str = field(compare=False)
    address: str = field(compare=False)
    country: str = field(compare=False)
    latency_ms: float = field(compare=False)

    @property
    def url(self) -> str:
        return f"{self.scheme}://{self.address}"

    @property
    def playwright_dict(self) -> dict:
        return {"server": self.url}


@dataclass(frozen=True)
class EngineConfig:
    target_url: str
    total_views: int
    concurrency: int
    min_watch_sec: float
    max_watch_sec: float
    strict_vn_only: bool
    max_scan_candidates: int
    proxy_save_path: Path
    headless: bool = True


@dataclass
class StatsCounter:
    attempted: int = 0
    retained_views: int = 0
    proxy_errors: int = 0
    telemetry_pings: int = 0


async def fetch_source(client: httpx.AsyncClient, scheme: str, url: str) -> List[Tuple[str, str]]:
    found: List[Tuple[str, str]] = []
    try:
        resp = await client.get(url, timeout=10.0)
        if resp.status_code == 200:
            matches = IP_PORT_REGEX.findall(resp.text)
            for m in matches:
                found.append((scheme, m))
    except Exception:
        pass
    return found


async def harvest_raw_proxies(max_candidates: int = 1200) -> List[Tuple[str, str]]:
    print("[*] Đang cào proxy free từ 14 nguồn public & API khu vực...")
    seen: Set[str] = set()
    priority_list: List[Tuple[str, str]] = []
    general_list: List[Tuple[str, str]] = []

    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        tasks = [fetch_source(client, scheme, url) for scheme, url in PROXY_SOURCES]
        results = await asyncio.gather(*tasks)

    for idx, batch in enumerate(results):
        is_priority = idx < 8  # 8 nguồn đầu tiên là VN và SEA
        for scheme, addr in batch:
            key = f"{scheme}://{addr}"
            if key not in seen:
                seen.add(key)
                if is_priority:
                    priority_list.append((scheme, addr))
                else:
                    general_list.append((scheme, addr))

    random.shuffle(general_list)
    combined = priority_list + general_list
    selected = combined[:max_candidates]
    print(f"[*] Thu thập được {len(seen)} proxy thô. Chọn {len(selected)} ứng viên ưu tiên để lọc sống...")
    return selected


async def probe_single_proxy(
    scheme: str,
    addr: str,
    sem: asyncio.Semaphore,
    strict_vn: bool,
    timeout: float = 6.5,
) -> Optional[VerifiedProxy]:
    proxy_url = f"{scheme}://{addr}"
    allowed_sea = {"VN", "SG", "TH", "TW", "HK", "MY", "ID", "PH"}

    async with sem:
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=timeout,
                verify=False,
                follow_redirects=True,
            ) as client:
                # Bước 1: Kiểm tra IP + Quốc gia
                geo_resp = await client.get("http://ip-api.com/json/?fields=status,countryCode,query")
                if geo_resp.status_code != 200:
                    return None
                geo_data = geo_resp.json()
                if geo_data.get("status") != "success":
                    return None

                cc = geo_data.get("countryCode", "XX")
                if strict_vn and cc != "VN":
                    return None
                if not strict_vn and cc not in allowed_sea:
                    return None

                # Bước 2: Kiểm tra thông kết nối tới TikTok (tránh proxy bị TikTok chặn IP)
                tt_resp = await client.get(
                    "https://www.tiktok.com/robots.txt",
                    headers={"User-Agent": random.choice(VN_USER_AGENTS)},
                )
                if tt_resp.status_code not in (200, 301, 302):
                    return None

                latency = (time.perf_counter() - t0) * 1000.0
                # Chấm điểm ưu tiên: VN được giảm 2000 điểm để luôn xếp đầu bảng
                priority_bonus = -2000.0 if cc == "VN" else (-500.0 if cc in {"SG", "TH"} else 0.0)
                score = latency + priority_bonus

                return VerifiedProxy(
                    score=score,
                    scheme=scheme,
                    address=addr,
                    country=cc,
                    latency_ms=latency,
                )
        except Exception:
            return None


async def build_verified_proxy_pool(cfg: EngineConfig) -> List[VerifiedProxy]:
    candidates = await harvest_raw_proxies(cfg.max_scan_candidates)
    if cfg.proxy_save_path.exists():
        # Nạp thêm các proxy cũ từng sống ở lần chạy trước để kiểm tra lại
        for line in cfg.proxy_save_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "://" in line:
                parts = line.split("://", 1)
                candidates.insert(0, (parts[0], parts[1]))

    check_sem = asyncio.Semaphore(120)
    print(f"[*] Đang lọc sống & test cổng TikTok cho {len(candidates)} proxy (120 luồng async)...")

    tasks = [
        probe_single_proxy(scheme, addr, check_sem, cfg.strict_vn_only)
        for scheme, addr in candidates
    ]
    results = await asyncio.gather(*tasks)
    verified = [r for r in results if r is not None]
    verified.sort()

    # Lưu ra file proxies_vn.txt để tái sử dụng
    if verified:
        lines = [p.url for p in verified]
        cfg.proxy_save_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    vn_count = sum(1 for p in verified if p.country == "VN")
    sea_count = len(verified) - vn_count
    print(
        f"[+] Lọc hoàn tất: {len(verified)} Proxy vượt bài test TikTok "
        f"(VN: {vn_count} | Cụm SEA vệ tinh: {sea_count}) -> Đã lưu vào {cfg.proxy_save_path}"
    )
    return verified


def generate_vn_device_cookies() -> List[dict]:
    tt_webid = "".join(random.choices("0123456789", k=19))
    csrf_token = uuid.uuid4().hex
    return [
        {"name": "tt_webid", "value": tt_webid, "domain": ".tiktok.com", "path": "/"},
        {"name": "tt_webid_v2", "value": tt_webid, "domain": ".tiktok.com", "path": "/"},
        {"name": "tt_csrf_token", "value": csrf_token[:16], "domain": ".tiktok.com", "path": "/"},
        {"name": "ttwid", "value": f"1%7C{uuid.uuid4().hex}%7C{int(time.time())}", "domain": ".tiktok.com", "path": "/"},
    ]


async def simulate_human_interaction(page: Page, watch_duration: float) -> int:
    start_ts = time.monotonic()
    telemetry_hits = 0

    def on_request(req):
        nonlocal telemetry_hits
        u = req.url
        if any(k in u for k in ("/aweme/v1/", "mcs.tiktokv.com", "mon.tiktokv.com", "/api/item_detail/")):
            telemetry_hits += 1

    page.on("request", on_request)

    try:
        for selector in [
            '[data-e2e="modal-close-inner-button"]',
            'button:has-text("Decline optional cookies")',
            'button:has-text("Không phải bây giờ")',
            'div[role="dialog"] button[aria-label="Close"]',
        ]:
            loc = page.locator(selector).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click(timeout=1500)
                await asyncio.sleep(random.uniform(0.3, 0.7))
    except Exception:
        pass

    await page.evaluate(
        """() => {
            const v = document.querySelector('video');
            if (v) {
                v.muted = true;
                v.play().catch(() => {});
            }
        }"""
    )

    while (time.monotonic() - start_ts) < watch_duration:
        elapsed = time.monotonic() - start_ts
        remaining = watch_duration - elapsed
        step = min(random.uniform(2.5, 5.2), max(0.5, remaining))
        await asyncio.sleep(step)

        action_roll = random.random()
        try:
            if action_roll < 0.45:
                x = random.randint(75, 330)
                y = random.randint(180, 660)
                await page.mouse.move(x, y, steps=random.randint(5, 14))
            elif action_roll < 0.72:
                await page.mouse.wheel(0, random.randint(20, 70))
                await asyncio.sleep(random.uniform(0.25, 0.6))
                await page.mouse.wheel(0, -random.randint(15, 55))
            else:
                await page.evaluate(
                    """() => {
                        const v = document.querySelector('video');
                        if (v && v.paused) v.play().catch(() => {});
                    }"""
                )
        except Exception:
            break

    return telemetry_hits


async def run_view_worker(
    browser: Browser,
    cfg: EngineConfig,
    proxy_pool: List[VerifiedProxy],
    bad_proxies: Dict[str, int],
    stats: StatsCounter,
    sem: asyncio.Semaphore,
    worker_id: int,
) -> None:
    async with sem:
        stats.attempted += 1

        # Lọc các proxy chưa bị quá 2 lần lỗi liên tiếp
        active_candidates = [p for p in proxy_pool if bad_proxies.get(p.url, 0) < 2]
        chosen: Optional[VerifiedProxy] = None
        if active_candidates:
            # Ưu tiên bốc trong top 40% proxy nhanh nhất/VN
            top_slice = max(1, int(len(active_candidates) * 0.4))
            chosen = random.choice(active_candidates[:top_slice])

        ua = random.choice(VN_USER_AGENTS)
        vp = random.choice(VN_VIEWPORTS)
        referer = random.choice(VN_REFERERS)
        cores = random.choice([4, 6, 8])
        mem = random.choice([4, 6, 8])
        canvas_shift = random.randint(1, 7)

        context_kwargs = {
            "user_agent": ua,
            "viewport": {"width": vp["width"], "height": vp["height"]},
            "is_mobile": vp["is_mobile"],
            "has_touch": vp["has_touch"],
            "device_scale_factor": vp["device_scale_factor"],
            "locale": "vi-VN",
            "timezone_id": "Asia/Ho_Chi_Minh",
            "geolocation": {
                "latitude": round(random.uniform(10.75, 21.03), 5),
                "longitude": round(random.uniform(105.80, 106.70), 5),
                "accuracy": random.randint(15, 75),
            },
            "permissions": ["geolocation"],
            "extra_http_headers": {
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": referer,
            },
        }
        if chosen:
            context_kwargs["proxy"] = chosen.playwright_dict

        context: Optional[BrowserContext] = None
        proxy_tag = f"{chosen.country}:{chosen.address} ({chosen.latency_ms:.0f}ms)" if chosen else "DIRECT_IP"

        try:
            context = await browser.new_context(**context_kwargs)
            await context.add_init_script(STEALTH_INIT_SCRIPT % (cores, mem, canvas_shift))
            await context.add_cookies(generate_vn_device_cookies())

            page = await context.new_page()
            await page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ("font", "image")
                and "tiktokv.com" not in route.request.url
                else route.continue_(),
            )

            watch_sec = random.uniform(cfg.min_watch_sec, cfg.max_watch_sec)
            resp = await page.goto(cfg.target_url, wait_until="domcontentloaded", timeout=32000)
            if not resp or resp.status >= 400:
                stats.proxy_errors += 1
                if chosen:
                    bad_proxies[chosen.url] = bad_proxies.get(chosen.url, 0) + 1
                return

            hits = await simulate_human_interaction(page, watch_sec)
            stats.telemetry_pings += hits
            stats.retained_views += 1

            print(
                f"[#{worker_id:03d}] [OK] [{proxy_tag}] Watch: {watch_sec:.1f}s | "
                f"Telemetry: {hits:02d} | Retained: {stats.retained_views}/{cfg.total_views}"
            )
        except Exception as exc:
            stats.proxy_errors += 1
            if chosen:
                bad_proxies[chosen.url] = bad_proxies.get(chosen.url, 0) + 1
            print(f"[#{worker_id:03d}] [DROP] [{proxy_tag}] {type(exc).__name__}")
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass


async def run_pipeline(cfg: EngineConfig) -> None:
    proxy_pool = await build_verified_proxy_pool(cfg)
    if not proxy_pool and cfg.strict_vn_only:
        print("[!] Chế độ chỉ lọc IP VN không tìm được proxy free sống lúc này. Tự động mở rộng sang cụm SEA vệ tinh...")
        fallback_cfg = EngineConfig(
            target_url=cfg.target_url,
            total_views=cfg.total_views,
            concurrency=cfg.concurrency,
            min_watch_sec=cfg.min_watch_sec,
            max_watch_sec=cfg.max_watch_sec,
            strict_vn_only=False,
            max_scan_candidates=cfg.max_scan_candidates,
            proxy_save_path=cfg.proxy_save_path,
            headless=cfg.headless,
        )
        proxy_pool = await build_verified_proxy_pool(fallback_cfg)

    if not proxy_pool:
        print("[!] Tất cả proxy free đều nghẽn. Chuyển sang chạy trực tiếp bằng IP gốc của máy.")

    sem = asyncio.Semaphore(cfg.concurrency)
    stats = StatsCounter()
    bad_proxies: Dict[str, int] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=cfg.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-webrtc-encryption",
                "--no-sandbox",
            ],
        )

        tasks = []
        for idx in range(1, cfg.total_views + 1):
            tasks.append(
                asyncio.create_task(
                    run_view_worker(browser, cfg, proxy_pool, bad_proxies, stats, sem, idx)
                )
            )
            await asyncio.sleep(random.uniform(0.3, 1.0))

        await asyncio.gather(*tasks)
        await browser.close()

    print("\n" + "=" * 60)
    print(f"BÁO CÁO TỔNG KẾT | Target: {cfg.target_url}")
    print(f"- Proxy sạch nạp vào bể : {len(proxy_pool)} (Lưu tại: {cfg.proxy_save_path})")
    print(f"- Tổng phiên chạy       : {stats.attempted}")
    print(f"- View giữ chân thành công: {stats.retained_views}")
    print(f"- Tổng gói Telemetry đẩy: {stats.telemetry_pings}")
    print(f"- Phiên lỗi do Proxy free: {stats.proxy_errors}")
    print("=" * 60)


def main() -> None:
    print("=== TIKTOK VN PROXY HARVESTER + NON-DROP VIEW ENGINE ===")
    mode = input("Chọn chế độ [1 = Cào/Lọc Proxy + Buff View | 2 = Chỉ Cào & Xuất file Proxy]: ").strip() or "1"

    strict_choice = input("Chỉ lấy duy nhất IP Việt Nam? [y/N - mặc định N để lấy cả VN + SEA tốc độ cao]: ").strip().lower()
    strict_vn = strict_choice == "y"
    scan_limit = int(input("Số lượng proxy thô tối đa muốn quét (VD: 1000): ").strip() or "1000")

    if mode == "2":
        cfg = EngineConfig(
            target_url="https://www.tiktok.com",
            total_views=0,
            concurrency=1,
            min_watch_sec=10,
            max_watch_sec=20,
            strict_vn_only=strict_vn,
            max_scan_candidates=scan_limit,
            proxy_save_path=Path("proxies_vn.txt"),
        )
        asyncio.run(build_verified_proxy_pool(cfg))
        return

    target = input("Nhập link video TikTok: ").strip()
    if not target.startswith("http"):
        print("Link video không hợp lệ.")
        sys.exit(1)

    try:
        total_views = int(input("Số lượng view cần chạy (VD: 100): ").strip() or "100")
        concurrency = int(input("Số luồng chạy song song (VD: 5): ").strip() or "5")
        min_watch = float(input("Thời gian xem tối thiểu (giây, VD: 12): ").strip() or "12")
        max_watch = float(input("Thời gian xem tối đa (giây, VD: 25): ").strip() or "25")
    except ValueError:
        print("Thông số phải là số hợp lệ.")
        sys.exit(1)

    concurrency = max(1, min(concurrency, 30))
    if max_watch < min_watch:
        max_watch = min_watch + 5.0

    cfg = EngineConfig(
        target_url=target,
        total_views=total_views,
        concurrency=concurrency,
        min_watch_sec=min_watch,
        max_watch_sec=max_watch,
        strict_vn_only=strict_vn,
        max_scan_candidates=scan_limit,
        proxy_save_path=Path("proxies_vn.txt"),
        headless=True,
    )
    asyncio.run(run_pipeline(cfg))


if __name__ == "__main__":
    main()