"""Central configuration for Ruzivo.

Secret handling: the DeepSeek API key is read from the environment if present,
otherwise from ~/.secrets/deepseek-api-key (where it already lives via OpenCode).
We deliberately do NOT auto-load a .env file here — the project's .env is
protected by a global secret rule, and relying on code defaults keeps every
script runnable out-of-the-box. Override any value via real environment vars.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Settings:
    # --- DeepSeek (generation / backbone LLM) ---
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str

    # --- Embeddings (isolated Ollama 0.30.6 on :11435, CPU) ---
    ollama_base_url: str
    embed_model: str
    embed_dim: int

    # --- Knowledge Store ---
    database_url: str

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            deepseek_api_key=_deepseek_key(),
            deepseek_base_url=os.environ.get(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
            ),
            # flash is ~6x faster than pro (pro is a reasoning model that "thinks"
            # ~15-20s first). For grounded RAG, flash quality is more than enough.
            deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11435"),
            embed_model=os.environ.get("EMBED_MODEL", "qwen3-embedding:8b"),
            embed_dim=int(os.environ.get("EMBED_DIM", "4096")),
            database_url=os.environ.get(
                "DATABASE_URL",
                "postgresql://ruzivo:ruzivo_local_dev@127.0.0.1:5432/ruzivo",
            ),
        )


settings = Settings.load()
