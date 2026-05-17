# Publication Delays

Authors: Dominik Dianovics, Marton A. Varga, Miklos Bognar, Balazs Aczel

This repository contains a reproducible pipeline for studying publication and editorial delays in PubMed/MEDLINE records. The active implementation is Python-first and Polars-backed for tabular work. It supports local bare-metal runs, Nix, uv, resumable atomic outputs, SQLite manifests, and opt-in SLURM job arrays.

## Active layout

```text
src/pubdelays/parser/medline.py      # streaming self-vendored MEDLINE XML parser
src/pubdelays/external/              # Polars preprocessors for Scimago, WoS, DOAJ, NPI, Retraction Watch
src/pubdelays/transform/articles.py  # Polars article filtering and enrichment
src/pubdelays/aggregate.py           # Polars aggregation into processed outputs
src/pubdelays/manifest.py            # SQLite manifest, WAL mode, process-safe append writes
src/pubdelays/cli.py                 # pubdelays-pipeline CLI
config/default.toml                  # canonical paths and defaults
DATA_LAYOUT.md                       # exact raw/generated data placement
docs/STAGE_CONTRACTS.md              # stage inputs, outputs, manifests, and failure behavior
docs/ANALYSIS_DATASET_V1.md          # final analysis schema and data dictionary
LEGACY.md                            # semantics ported from legacy R/shell/Python
```

Legacy execution scripts have been replaced by the CLI and documented in `LEGACY.md`.

## Install

Python 3.12 is the supported runtime. Nix is the reference environment:

```bash
nix develop
pubdelays-pipeline --help
pytest -q
```

Fallback for collaborators without Nix:

```bash
scripts/bootstrap_uv.sh
uv run pubdelays-pipeline --help
uv run pytest -q
```

## Place data

Create directories:

```bash
pubdelays-pipeline init-dirs
```

Place existing raw files as documented in `DATA_LAYOUT.md`:

```text
data/raw_data/pubmed/xmls/*.xml.gz
data/raw_data/scimago/scimagojr 2015.csv ... scimagojr 2024.csv
data/raw_data/web_of_science/wos.csv
data/raw_data/directory_of_open_access_journals/doaj_2025_05_15.csv
data/raw_data/norwegian_publication_indicator/norwegian_list_2025_05_14.csv
data/raw_data/retraction_watch/retraction_watch.csv
```

Check readiness:

```bash
pubdelays-pipeline preflight
```

## Local full pipeline

```bash
JOBS=16 SHARDS=64 scripts/pipeline.sh
```

The local transform stage uses shard-level parallelism, not one job per JSON file. Each transform worker loads the external metadata once and processes many JSONL files.

Primary outputs:

```text
data/temp_data/pubmed/jsonl/         # parsed PubMed shards
data/temp_data/article_parquet/      # transformed article shards
data/processed_data/processed.parquet# preferred analysis dataset
data/processed_data/processed.csv    # export/collaboration dataset
data/manifests/pipeline.sqlite       # audit manifest
```

## Download PubMed data

Full baseline:

```bash
pubdelays-pipeline download --source baseline --jobs 4 --resume
```

Smoke test:

```bash
pubdelays-pipeline download --source baseline --limit 2 --jobs 2 --resume
```

Update files:

```bash
pubdelays-pipeline download --source updatefiles --jobs 4 --resume
```

Downloads keep `.md5` sidecars and verify them after transfer. Baseline and updatefiles use the same NCBI layout: each `.xml.gz` file is paired with a same-directory `.xml.gz.md5` sidecar. With `--resume`, existing data files are skipped only when the data file is non-empty and its sidecar verifies; existing sidecars are reused as complete metadata files.

## Individual stages

All commands use `config/default.toml` by default and validate required sections, path keys, dates, and supported shard formats before running a stage. Stage inputs, outputs, manifest rows, resume behavior, and failure behavior are documented in `docs/STAGE_CONTRACTS.md`. The top-level `--help` output lists the canonical workflow order; expensive workflow commands such as `download`, `parse`, `external-all`, `transform-shards`, and `aggregate-all` support `--dry-run` for planning without writing outputs or manifest rows. Override config paths with:

```bash
pubdelays-pipeline --config path/to/config.toml <command>
```

External metadata:

```bash
pubdelays-pipeline external-all --resume
```

Parse XML:

```bash
pubdelays-pipeline parse --jobs 16 --format jsonl --parse-mesh-subterms --resume
```

Parsing fails on malformed XML by default. Use `--recover-malformed-xml` only for explicit best-effort salvage runs. `jsonl` is the preferred full-scale output because it streams records; `json` writes one array and accumulates records in memory.

Validate parsed JSONL:

```bash
pubdelays-pipeline validate
```

Sharded transform:

```bash
pubdelays-pipeline transform-shards --shards 64 --jobs 16 --format parquet --resume
```

Aggregate:

```bash
pubdelays-pipeline aggregate-all --resume
```

For a single custom output format, use `aggregate --output path/to/output.parquet`.

Derive analysis summaries:

```bash
pubdelays-pipeline summaries --resume
```

Inspect manifest:

```bash
pubdelays-pipeline manifest --limit 20
```

## SLURM job arrays

SLURM is opt-in. Run external metadata preprocessing once locally or as one small job, then use arrays for XML parsing and article transforms. Recommended defaults are one XML file per parse array task, modulo JSONL sharding for transform tasks (`SHARDS=64` by default), and one aggregate job with enough memory for the final collect. SLURM logs are written under `logs/` with job and array IDs so failed tasks can be identified and rerun.

```bash
pubdelays-pipeline external-all --resume
scripts/slurm_prepare_arrays.sh
```

Parse array:

```bash
N=$(wc -l < data/manifests/parse_inputs.txt)
sbatch --array=0-$((N - 1)) scripts/slurm_parse_array.sh
```

The parse wrapper fails early when `data/manifests/parse_inputs.txt` is missing or empty. Rerun failed task IDs with the same array index after fixing inputs or resource limits.

After parsing completes, refresh transform inputs and submit transform shards:

```bash
pubdelays-pipeline list-inputs \
  --kind json \
  --input-dir data/temp_data/pubmed/jsonl \
  --output data/manifests/transform_inputs.txt

SHARDS=64 sbatch --array=0-63 scripts/slurm_transform_array.sh
```

The transform wrapper fails early when `data/manifests/transform_inputs.txt` is missing or empty. Each task writes one deterministic modulo shard, so failed array indices can be rerun independently.

Aggregate after all transform jobs complete:

```bash
sbatch scripts/slurm_aggregate.sh
```

The aggregation script uses `aggregate-all`, so the shard directory is scanned once and both Parquet and CSV outputs are written from the same collected frame.

## Manifest and resumability

Every mutating stage writes a row to `data/manifests/pipeline.sqlite` with stage name, status, input/output paths, byte sizes, checksums when enabled, row counts, worker identity, timestamps, and error text.

Outputs are written through same-directory temporary files and atomically renamed on success. A failed task leaves the previous completed output intact.

## Performance model

The main throughput path is:

```text
PubMed .xml.gz -> streaming parser -> JSONL shards -> Polars transform shards -> Parquet -> aggregate
```

Performance choices:

- no decompression of PubMed XML to disk;
- JSONL for parse shards, because it is append-free, line-oriented, resumable, and easy to validate;
- Parquet for transformed article shards and final analysis input;
- Polars for all tabular preprocessing, joins, and aggregation;
- SLURM modulo sharding for transform tasks, so each worker amortizes external metadata loading over many PubMed files;
- SQLite WAL manifest instead of shared progress text files.

## Correctness notes

The migration preserves the legacy R data-logic sequence unless documented otherwise. Two legacy defects are intentionally corrected:

1. Missing `article_date` falls back to `pubdate` for `publication_delay`.
2. Ceased journals are filtered against the article publication year.

See `LEGACY.md` for details.
