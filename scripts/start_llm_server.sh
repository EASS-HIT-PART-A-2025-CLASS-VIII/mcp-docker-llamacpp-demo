#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-1234}
HOST=${HOST:-0.0.0.0}
MODEL_REPO=${MODEL_REPO:-ggml-org/gemma-3-270m-it-GGUF}
IMAGE=${IMAGE:-ghcr.io/ggml-org/llama.cpp:server}
CONTEXT=${CONTEXT:-4096}
PULL_IMAGE=${PULL_IMAGE:-true}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker CLI is required" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Start Docker Desktop and rerun this script." >&2
  exit 1
fi

shopt -s nocasematch
if [[ "${PULL_IMAGE}" != "false" && "${PULL_IMAGE}" != "0" ]]; then
  echo "Pulling container image ${IMAGE} (override with PULL_IMAGE=false)..."
  docker pull "${IMAGE}"
fi
shopt -u nocasematch

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
