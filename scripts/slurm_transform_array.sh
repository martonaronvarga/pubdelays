#!/usr/bin/env bash
#SBATCH --job-name=pubdelays-transform
#SBATCH --cpus-per-task=4          # one modulo shard per task; Polars can use allocated CPUs
#SBATCH --mem=24G                  # external metadata is loaded once per shard task
#SBATCH --time=06:00:00            # rerun failed task IDs after fixing inputs or resources
#SBATCH --output=logs/%x-%A_%a.out # array/task IDs make failed shards easy to identify
#SBATCH --error=logs/%x-%A_%a.err
set -euo pipefail

ROOT="${ROOT:-$(pwd)}"
CONFIG="${CONFIG:-$ROOT/config/default.toml}"
RUN="${RUN:-pubdelays-pipeline}"
INPUTS="${INPUTS:-$ROOT/data/manifests/transform_inputs.txt}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/data/temp_data/article_parquet}"
TASK_ID="${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is not set}"
SHARDS="${SHARDS:-64}"

[[ -s "$INPUTS" ]] || { echo "Missing or empty transform input list: $INPUTS" >&2; exit 2; }
mkdir -p "$OUTPUT_DIR" logs
"$RUN" --config "$CONFIG" transform-shard \
  --input-list "$INPUTS" \
  --output-dir "$OUTPUT_DIR" \
  --shard-index "$TASK_ID" \
  --shards "$SHARDS" \
  --format parquet \
  --resume
