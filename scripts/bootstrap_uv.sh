#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install uv first: https://docs.astral.sh/uv/" >&2
  exit 1
fi

uv sync --extra dev
cat <<'EOF'
Environment ready.
Run commands with:
  uv run pubdelays-pipeline --help
  uv run pytest -q
EOF

