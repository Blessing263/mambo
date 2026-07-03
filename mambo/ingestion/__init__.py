"""Module 3 — Ingestion: discover → fetch → parse/OCR → chunk → embed → load.

Run as a module from the repo root so both `shared.*` and relative imports resolve:
    uv run python -m ingestion.pipeline --ministry ict --max-docs 8
    uv run python -m ingestion.pipeline --url https://www.ictministry.gov.zw/some.pdf
"""
