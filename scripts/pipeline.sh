#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
RUN="${RUN:-pubdelays-pipeline}"
MANIFEST="${MANIFEST:-$ROOT/data/manifests/pipeline.sqlite}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 4)}"

RAW_XML_DIR="${RAW_XML_DIR:-$ROOT/data/raw_data/pubmed/xmls}"
JSONL_DIR="${JSONL_DIR:-$ROOT/data/temp_data/pubmed/jsonl}"
ARTICLE_DIR="${ARTICLE_DIR:-$ROOT/data/temp_data/article_parquet}"
PROCESSED_PARQUET="${PROCESSED_PARQUET:-$ROOT/data/processed_data/processed.parquet}"
PROCESSED_CSV="${PROCESSED_CSV:-$ROOT/data/processed_data/processed.csv}"

SCIMAGO_RAW="${SCIMAGO_RAW:-$ROOT/data/raw_data/scimago}"
WOS_RAW="${WOS_RAW:-$ROOT/data/raw_data/web_of_science/wos.csv}"
DOAJ_RAW="${DOAJ_RAW:-$ROOT/data/raw_data/directory_of_open_access_journals/doaj_2025_05_15.csv}"
NPI_RAW="${NPI_RAW:-$ROOT/data/raw_data/norwegian_publication_indicator/norwegian_list_2025_05_14.csv}"
RW_RAW="${RW_RAW:-$ROOT/data/raw_data/retraction_watch/retraction_watch.csv}"

SCIMAGO="${SCIMAGO:-$ROOT/data/processed_data/scimago.csv}"
WOS="${WOS:-$ROOT/data/processed_data/web_of_science.csv}"
DOAJ="${DOAJ:-$ROOT/data/processed_data/doaj.csv}"
NPI="${NPI:-$ROOT/data/processed_data/norwegian_list.csv}"
RW="${RW:-$ROOT/data/processed_data/retraction_watch.csv}"

mkdir -p "$RAW_XML_DIR" "$JSONL_DIR" "$ARTICLE_DIR" "$ROOT/data/processed_data" "$ROOT/data/manifests" "$ROOT/data/external"
cd "$ROOT"

"$RUN" preflight \
  --pubmed-xml-dir "$RAW_XML_DIR" \
  --scimago-dir "$SCIMAGO_RAW" \
  --web-of-science "$WOS_RAW" \
  --doaj "$DOAJ_RAW" \
  --norwegian-list "$NPI_RAW" \
  --retraction-watch "$RW_RAW"

"$RUN" external-scimago --input-dir "$SCIMAGO_RAW" --output "$SCIMAGO" --manifest "$MANIFEST" --resume
"$RUN" external-wos --input "$WOS_RAW" --output "$WOS" --manifest "$MANIFEST" --resume
"$RUN" external-doaj --input "$DOAJ_RAW" --output "$DOAJ" --manifest "$MANIFEST" --resume
"$RUN" external-npi --input "$NPI_RAW" --output "$NPI" --manifest "$MANIFEST" --resume
"$RUN" external-retraction-watch --input "$RW_RAW" --output "$RW" --manifest "$MANIFEST" --resume

"$RUN" journals --output "$ROOT/data/external/pubmed-journals.csv" --manifest "$MANIFEST" --resume

"$RUN" parse \
  --input-dir "$RAW_XML_DIR" \
  --output-dir "$JSONL_DIR" \
  --format jsonl \
  --parse-mesh-subterms \
  --jobs "$JOBS" \
  --manifest "$MANIFEST" \
  --resume

"$RUN" validate "$JSONL_DIR" --manifest "$MANIFEST"

"$RUN" transform \
  --input "$JSONL_DIR" \
  --output-dir "$ARTICLE_DIR" \
  --format parquet \
  --scimago "$SCIMAGO" \
  --web-of-science "$WOS" \
  --doaj "$DOAJ" \
  --norwegian-list "$NPI" \
  --retraction-watch "$RW" \
  --jobs "$JOBS" \
  --manifest "$MANIFEST" \
  --resume

"$RUN" aggregate --input "$ARTICLE_DIR" --output "$PROCESSED_PARQUET" --manifest "$MANIFEST" --resume
"$RUN" aggregate --input "$ARTICLE_DIR" --output "$PROCESSED_CSV" --manifest "$MANIFEST" --resume
