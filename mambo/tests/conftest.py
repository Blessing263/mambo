"""Shared pytest fixtures for Mambo.

Tests are hermetic: they never call the real DeepSeek LLM or the live Postgres DB.
A dummy DEEPSEEK_API_KEY is set before importing rag.* so shared.config loads
without ~/.secrets present (keeps the suite portable for CI/graders).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Portable config: config.load() needs a DeepSeek key to import; stub it.
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-for-pytest")
# Web verifier must stay OFF in tests (default), but be explicit:
os.environ.setdefault("RUZIVO_ENABLE_WEB_VERIFY", "")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from rag import security  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (MamboTest)"}


def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true",
                     help="run DB-dependent integration tests")


def pytest_collection_modifyitems(config, items):
    """Skip @pytest.mark.integration unless --integration (or RUN_INTEGRATION) is set."""
    if config.getoption("--integration") or os.environ.get("RUN_INTEGRATION"):
        return
    skip = pytest.mark.skip(reason="integration test (needs Postgres+pgvector); enable with --integration")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def client():
    """FastAPI TestClient against the real app (LLM/DB neutralised per-test)."""
    import rag.api as api
    from fastapi.testclient import TestClient
    return TestClient(api.app)


@pytest.fixture
def reset_security():
    """Clear in-memory security stores so tests are isolated."""
    security.reset_state()
    yield
    security.reset_state()


@pytest.fixture
def get_nonce(client):
    """Helper: fetch a fresh single-use nonce."""
    def _() -> str:
        return client.get("/nonce", headers=UA).json()["nonce"]
    return _
