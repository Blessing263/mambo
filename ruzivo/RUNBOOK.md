# Ruzivo — Runbook (local VPS: meet.ziklag.co.uk)

How to run and operate the demo. Architecture & decisions live in `FOUNDATION.md`.

## Public URL
**https://ruzivo.yttrix.tech** — nginx (`/etc/nginx/sites-available/ruzivo.yttrix.tech`,
Let's Encrypt cert, auto-renew) → Next.js (:3055) → `/api/*` rewrite → RAG API (:8770).
SSE streaming preserved (`proxy_buffering off`).

## Services & ports (all systemd, enabled = survive reboot)
| Component | Where | Port | systemd unit |
|---|---|---|---|
| Embedding engine | isolated Ollama **0.30.6** | `127.0.0.1:11435` | `ollama-ruzivo` |
| Knowledge Store | Postgres 16 + pgvector 0.6.0 | `127.0.0.1:5432` | `postgresql` (db `ruzivo`) |
| RAG API (Module 2) | uvicorn `rag.api:app` | `127.0.0.1:8770` | `ruzivo-api` |
| Webchat (Module 1) | Next.js **production** (`npm start`) | `127.0.0.1:3055` | `ruzivo-web` |

```bash
# manage
sudo systemctl status ruzivo-api ruzivo-web ollama-ruzivo
sudo systemctl restart ruzivo-api      # after code changes in rag/ or shared/
# after webchat code changes: rebuild then restart
cd /home/blessing/patriot/webchat && npm run build && sudo systemctl restart ruzivo-web
journalctl -u ruzivo-api -n 50 --no-pager   # logs
```

## Embeddings (Qwen 4096-dim) — gather locally, embed on GPU
All 1,298 chunks are embedded at uniform **4096-dim** (qwen3-embedding:8b). CPU embedding
is ~16s/chunk (too slow for bulk); a RunPod GPU does it at ~0.10s/chunk. **Live queries**
embed locally (~1.5s warm — short text). To (re)embed in bulk on a GPU:
```bash
# 1. Create a RunPod pod (ollama/ollama:latest, any GPU, env OLLAMA_HOST=0.0.0.0, HTTP port 11434)
#    HTTP ports have NO public IP — use the proxy URL: https://<POD_ID>-11434.proxy.runpod.net
# 2. curl https://<POD_ID>-11434.proxy.runpod.net/api/pull -d '{"name":"qwen3-embedding:8b"}'
# 3. embed all NULL chunks, then terminate the pod:
export OLLAMA_BASE_URL=https://<POD_ID>-11434.proxy.runpod.net
export EMBED_MODEL=qwen3-embedding:8b EMBED_DIM=4096 RUZIVO_EMBED_BATCH=64
uv run python -m ingestion.embed_bulk
curl -X DELETE https://rest.runpod.io/v1/pods/<POD_ID> -H "Authorization: Bearer $RUNPOD_API_KEY"
```

> The system Ollama (`:11434`, v0.18.2) is **untouched** — it segfaults on local models
> (broken ggml backend), so embeddings run on the isolated `ollama-ruzivo` instance.
> Model store copied to `~/.ollama-ruzivo/models`; binary at `~/.ollama-ruzivo/bin`.

## Secrets / config
- DeepSeek key: read from `~/.secrets/deepseek-api-key` (also in `.env`, which is edit-locked by a global rule).
- Config defaults live in `shared/config.py` (override via real env vars).
- DB: `postgresql://ruzivo:ruzivo_local_dev@127.0.0.1:5432/ruzivo`

## Start everything
```bash
# 1. Embedding engine (already a durable service)
sudo systemctl status ollama-ruzivo

# 2. RAG API
cd /home/blessing/patriot
uv run uvicorn rag.api:app --host 127.0.0.1 --port 8770 &

# 3. Webchat
cd /home/blessing/patriot/webchat
npm run dev &   # http://127.0.0.1:3055
```

## View the demo from your laptop
The web/API bind to localhost on the VPS. Tunnel over SSH:
```bash
ssh -L 3055:127.0.0.1:3055 blessing@meet.ziklag.co.uk
# then open http://localhost:3055 in your browser
```
(Or bind Next to `0.0.0.0` and open the firewall — productionisation step.)

## Ingest documents
```bash
cd /home/blessing/patriot
uv run python registry/load_registry.py                       # sync registry -> DB
uv run python -m ingestion.pipeline --ministry ict --max-docs 8
uv run python -m ingestion.pipeline --url <official-pdf-url>   # one document
```

## Health checks
```bash
curl -s http://127.0.0.1:8770/health | jq .
curl -s http://127.0.0.1:11435/api/version
psql "$DATABASE_URL" -c "SELECT ministry_id, count(*) FROM chunks GROUP BY 1;"
```
