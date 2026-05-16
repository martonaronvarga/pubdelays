#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CONFIG="${CONFIG:-$ROOT/config/default.toml}"
RUN="${RUN:-pubdelays-pipeline}"
SOURCE="${SOURCE:-baseline}"
JOBS="${JOBS:-4}"
LIMIT_ARGS=()
if [[ -n "${LIMIT:-}" ]]; then
  LIMIT_ARGS=(--limit "$LIMIT")
fi

cd "$ROOT"
"$RUN" --config "$CONFIG" download --source "$SOURCE" --jobs "$JOBS" --resume "${LIMIT_ARGS[@]}"
