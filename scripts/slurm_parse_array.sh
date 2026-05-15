#!/usr/bin/env bash
#SBATCH --job-name=pubdelays-parse
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=04:00:00
set -euo pipefail

ROOT="${ROOT:-$(pwd)}"
RUN="${RUN:-pubdelays-pipeline}"
MANIFEST="${MANIFEST:-$ROOT/data/manifests/pipeline.sqlite}"
INPUTS="${INPUTS:-$ROOT/data/manifests/parse_inputs.txt}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/data/temp_data/pubmed/jsonl}"
TASK_ID="${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is not set}"
INPUT="$(sed -n "$((TASK_ID + 1))p" "$INPUTS")"

[[ -n "$INPUT" ]] || { echo "No input at array index $TASK_ID" >&2; exit 2; }
mkdir -p "$OUTPUT_DIR"
BASENAME="$(basename "$INPUT")"
"$RUN" parse-one \
  --input "$INPUT" \
  --output "$OUTPUT_DIR/$BASENAME.jsonl" \
  --format jsonl \
  --parse-mesh-subterms \
  --manifest "$MANIFEST" \
  --resume
