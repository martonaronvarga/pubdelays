#!/usr/bin/env bash
#SBATCH --job-name=pubdelays-transform
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=06:00:00
set -euo pipefail

ROOT="${ROOT:-$(pwd)}"
RUN="${RUN:-pubdelays-pipeline}"
MANIFEST="${MANIFEST:-$ROOT/data/manifests/pipeline.sqlite}"
INPUTS="${INPUTS:-$ROOT/data/manifests/transform_inputs.txt}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/data/temp_data/article_parquet}"
TASK_ID="${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is not set}"
SHARDS="${SHARDS:-64}"

SCIMAGO="${SCIMAGO:-$ROOT/data/processed_data/scimago.csv}"
WOS="${WOS:-$ROOT/data/processed_data/web_of_science.csv}"
DOAJ="${DOAJ:-$ROOT/data/processed_data/doaj.csv}"
NPI="${NPI:-$ROOT/data/processed_data/norwegian_list.csv}"
RW="${RW:-$ROOT/data/processed_data/retraction_watch.csv}"

mkdir -p "$OUTPUT_DIR"
"$RUN" transform-shard \
  --input-list "$INPUTS" \
  --output-dir "$OUTPUT_DIR" \
  --shard-index "$TASK_ID" \
  --shards "$SHARDS" \
  --format parquet \
  --scimago "$SCIMAGO" \
  --web-of-science "$WOS" \
  --doaj "$DOAJ" \
  --norwegian-list "$NPI" \
  --retraction-watch "$RW" \
  --manifest "$MANIFEST" \
  --resume
