import json
from playwright.sync_api import sync_playwright

url = "https://www.tiktok.com/@chauhp1337/video/7647538174658415879"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720}
    )
    page = context.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except:
        pass
    
    stats = page.evaluate("""() => {
        try {
            const el = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
            if (el) {
                const data = JSON.parse(el.innerText);
                const scope = data['__DEFAULT_SCOPE__'];
                const detail = scope['webapp.video-detail'];
                return detail.itemInfo.itemStruct.stats;
            }
        } catch(e) {}
        return null;
    }""")
    print("Exact stats:", json.dumps(stats, indent=2))
    browser.close()
