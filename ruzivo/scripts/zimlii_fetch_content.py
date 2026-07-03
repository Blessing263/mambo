"""
ZimLII Judgment Content Fetcher
Run from your machine (where Chrome passes Cloudflare).

Reads zimlii_judgment_urls.json, fetches each judgment via nodriver (real Chrome),
saves raw HTML files to raw_docs/zimlii/.

Usage:
    pip install nodriver
    python zimlii_fetch_content.py [--limit 50] [--start 0]
"""
import asyncio, json, os, sys, argparse
from pathlib import Path

OUT_DIR = Path("raw_docs/zimlii")
OUT_DIR.mkdir(parents=True, exist_ok=True)

async def fetch_one(browser, url: str, idx: int, total: int) -> bool:
    """Fetch a single judgment page, save raw HTML. Returns True if successful."""
    try:
        page = await browser.get(url)
        # Wait for Cloudflare challenge to clear
        for _ in range(10):
            content = await page.get_content()
            if "Just a moment" not in content:
                break
            await page.sleep(3)
        else:
            print(f"  [{idx}/{total}] CHALLENGE FAILED: {url[:80]}")
            return False

        title = await page.query_selector("h1")
        title_text = await title.evaluate("el => el.textContent") if title else "unknown"
        content = await page.get_content()

        # Extract just the main judgment text area
        main = await page.query_selector("main") or await page.query_selector(".document-content")
        if main:
            content = await main.evaluate("el => el.outerHTML")

        # Save
        slug = url.rstrip("/").split("/")[-1]
        out_path = OUT_DIR / f"{slug}.html"
        out_path.write_text(content, encoding="utf-8")

        short_title = title_text[:80].strip()
        print(f"  [{idx}/{total}] OK: {short_title}")
        return True

    except Exception as e:
        print(f"  [{idx}/{total}] ERROR: {e}")
        return False

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50, help="Max judgments to fetch")
    parser.add_argument("--start", type=int, default=0, help="Start index")
    parser.add_argument("urls_file", nargs="?", default="zimlii_judgment_urls.json")
    args = parser.parse_args()

    urls = json.loads(Path(args.urls_file).read_text())
    batch = urls[args.start : args.start + args.limit]
    print(f"Fetching {len(batch)} of {len(urls)} judgments (start={args.start})")

    import nodriver as uc
    browser = await uc.start(
        headless=False,
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"],
    )

    ok = 0
    for i, url in enumerate(batch):
        idx = args.start + i + 1
        if await fetch_one(browser, url, idx, len(urls)):
            ok += 1
        if (i + 1) % 10 == 0:
            print(f"  --- {i+1}/{len(batch)} fetched, {ok} ok ---")

    browser.stop()
    print(f"\nDone: {ok}/{len(batch)} saved to {OUT_DIR}/")

if __name__ == "__main__":
    asyncio.run(main())
