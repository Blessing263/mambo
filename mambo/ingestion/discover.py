"""Discovery — breadth-first crawl within allow-listed official hosts to find
documents (PDFs) and content pages worth ingesting. Bounded by page/doc limits
so a crawl is always quick and polite.
"""

from __future__ import annotations

from collections import deque
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup

from .allowlist import is_allowed
from .fetch import FetchBlocked, fetch


def _clean(url: str) -> str:
    return urldefrag(url)[0]


def discover(seed_urls: list[str], *, max_pages: int = 40, max_docs: int = 50) -> dict:
    """Crawl from seeds, returning discovered PDF URLs and visited HTML pages.

    Returns {'pdf_urls': [...], 'html_pages': [(url, content_bytes), ...]}.
    HTML page bytes are returned so the caller can ingest them without re-fetching.
    """
    seen: set[str] = set()
    pdf_urls: list[str] = []
    html_pages: list[tuple[str, bytes]] = []
    queue: deque[str] = deque(_clean(u) for u in seed_urls)

    while queue and len(seen) < max_pages and len(pdf_urls) < max_docs:
        url = _clean(queue.popleft())
        if url in seen or not is_allowed(url):
            continue
        seen.add(url)
        try:
            content, content_type, final_url = fetch(url)
        except (FetchBlocked, Exception):
            continue

        final_url = _clean(final_url)
        is_pdf = "pdf" in content_type or final_url.lower().endswith(".pdf")
        if is_pdf:
            if final_url not in pdf_urls:
                pdf_urls.append(final_url)
            continue
        if "html" not in content_type:
            continue

        html_pages.append((final_url, content))
        soup = BeautifulSoup(content, "lxml")
        for anchor in soup.find_all("a", href=True):
            link = _clean(urljoin(final_url, anchor["href"]))
            if not is_allowed(link) or link in seen:
                continue
            if link.lower().endswith(".pdf"):
                if link not in pdf_urls:
                    pdf_urls.append(link)
            else:
                queue.append(link)

    return {"pdf_urls": pdf_urls[:max_docs], "html_pages": html_pages}
