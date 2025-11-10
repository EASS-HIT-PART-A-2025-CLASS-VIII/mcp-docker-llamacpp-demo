#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-8080}
TRANSPORT=${TRANSPORT:-streaming}
SERVERS=${SERVERS:-duckduckgo,playwright,youtube_transcript}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker CLI is required" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Start Docker Desktop and rerun this script." >&2
  exit 1
fi

if ! docker mcp --help >/dev/null 2>&1; then
  echo "The docker MCP plugin is required. Install via 'docker extension install docker/mcp'." >&2
  exit 1
fi

for server in ${SERVERS//,/ }; do
  echo "Ensuring MCP server '$server' is enabled..."
  docker mcp server enable "$server" >/dev/null || true
done

echo "Starting MCP gateway on port ${PORT} with transport ${TRANSPORT}..."

docker mcp gateway run \
  --port "${PORT}" \
  --transport "${TRANSPORT}" \
  --servers="${SERVERS}" \
  "$@"
