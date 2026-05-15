#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(pwd)}"
RUN="${RUN:-pubdelays-pipeline}"
MANIFEST_DIR="${MANIFEST_DIR:-$ROOT/data/manifests}"
RAW_XML_DIR="${RAW_XML_DIR:-$ROOT/data/raw_data/pubmed/xmls}"
JSONL_DIR="${JSONL_DIR:-$ROOT/data/temp_data/pubmed/jsonl}"
mkdir -p "$MANIFEST_DIR"

"$RUN" list-inputs --kind xml --input-dir "$RAW_XML_DIR" --output "$MANIFEST_DIR/parse_inputs.txt"
"$RUN" list-inputs --kind json --input-dir "$JSONL_DIR" --output "$MANIFEST_DIR/transform_inputs.txt"

parse_n=$(wc -l < "$MANIFEST_DIR/parse_inputs.txt" | tr -d ' ')
transform_n=$(wc -l < "$MANIFEST_DIR/transform_inputs.txt" | tr -d ' ')
shards="${SHARDS:-64}"

echo "parse inputs:      $parse_n"
echo "transform inputs:  $transform_n"
echo "transform shards:  $shards"
echo "Submit parsing:    sbatch --array=0-$((parse_n - 1)) scripts/slurm_parse_array.sh"
echo "Submit transform:  sbatch --array=0-$((shards - 1)) scripts/slurm_transform_array.sh"
