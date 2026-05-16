
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
uv run pubdelays-pipeline --help
```

## CLI smoke checks

These should work without raw data:

```bash
pubdelays-pipeline --help
pubdelays-pipeline init-dirs
pubdelays-pipeline preflight
pubdelays-pipeline manifest --limit 10
pubdelays-pipeline schema
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
pubdelays-pipeline external-all --resume
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
pubdelays-pipeline manifest --limit 20
```

Check:

```text
failed rows include error text
skipped rows include skip reason metadata
success rows include output path and row count when applicable
worker identity is present
elapsed_seconds is nonnegative
```

## Differential validation against legacy

When full raw data and legacy outputs are available, compare old and new results. Exact equality is not expected because known legacy bugs are corrected.

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
9. rows retained only by pubdate fallback
10. rows removed by ceased-year correction
```

Run the lightweight differential harness:

```bash
pubdelays-pipeline compare-legacy \
  --legacy path/to/legacy_processed.csv \
  --new data/processed_data/processed.parquet \
  --output data/processed_data/validation/differential.csv
```

The report classifies differences as `expected_correction`, `format_or_type_difference`, or `potential_migration_bug`. See `docs/SEMANTIC_DECISIONS.md` for the narrow expected-correction predicates.

Suggested row-hash check:

```text
hash selected stable columns: doi, title, journal, issn_linking, received, accepted, article_date, acceptance_delay, publication_delay
compare matched rows by DOI, then by PMID, then by normalized title+journal
```

## Performance benchmark plan

Record hardware, filesystem, Python version, Polars version, Nix/uv environment, number of workers, and SLURM settings.

### XML parse throughput

Measure:

```text
XML files / minute
records / second
peak RSS per worker
output MB / second
```

Example:

```bash
time pubdelays-pipeline parse --jobs 16 --format jsonl --parse-mesh-subterms --resume
```

### External preprocessors

Measure each preprocessor separately and together:

```bash
time pubdelays-pipeline external-all --resume
```

### Transform throughput

Canonical benchmark:

```bash
time pubdelays-pipeline transform-shards --shards 64 --jobs 16 --format parquet --resume
```

Measure:

```text
JSONL files / minute
input records / second
output rows / second
metadata load time per shard
```

### Aggregation throughput

```bash
time pubdelays-pipeline aggregate-all --resume
```

Measure:

```text
Parquet shard count
input rows / second
final Parquet size
CSV export time
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
