"""
Import locally-fetched ZimLII raw HTML files into the Knowledge Store.
Run on the VPS after transferring raw_docs/zimlii/ from your machine.

Usage:
    RUZIVO_NO_EMBED=true python scripts/zimlii_import_raw.py
"""
import sys, json, os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ingestion.pipeline import ingest_content
from shared.db import get_conn

RAW_DIR = REPO_ROOT / "raw_docs" / "zimlii"
URLS_FILE = Path("zimlii_judgment_urls.json")


def main():
    if not URLS_FILE.exists():
        print(f"Error: {URLS_FILE} not found. Copy it from your machine first.")
        sys.exit(1)

    urls = json.loads(URLS_FILE.read_text())
    url_to_file = {}
    for f in RAW_DIR.glob("*.html"):
        slug = f.stem
        url_to_file[slug] = f

    # Get already ingested URLs
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT source_url FROM documents WHERE ministry_id='zimlii'")
        done = {r["source_url"] for r in cur.fetchall()}

    todo = []
    for url in urls:
        slug = url.rstrip("/").split("/")[-1]
        if url in done:
            continue
        fpath = url_to_file.get(slug)
        if fpath and fpath.exists():
            todo.append((url, fpath))

    print(f"{len(todo)} judgments to import ({len(done)} already ingested, "
          f"{len(urls) - len(todo) - len(done)} missing files)")

    imported = skipped = errors = 0
    for url, fpath in todo:
        try:
            html = fpath.read_bytes()
            status, _w, nchunks = ingest_content(
                url, html, "text/html", ministry_id="zimlii"
            )
            if status == "ingested":
                imported += 1
                if imported % 25 == 0:
                    print(f"  …{imported} imported")
            elif status == "skipped":
                skipped += 1
            else:
                errors += 1
                print(f"  {status}: {url[:80]}")
        except Exception as e:
            errors += 1
            print(f"  error: {fpath.name}: {e}")

    print(f"Done: {imported} imported, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
