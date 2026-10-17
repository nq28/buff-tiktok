# File: tiktok_smart_progress.py
# Runtime: Python 3.11+ | Dependencies: playwright, httpx[http2,socks], tqdm
# Note: Integrated real-time tqdm progress bars for proxy harvesting, async probing, and view emission.

import asyncio
import json
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
from tqdm import tqdm

PROXY_SOURCES = [
    ("http", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=VN&ssl=all&anonymity=all"),
    ("socks4", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=5000&country=VN"),
    ("socks5", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=VN"),
    ("http", "https://www.proxy-list.download/api/v1/get?type=http&country=VN"),
    ("socks4", "https://www.proxy-list.download/api/v1/get?type=socks4&country=VN"),
    ("socks5", "https://www.proxy-list.download/api/v1/get?type=socks5&country=VN"),
    ("http", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=4000&country=SG,TH,VN,TW,HK,MY&ssl=all&anonymity=all"),
    ("socks5", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=4000&country=SG,TH,VN,TW,HK,MY"),
    ("http", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    ("socks4", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt"),
    ("socks5", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt"),
    ("http", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
    ("socks5", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt"),
]

IP_PORT_REGEX = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{2,5}\b")

VN_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Redmi Note 12 Pro 5G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.118 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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


@dataclass
class SmartEngineConfig:
    target_url: str
    total_views: int
    concurrency: int
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


async def fetch_source_with_progress(client: httpx.AsyncClient, scheme: str, url: str, pbar: tqdm) -> List[Tuple[str, str]]:
    found: List[Tuple[str, str]] = []
    try:
        resp = await client.get(url, timeout=9.0)
        if resp.status_code == 200:
            for m in IP_PORT_REGEX.findall(resp.text):
                found.append((scheme, m))
    except Exception:
        pass
    finally:
        pbar.update(1)
    return found


async def harvest_raw_proxies(max_candidates: int = 1200) -> List[Tuple[str, str]]:
    seen: Set[str] = set()
    priority, general = [], []

    print("[*] Đang cào proxy từ 14 nguồn...")
    with tqdm(total=len(PROXY_SOURCES), desc="[1/3] Cào Proxy Thô", colour="cyan") as pbar:
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            tasks = [fetch_source_with_progress(client, s, u, pbar) for s, u in PROXY_SOURCES]
            results = await asyncio.gather(*tasks)

    for idx, batch in enumerate(results):
        is_priority = idx < 6
        for scheme, addr in batch:
            key = f"{scheme}://{addr}"
            if key not in seen:
                seen.add(key)
                if is_priority:
                    priority.append((scheme, addr))
                else:
                    general.append((scheme, addr))

    random.shuffle(general)
    selected = (priority + general)[:max_candidates]
    print(f"[+] Thu thập tổng cộng {len(seen)} proxy thô. Lọc lấy {len(selected)} ứng viên.")
    return selected


async def probe_single_proxy(
    scheme: str,
    addr: str,
    sem: asyncio.Semaphore,
    strict_vn: bool,
    pbar: tqdm,
    timeout: float = 5.5,
) -> Optional[VerifiedProxy]:
    proxy_url = f"{scheme}://{addr}"
    allowed_sea = {"VN", "SG", "TH", "TW", "HK", "MY", "ID", "PH"}

    async with sem:
        t0 = time.perf_counter()
        result = None
        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=timeout, verify=False, follow_redirects=True) as client:
                r = await client.get("http://ip-api.com/json/?fields=status,countryCode")
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == "success":
                        cc = data.get("countryCode", "XX")
                        if not (strict_vn and cc != "VN") and (strict_vn or cc in allowed_sea):
                            tt = await client.get("https://www.tiktok.com/robots.txt", headers={"User-Agent": random.choice(VN_USER_AGENTS)})
                            if tt.status_code in (200, 301, 302):
                                latency = (time.perf_counter() - t0) * 1000.0
                                bonus = -2500.0 if cc == "VN" else (-600.0 if cc in {"SG", "TH"} else 0.0)
                                result = VerifiedProxy(score=latency + bonus, scheme=scheme, address=addr, country=cc, latency_ms=latency)
        except Exception:
            pass
        finally:
            pbar.update(1)
        return result


async def build_verified_proxy_pool(cfg: SmartEngineConfig) -> List[VerifiedProxy]:
    candidates = await harvest_raw_proxies(cfg.max_scan_candidates)
    if cfg.proxy_save_path.exists():
        for line in cfg.proxy_save_path.read_text(encoding="utf-8").splitlines():
            if "://" in line:
                p = line.split("://", 1)
                candidates.insert(0, (p[0], p[1]))

    sem = asyncio.Semaphore(100)
    verified = []

    with tqdm(total=len(candidates), desc="[2/3] Kiểm tra & Lọc Proxy Sống", colour="green") as pbar:
        tasks = [probe_single_proxy(s, a, sem, cfg.strict_vn_only, pbar) for s, a in candidates]
        results = await asyncio.gather(*tasks)
        verified = [r for r in results if r is not None]

    verified.sort()
    if verified:
        cfg.proxy_save_path.write_text("\n".join(p.url for p in verified) + "\n", encoding="utf-8")

    vn = sum(1 for p in verified if p.country == "VN")
    print(f"[+] Hoàn tất lọc: {len(verified)} proxy sạch sẵn sàng (VN: {vn} | SEA: {len(verified)-vn})")
    return verified


async def smart_detect_video_duration(target_url: str) -> float:
    print("[*] Đang bóc tách độ dài thực tế của video TikTok...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=random.choice(VN_USER_AGENTS), viewport={"width": 390, "height": 844}, locale="vi-VN")
        page = await context.new_page()
        duration = 15.0
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(2.0)
            dur = await page.evaluate(
                """() => {
                    const v = document.querySelector('video');
                    if (v && !isNaN(v.duration) && v.duration > 0) return v.duration;
                    try {
                        const script = document.getElementById('SIGI_STATE') || document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
                        if (script) {
                            const json = JSON.parse(script.innerText);
                            const match = JSON.stringify(json).match(/"duration":\s*(\d+)/);
                            if (match) return parseFloat(match[1]);
                        }
                    } catch(e) {}
                    return null;
                }"""
            )
            if dur and dur > 1.0:
                duration = float(dur)
        except Exception:
            pass
        finally:
            await browser.close()
    print(f"[+] Thời lượng video chuẩn: {duration:.1f} giây.")
    return duration


def generate_vn_device_cookies() -> List[dict]:
    tt_webid = "".join(random.choices("0123456789", k=19))
    return [
        {"name": "tt_webid", "value": tt_webid, "domain": ".tiktok.com", "path": "/"},
        {"name": "tt_webid_v2", "value": tt_webid, "domain": ".tiktok.com", "path": "/"},
        {"name": "tt_csrf_token", "value": uuid.uuid4().hex[:16], "domain": ".tiktok.com", "path": "/"},
        {"name": "ttwid", "value": f"1%7C{uuid.uuid4().hex}%7C{int(time.time())}", "domain": ".tiktok.com", "path": "/"},
    ]


async def simulate_smart_interaction(page: Page, watch_duration: float) -> int:
    start_ts = time.monotonic()
    telemetry_hits = 0

    def on_request(req):
        nonlocal telemetry_hits
        if any(k in req.url for k in ("/aweme/v1/", "mcs.tiktokv.com", "mon.tiktokv.com", "/api/item_detail/")):
            telemetry_hits += 1

    page.on("request", on_request)

    try:
        for sel in ['[data-e2e="modal-close-inner-button"]', 'button:has-text("Không phải bây giờ")']:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click(timeout=1000)
                await asyncio.sleep(0.2)
    except Exception:
        pass

    await page.evaluate("const v = document.querySelector('video'); if (v) { v.muted = true; v.play().catch(() => {}); }")

    while (time.monotonic() - start_ts) < watch_duration:
        elapsed = time.monotonic() - start_ts
        remaining = watch_duration - elapsed
        await asyncio.sleep(min(random.uniform(2.0, 4.0), max(0.3, remaining)))
        try:
            roll = random.random()
            if roll < 0.4:
                await page.mouse.move(random.randint(80, 320), random.randint(200, 600), steps=random.randint(4, 8))
            elif roll < 0.7:
                await page.mouse.wheel(0, random.randint(15, 50))
            else:
                await page.evaluate("const v = document.querySelector('video'); if (v && v.paused) v.play().catch(()=>{});")
        except Exception:
            break

    return telemetry_hits


async def run_smart_worker(
    browser: Browser,
    cfg: SmartEngineConfig,
    video_duration: float,
    proxy_pool: List[VerifiedProxy],
    bad_proxies: Dict[str, int],
    stats: StatsCounter,
    sem: asyncio.Semaphore,
    pbar_view: tqdm,
) -> None:
    async with sem:
        stats.attempted += 1
        active = [p for p in proxy_pool if bad_proxies.get(p.url, 0) < 2]
        chosen = random.choice(active[:max(1, int(len(active) * 0.35))]) if active else None

        watch_sec = max(6.0, min(video_duration * random.uniform(0.85, 1.15), 55.0))
        context_kwargs = {
            "user_agent": random.choice(VN_USER_AGENTS),
            "viewport": {"width": 390, "height": 844},
            "is_mobile": True,
            "has_touch": True,
            "device_scale_factor": 3,
            "locale": "vi-VN",
            "timezone_id": "Asia/Ho_Chi_Minh",
            "extra_http_headers": {"Accept-Language": "vi-VN,vi;q=0.9", "Referer": "https://www.tiktok.com/foryou"},
        }
        if chosen:
            context_kwargs["proxy"] = chosen.playwright_dict

        context = None
        try:
            context = await browser.new_context(**context_kwargs)
            await context.add_init_script(STEALTH_INIT_SCRIPT % (random.choice([4, 6, 8]), random.choice([4, 8]), random.randint(1, 6)))
            await context.add_cookies(generate_vn_device_cookies())

            page = await context.new_page()
            await page.route("**/*", lambda r: r.abort() if r.request.resource_type in ("font", "image") and "tiktokv.com" not in r.request.url else r.continue_())

            resp = await page.goto(cfg.target_url, wait_until="domcontentloaded", timeout=28000)
            if not resp or resp.status >= 400:
                stats.proxy_errors += 1
                if chosen: bad_proxies[chosen.url] = bad_proxies.get(chosen.url, 0) + 1
                pbar_view.update(1)
                return

            hits = await simulate_smart_interaction(page, watch_sec)
            stats.telemetry_pings += hits
            stats.retained_views += 1
        except Exception:
            stats.proxy_errors += 1
            if chosen: bad_proxies[chosen.url] = bad_proxies.get(chosen.url, 0) + 1
        finally:
            if context:
                try: await context.close()
                except Exception: pass
            pbar_view.update(1)
            pbar_view.set_postfix(success=stats.retained_views, errors=stats.proxy_errors)


async def orchestrate_smart(cfg: SmartEngineConfig) -> None:
    proxy_pool = await build_verified_proxy_pool(cfg)
    video_duration = await smart_detect_video_duration(cfg.target_url)

    sem = asyncio.Semaphore(cfg.concurrency)
    stats = StatsCounter()
    bad_proxies: Dict[str, int] = {}

    print(f"\n[3/3] Đang tiến hành buff {cfg.total_views} view (Luồng song song: {cfg.concurrency})...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=cfg.headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--autoplay-policy=no-user-gesture-required"]
        )
        
        with tqdm(total=cfg.total_views, desc="Tiến trình Buff View", colour="magenta") as pbar_view:
            tasks = [
                asyncio.create_task(run_smart_worker(browser, cfg, video_duration, proxy_pool, bad_proxies, stats, sem, pbar_view))
                for _ in range(cfg.total_views)
            ]
            for task in tasks:
                await asyncio.gather(task)
                await asyncio.sleep(random.uniform(0.1, 0.4))

        await browser.close()

    print("\n" + "=" * 60)
    print(f"BÁO CÁO HOÀN TẤT | Tổng View Thành Công: {stats.retained_views}/{cfg.total_views}")
    print(f"- Thời lượng video gốc: {video_duration:.1f}s")
    print(f"- Tổng gói telemetry: {stats.telemetry_pings}")
    print(f"- Lỗi kết nối proxy : {stats.proxy_errors}")
    print("=" * 60)


def main() -> None:
    print("=== TIKTOK SMART ENGINE + LIVE PROGRESS BARS ===")
    target = input("Nhập link video TikTok: ").strip()
    if not target.startswith("http"):
        sys.exit(1)

    try:
        total_views = int(input("Số lượng view cần chạy (VD: 100): ").strip() or "100")
        concurrency = int(input("Số luồng song song (VD: 5): ").strip() or "5")
    except ValueError:
        sys.exit(1)

    cfg = SmartEngineConfig(
        target_url=target,
        total_views=total_views,
        concurrency=max(1, min(concurrency, 30)),
        strict_vn_only=False,
        max_scan_candidates=1200,
        proxy_save_path=Path("proxies_vn.txt"),
        headless=True,
    )
    asyncio.run(orchestrate_smart(cfg))


if __name__ == "__main__":
    main()