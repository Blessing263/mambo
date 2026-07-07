#!/usr/bin/env bash
# Embed all pending chunks on a RunPod GPU, then restore local Ollama and shut the pod.
# Usage: POD_IP=<ip> POD_ID=<id> ./scripts/runpod_embed.sh

set -euo pipefail
RUNPOD_API_KEY="${RUNPOD_API_KEY:?set RUNPOD_API_KEY in the environment}"
POD_IP="${POD_IP:?set POD_IP}"
POD_ID="${POD_ID:?set POD_ID}"
OLLAMA_URL="http://${POD_IP}:11434"

echo "=== $(date) Pulling qwen3-embedding:8b on GPU pod ${POD_IP} ==="
curl -s --max-time 600 "${OLLAMA_URL}/api/pull" -d '{"name":"qwen3-embedding:8b"}' | tail -1
echo "=== verifying model ==="
curl -s "${OLLAMA_URL}/api/tags" | jq -r '.models[]? | "\(.name) \(.size)"' | grep qwen

echo "=== $(date) Running bulk embed via GPU ==="
cd "$(dirname "$0")/.."
export OLLAMA_BASE_URL="${OLLAMA_URL}"
export EMBED_MODEL="qwen3-embedding:8b"
export EMBED_DIM="4096"
export RUZIVO_EMBED_BATCH="64"
uv run python -m ingestion.embed_bulk

echo "=== $(date) Embed complete. Verifying ==="
psql "${DATABASE_URL}" -c \
  "SELECT dim, count(*) FROM chunks WHERE embedding IS NOT NULL GROUP BY dim;"

echo "=== $(date) Terminating pod ${POD_ID} ==="
curl -s --max-time 15 -X DELETE "https://rest.runpod.io/v1/pods/${POD_ID}" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" | jq -r '.id // "terminated"'

echo "=== $(date) Done. Local ollama-ruzivo service unchanged. ==="
