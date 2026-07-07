"""Central configuration for Mambo.

Secret handling: the DeepSeek API key is read from the environment if present,
otherwise from ~/.secrets/deepseek-api-key (where it already lives via OpenCode).
We deliberately do NOT auto-load a .env file here — the project's .env is
protected by a global secret rule, and relying on code defaults keeps every
script runnable out-of-the-box. Override any value via real environment vars.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_SECRETS_KEY_FILE = Path.home() / ".secrets" / "deepseek-api-key"


def _deepseek_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key and key.strip():
        return key.strip()
    if _SECRETS_KEY_FILE.exists():
        return _SECRETS_KEY_FILE.read_text().strip().strip('"')
    raise RuntimeError(
        "DeepSeek API key not found: set DEEPSEEK_API_KEY or create "
        f"{_SECRETS_KEY_FILE}"
    )


# ── Shared environment-derived values (single source of truth) ─────────────
# IS_PROD defaults to TRUE so docs/redoc are disabled and cookies are secure
# unless the operator explicitly sets RUZIVO_ENV=development.
IS_PROD = os.environ.get("RUZIVO_ENV", "production").lower() != "development"

_ALLOWED_ORIGINS = [
    h.strip() for h in
    os.environ.get("RUZIVO_ALLOWED_ORIGINS",
        "https://mambo.yttrix.tech,https://ruzivo.yttrix.tech,http://localhost:3000,http://localhost:3055"
    ).split(",") if h.strip()
]

# ── Runtime tuning knobs (all overridable via env vars) ────────────────────
RETRIEVAL_TOP_K = int(os.environ.get("RUZIVO_RETRIEVAL_K", "6"))
CONFIDENCE_THRESHOLD = float(os.environ.get("RUZIVO_RETRIEVAL_CONFIDENCE", "0.45"))
RESCUE_MARGIN = float(os.environ.get("RUZIVO_RESCUE_MARGIN", "0.08"))
NONCE_TTL = int(os.environ.get("RUZIVO_NONCE_TTL_SECS", "300"))
CONCURRENT_STREAMS_MAX = int(os.environ.get("RUZIVO_CONCURRENT_STREAMS", "5"))
MIN_QUESTION_GAP = float(os.environ.get("RUZIVO_MIN_QUESTION_GAP", "0.5"))
CLEANUP_INTERVAL = int(os.environ.get("RUZIVO_SECURITY_CLEANUP_SECS", "300"))
HISTORY_TURNS = int(os.environ.get("RUZIVO_HISTORY_TURNS", "6"))
RETRIEVAL_OVERSAMPLE = int(os.environ.get("RUZIVO_RETRIEVAL_OVERSAMPLE", "3"))
SESSION_TTL = int(os.environ.get("RUZIVO_SESSION_TTL_HOURS", "12")) * 3600


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    ollama_base_url: str
    embed_model: str
    embed_dim: int
    database_url: str
    is_prod: bool = field(default=IS_PROD)
    allowed_origins: list[str] = field(default_factory=lambda: _ALLOWED_ORIGINS)
    retrieval_top_k: int = field(default=RETRIEVAL_TOP_K)
    confidence_threshold: float = field(default=CONFIDENCE_THRESHOLD)
    rescue_margin: float = field(default=RESCUE_MARGIN)
    nonce_ttl: int = field(default=NONCE_TTL)
    concurrent_streams_max: int = field(default=CONCURRENT_STREAMS_MAX)
    min_question_gap: float = field(default=MIN_QUESTION_GAP)
    cleanup_interval: int = field(default=CLEANUP_INTERVAL)
    history_turns: int = field(default=HISTORY_TURNS)
    retrieval_oversample: int = field(default=RETRIEVAL_OVERSAMPLE)
    session_ttl: int = field(default=SESSION_TTL)

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            deepseek_api_key=_deepseek_key(),
            deepseek_base_url=os.environ.get(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
            ),
            deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11435"),
            embed_model=os.environ.get("EMBED_MODEL", "qwen3-embedding:8b"),
            embed_dim=int(os.environ.get("EMBED_DIM", "4096")),
            database_url=os.environ.get("DATABASE_URL", ""),
        )


settings = Settings.load()
