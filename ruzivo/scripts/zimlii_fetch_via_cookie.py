"""
Hybrid ZimLII fetcher — uses a cf_clearance cookie from a real browser session
to fetch judgment content from the VPS via curl_cffi (which mimics browser TLS).

Workflow:
  1. Open https://zimlii.org in Chrome, press F12 → Application → Cookies → zimlii.org
  2. Copy the value of cf_clearance
  3. Run: python scripts/zimlii_fetch_via_cookie.py <cf_clearance_value> [--limit 200]

The cookie bypasses Cloudflare because Cloudflare sees a cookie from a session
that already passed the challenge. curl_cffi handles the TLS fingerprint matching.
"""
import sys, json, argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from curl_cffi import requests as cffi_requests
from ingestion.pipeline import ingest_content  # noqa: E402
from shared.db import get_conn  # noqa: E402

OUT_DIR = REPO_ROOT / "raw_docs" / "zimlii"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cookie", help="cf_clearance cookie value from Chrome DevTools")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--urls-file", default="zimlii_judgment_urls.json")
    args = parser.parse_args()

    urls_file = Path(args.urls_file)
    if not urls_file.exists():
        print(f"Error: {urls_file} not found. Run the JS snippet in Chrome first.")
        sys.exit(1)

    urls = json.loads(urls_file.read_text())
    batch = urls[args.start : args.start + args.limit]
    print(f"Fetching {len(batch)} of {len(urls)} judgments (cookie provided)")

    session = cffi_requests.Session(impersonate="chrome124")
    session.cookies.set("cf_clearance", args.cookie, domain=".zimlii.org")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    })

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT source_url FROM documents WHERE ministry_id='zimlii'")
        done = {r["source_url"] for r in cur.fetchall()}

    ok = skipped = blocked = errors = 0
    for i, url in enumerate(batch):
        if url in done:
            skipped += 1
            continue

        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 403 or "Just a moment" in resp.text[:500]:
                blocked += 1
                print(f"  [{i+1}/{len(batch)}] BLOCKED — cookie expired, get a fresh one from Chrome")
                break
            if resp.status_code != 200:
                errors += 1
                print(f"  [{i+1}/{len(batch)}] HTTP {resp.status_code}: {url[:80]}")
                continue

            slug = url.rstrip("/").split("/")[-1]
            (OUT_DIR / f"{slug}.html").write_text(resp.text, encoding="utf-8")

            status, _w, nchunks = ingest_content(
                url, resp.text.encode("utf-8"), "text/html", ministry_id="zimlii"
            )
            if status == "ingested":
                ok += 1
                if ok % 25 == 0:
                    print(f"  …{ok} ingested")
            else:
                print(f"  [{i+1}/{len(batch)}] {status}: {url[:80]}")

        except Exception as e:
            errors += 1
            print(f"  [{i+1}/{len(batch)}] error: {e}")

    print(f"\nDone: {ok} ingested, {skipped} skipped, {blocked} blocked, {errors} errors")


if __name__ == "__main__":
    main()
