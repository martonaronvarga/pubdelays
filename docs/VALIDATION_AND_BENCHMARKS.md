
# Validation and Benchmarks

This document defines the validation gates and performance checks for the active PubMed/MEDLINE pipeline.

## Static checks

Run before committing:

```bash
python -m compileall -q src tests
ruff check src tests
pytest -q
git diff --check
```

With Nix:

```bash
nix flake check --show-trace
nix build --show-trace --print-build-logs
```

With uv:

```bash
uv sync --extra dev
uv run pytest -q
uv run pubdelays --help
```

## CLI smoke checks

These should work without raw data:

```bash
pubdelays --help
pubdelays init-dirs
pubdelays preflight
pubdelays manifest --limit 10
pubdelays schema
```

`preflight` may report missing raw inputs, but should exit with a clear, documented status.

## Parser validation

Fixture tests must cover:

```text
normal PubmedArticle
missing History
missing ArticleDate but present PubDate
DeleteCitation
DOI in ELocationID and ArticleIdList
publication type extraction
ISSNLinking extraction
MeSH terms with qualifiers
```

Command:

```bash
pytest -q tests/test_medline_parser.py
```

## External metadata validation

Each external preprocessor must check required input columns and produce documented output columns.

Command:

```bash
pytest -q tests/test_external_preprocessors.py
```

Smoke command on real data:

```bash
pubdelays external-all --resume
```

Expected processed outputs:

```text
data/processed_data/scimago.csv
data/processed_data/web_of_science.csv
data/processed_data/doaj.csv
data/processed_data/norwegian_list.csv
data/processed_data/retraction_watch.csv
```

## Transform validation

Required behavioral tests:

```text
accepted and received required
article_date preferred over pubdate
pubdate fallback works when article_date missing
negative delays are dropped
ceased journal filtering works
retraction DOI join works
Scimago/NPI year-specific metadata is selected
final schema order is stable
```

Command:

```bash
pytest -q tests/test_transform_articles.py
```

## Manifest validation

After any smoke run:

```bash
pubdelays manifest --limit 20
```

Check:

```text
failed rows include error text
skipped rows include skip reason metadata
success rows include output path and row count when applicable
worker identity is present
elapsed_seconds is nonnegative
```

## Cross-run validation

When full raw data are available, compare a new run against the previous accepted processed dataset and manifest summary.

Required comparisons:

```text
1. total row count
2. total unique DOI count
3. total unique PMID count if available
4. column names and order
5. per-stage filter counts
6. join cardinalities by external source
7. missingness by key fields
8. distribution summaries for acceptance_delay and publication_delay
9. rows retained by pubdate fallback
10. rows removed by ceased-year correction
```

Suggested row-hash check:

```text
hash selected stable columns: doi, title, journal, issn_linking, received, accepted, article_date, acceptance_delay, publication_delay
compare matched rows by DOI, then by PMID, then by normalized title+journal
```

## Performance benchmark plan

Record hardware, filesystem, Python version, Polars version, Nix/uv environment, number of workers, and SLURM settings. Benchmark reports are generated artifacts; write them under `data/processed_data/benchmarks/` and do not commit them.

Use this setup block before stage-specific commands:

```bash
mkdir -p data/processed_data/benchmarks
REPORT="data/processed_data/benchmarks/benchmark-$(date -u +%Y%m%dT%H%M%SZ).txt"
{
  echo "# pubdelays benchmark"
  date -u
  uname -a
  python --version
  pubdelays --help | head -1
} > "$REPORT"
TIME="/usr/bin/time -v -a -o $REPORT"
```

`/usr/bin/time -v` records elapsed time and peak RSS on Linux. On systems without GNU time, use `time -p` and record peak RSS from the scheduler or OS monitor.

### External preprocessors

Measure all external preprocessors together, or replace `external-all` with one `external-*` command for per-source timings:

```bash
$TIME pubdelays external-all --resume
```

Record output rows from the manifest and output sizes:

```bash
pubdelays manifest summary >> "$REPORT"
du -h data/processed_data/scimago.csv data/processed_data/web_of_science.csv data/processed_data/doaj.csv data/processed_data/norwegian_list.csv data/processed_data/retraction_watch.csv data/processed_data/publisher_metadata.csv >> "$REPORT" 2>/dev/null || true
```

### XML parse throughput

Full-corpus parse benchmark:

```bash
XML_MB_BEFORE=$(find data/raw_data/pubmed/xmls -type f \( -name '*.xml' -o -name '*.xml.gz' \) -print0 | du --files0-from=- -cb | tail -1 | cut -f1)
$TIME pubdelays parse --jobs 16 --format jsonl --parse-mesh-subterms --resume
JSONL_MB_AFTER=$(find data/temp_data/pubmed/jsonl -type f -name '*.jsonl' -print0 | du --files0-from=- -cb | tail -1 | cut -f1)
printf 'parse_input_bytes=%s\nparse_output_bytes=%s\n' "$XML_MB_BEFORE" "$JSONL_MB_AFTER" >> "$REPORT"
pubdelays manifest summary >> "$REPORT"
```

For a small reproducible smoke benchmark equivalent to `benchmark parse --limit 10`, copy or symlink ten XML/XML.GZ files into a temporary configured `pubmed.xml_dir`, then run the same parse command with that config.

Measure:

```text
XML files / minute
records / second
input MB / second
output MB / second
peak RSS per worker
```

### Transform throughput

Canonical local benchmark:

```bash
$TIME pubdelays transform-shards --shards 64 --jobs 16 --format parquet --resume
pubdelays manifest summary >> "$REPORT"
```

Measure shard skew from filter sidecars:

```bash
python - <<'PY' >> "$REPORT"
from pathlib import Path
import csv
rows = []
for path in sorted(Path('data/temp_data/article_parquet').glob('*.filters.csv')):
    with path.open(newline='', encoding='utf-8') as handle:
        final = {row['stage']: int(row['count']) for row in csv.DictReader(handle)}.get('final_rows', 0)
    rows.append(final)
if rows:
    print(f'transform_shards={len(rows)} min_rows={min(rows)} max_rows={max(rows)} skew={max(rows) / max(min(rows), 1):.2f}')
PY
```

Measure:

```text
JSONL files / minute
input records / second
output rows / second
input MB / second
output MB / second
peak RSS per worker
shard skew
```

For a small reproducible smoke benchmark equivalent to `benchmark transform --shards 8`, run:

```bash
$TIME pubdelays transform-shards --shards 8 --jobs 8 --format parquet --resume
```

### Aggregation throughput

```bash
$TIME pubdelays aggregate-all --resume
pubdelays manifest summary >> "$REPORT"
du -h data/temp_data/article_parquet data/processed_data/processed.parquet data/processed_data/processed.csv >> "$REPORT" 2>/dev/null || true
```

Measure:

```text
Parquet shard count
input rows / second
input MB / second
final Parquet size
CSV export time
peak RSS
```

## Recommended defaults

Local workstation:

```text
JOBS = physical cores - 1
SHARDS = 8 to 16
```

HPC shared filesystem:

```text
parse: one XML file per SLURM array task
transform: SHARDS = 32 to 128
aggregate: single job with enough memory
```

Avoid over-sharding. Too many tiny Parquet files hurt aggregation and shared-filesystem metadata performance.
