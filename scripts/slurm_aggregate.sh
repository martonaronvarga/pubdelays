#!/usr/bin/env bash
#SBATCH --job-name=pubdelays-aggregate
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
set -euo pipefail

ROOT="${ROOT:-$(pwd)}"
RUN="${RUN:-pubdelays-pipeline}"
MANIFEST="${MANIFEST:-$ROOT/data/manifests/pipeline.sqlite}"
INPUT_DIR="${INPUT_DIR:-$ROOT/data/temp_data/article_parquet}"
OUTPUT="${OUTPUT:-$ROOT/data/processed_data/processed.parquet}"

"$RUN" aggregate --input "$INPUT_DIR" --output "$OUTPUT" --manifest "$MANIFEST" --resume
