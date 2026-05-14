#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
JOBS="${JOBS:-$(python3 - <<'PY'
import os
print(max((os.cpu_count() or 2) - 1, 1))
PY
)}"

XML_DIR="${XML_DIR:-$ROOT/data/raw_data/pubmed/xmls}"
JSONL_DIR="${JSONL_DIR:-$ROOT/data/raw_data/pubmed/jsonl}"
EXTERNAL_DIR="${EXTERNAL_DIR:-$ROOT/data/external}"
PROCESSED_DIR="${PROCESSED_DIR:-$ROOT/data/processed_data}"

SCIMAGO="${SCIMAGO:-$PROCESSED_DIR/scimago.csv}"
WEB_OF_SCIENCE="${WEB_OF_SCIENCE:-$PROCESSED_DIR/web_of_science.csv}"
DOAJ="${DOAJ:-$PROCESSED_DIR/doaj.csv}"
NORWEGIAN_LIST="${NORWEGIAN_LIST:-$PROCESSED_DIR/norwegian_list.csv}"
RETRACTION_WATCH="${RETRACTION_WATCH:-$PROCESSED_DIR/retraction_watch.csv}"
ARTICLES_TSV="${ARTICLES_TSV:-$PROCESSED_DIR/articles.tsv}"
FILTERS_CSV="${FILTERS_CSV:-$PROCESSED_DIR/filter_counts.csv}"

cd "$ROOT"

if [[ "${USE_NIX:-1}" == "1" ]] && command -v nix >/dev/null 2>&1; then
  PIPELINE=(nix run "$ROOT#pubdelays-pipeline" --)
else
  export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
  PIPELINE=(python3 -m pubdelays.cli)
fi

"${PIPELINE[@]}" journals \
  --output "$EXTERNAL_DIR/pubmed-journals.csv"

"${PIPELINE[@]}" parse \
  --input-dir "$XML_DIR" \
  --output-dir "$JSONL_DIR" \
  --jobs "$JOBS" \
  --format jsonl \
  --resume \
  --parse-mesh-subterms

"${PIPELINE[@]}" validate "$JSONL_DIR"

"${PIPELINE[@]}" transform \
  --input "$JSONL_DIR" \
  --output "$ARTICLES_TSV" \
  --filters-output "$FILTERS_CSV" \
  --scimago "$SCIMAGO" \
  --web-of-science "$WEB_OF_SCIENCE" \
  --doaj "$DOAJ" \
  --norwegian-list "$NORWEGIAN_LIST" \
  --retraction-watch "$RETRACTION_WATCH"
