#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "${ROOT_DIR}"

if command -v uv >/dev/null 2>&1; then
  echo "Running analyzer via uv..."
  uv run python script.py "$@"
else
  echo "uv not found; using system python"
  python script.py "$@"
fi
