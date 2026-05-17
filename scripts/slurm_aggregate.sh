#!/usr/bin/env bash
#SBATCH --job-name=pubdelays-aggregate
#SBATCH --cpus-per-task=4       # single aggregation job; Polars can use allocated CPUs
#SBATCH --mem=16G               # raise for full-corpus aggregation if shard validation passes but collection is memory-bound
#SBATCH --time=02:00:00         # safe to rerun because aggregate-all uses atomic outputs and --resume
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
set -euo pipefail

ROOT="${ROOT:-$(pwd)}"
CONFIG="${CONFIG:-$ROOT/config/default.toml}"
RUN="${RUN:-pubdelays-pipeline}"

mkdir -p logs
ARGS=(--resume)
if [[ -n "${SHARDS:-}" ]]; then
  ARGS+=(--shards "$SHARDS")
fi
if [[ -n "${FORMAT:-}" ]]; then
  ARGS+=(--format "$FORMAT")
fi

"$RUN" --config "$CONFIG" aggregate-all "${ARGS[@]}"
