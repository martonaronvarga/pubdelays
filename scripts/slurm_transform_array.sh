#!/usr/bin/env bash
#SBATCH --job-name=pubdelays-transform
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=06:00:00
set -euo pipefail

ROOT="${ROOT:-$(pwd)}"
CONFIG="${CONFIG:-$ROOT/config/default.toml}"
RUN="${RUN:-pubdelays-pipeline}"
INPUTS="${INPUTS:-$ROOT/data/manifests/transform_inputs.txt}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/data/temp_data/article_parquet}"
TASK_ID="${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is not set}"
SHARDS="${SHARDS:-64}"

mkdir -p "$OUTPUT_DIR"
"$RUN" --config "$CONFIG" transform-shard \
  --input-list "$INPUTS" \
  --output-dir "$OUTPUT_DIR" \
  --shard-index "$TASK_ID" \
  --shards "$SHARDS" \
  --format parquet \
  --resume
