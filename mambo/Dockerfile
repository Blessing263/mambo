FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY uv.lock pyproject.toml ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev \
    && uv pip install --system psycopg_pool

COPY . .

EXPOSE 8770

ENV RUZIVO_ENV=production

CMD ["uv", "run", "uvicorn", "rag.api:app", "--host", "0.0.0.0", "--port", "8770"]
