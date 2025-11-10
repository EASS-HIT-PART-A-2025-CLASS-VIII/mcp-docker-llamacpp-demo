#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-1234}
HOST=${HOST:-0.0.0.0}
MODEL_REPO=${MODEL_REPO:-ggml-org/gemma-3-270m-it-GGUF}
IMAGE=${IMAGE:-ghcr.io/ggml-org/llama.cpp:server}
CONTEXT=${CONTEXT:-4096}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker CLI is required" >&2
  exit 1
fi

echo "Starting llama.cpp server on ${HOST}:${PORT} using ${MODEL_REPO}..."

docker run --rm \
  -p "${PORT}:${PORT}" \
  "${IMAGE}" \
  -hf "${MODEL_REPO}" \
  --port "${PORT}" \
  --host "${HOST}" \
  --jinja \
  -c "${CONTEXT}" \
  "$@"
