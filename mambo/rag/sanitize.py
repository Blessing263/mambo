"""Light output sanitisation — strip HTML tags and safe-markdown injection from
LLM outputs before they reach the citizen-facing UI.
"""

from __future__ import annotations

import re

_HTML_TAG = re.compile(r"<[^>]*>")
_SCRIPT = re.compile(r"<script[^>]*>.*?</script>", re.I | re.S)
_STYLE = re.compile(r"<style[^>]*>.*?</style>", re.I | re.S)
_JS_URI = re.compile(r"javascript\s*:", re.I)
_EVENT_ATTR = re.compile(
    r"\bon(?:load|error|click|mouse|key|focus|blur|submit|change|scroll"
    r"|resize|input|select|dblclick|contextmenu)\s*=", re.I)


def sanitize(text: str) -> str:
    if not text:
        return text
    t = _SCRIPT.sub("", text)
    t = _STYLE.sub("", t)
    t = _HTML_TAG.sub("", t)
    t = _JS_URI.sub("blocked:", t)
    t = _EVENT_ATTR.sub(" ", t)
    return t
