"""Sitemap discovery — pull a site's full page list from sitemap.xml.

Government CMSes (Joomla, Drupal, WordPress) almost always publish a sitemap that
enumerates every content page — far more complete than crawling links. Handles
sitemap *index* files (which point at sub-sitemaps) recursively.
"""

from __future__ import annotations

import re

import httpx

from .allowlist import is_allowed
from .fetch import USER_AGENT

_LOC = re.compile(r"<loc>\s*([^<]+?)\s*</loc>", re.IGNORECASE)


def _get(url: str) -> str:
    try:
        r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return ""


def sitemap_urls(domain: str, *, max_urls: int = 600) -> list[str]:
    """Return allow-listed content URLs from a domain's sitemap(s)."""
    candidates = [
        f"https://{domain}/sitemap.xml",
        f"https://{domain}/sitemap_index.xml",
        f"https://{domain}/sitemap-index.xml",
        f"https://{domain}/wp-sitemap.xml",  # WordPress 5.5+
        f"https://{domain}/index.php?option=com_jmap&view=sitemap&format=xml",  # Joomla
    ]
    seen_maps: set[str] = set()
    queue = list(candidates)
    urls: list[str] = []

    while queue and len(urls) < max_urls:
        sm = queue.pop(0)
        if sm in seen_maps:
            continue
        seen_maps.add(sm)
        xml = _get(sm)
        if not xml:
            continue
        locs = _LOC.findall(xml)
        if "<sitemapindex" in xml.lower():
            queue.extend(loc for loc in locs if loc not in seen_maps)
        else:
            for loc in locs:
                if is_allowed(loc) and loc not in urls:
                    urls.append(loc)
    return urls[:max_urls]
