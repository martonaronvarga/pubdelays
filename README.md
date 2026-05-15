# Publication Delays

Authors: Dominik Dianovics, Marton A. Varga, Miklos Bognar, Balazs Aczel

This repository contains a reproducible pipeline for studying publication and editorial delays in PubMed/MEDLINE records. The active implementation is Python-first, Polars-backed for tabular work, Nix/uv reproducible, resumable, and safe for local or SLURM execution.

## Current implementation

The canonical source code is under `src/pubdelays/`.

```text
src/pubdelays/parser/medline.py     # streaming self-vendored MEDLINE XML parser
src/pubdelays/external/             # Polars preprocessors for Scimago, WoS, DOAJ, NPI, Retraction Watch
src/pubdelays/transform/articles.py # Polars article filtering/enrichment
src/pubdelays/aggregate.py          # Polars aggregation into processed outputs
src/pubdelays/manifest.py           # SQLite manifest, WAL mode, process-safe append writes
src/pubdelays/cli.py                # pubdelays-pipeline CLI
```

Legacy ad hoc R/shell/Python scripts are not part of the active pipeline. Their behavior has been ported into named Python modules and documented in `LEGACY_MIGRATION.md` where relevant.

## Install

Nix is the reference environment:

```bash
nix develop
pubdelays-pipeline --help
pytest -q
```

Collaborator fallback without Nix:

```bash
scripts/bootstrap_uv.sh
uv run pubdelays-pipeline --help
uv run pytest -q
```

## Place raw data

Run:

```bash
pubdelays-pipeline init-dirs
```

Then place files as described in `DATA_LAYOUT.md`:

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

`io/` is intentionally unused.

## Local full pipeline

```bash
JOBS=16 scripts/pipeline.sh
```

Outputs:

```text
data/temp_data/pubmed/jsonl/        # parser shards
data/temp_data/article_parquet/     # transformed article shards
data/processed_data/processed.parquet
data/processed_data/processed.csv
data/manifests/pipeline.sqlite
```

The final Parquet file is the preferred internal analysis input. The CSV export exists for collaborators and downstream tools that do not read Parquet.

## Individual stages

Download PubMed baseline XML and MD5 files:

```bash
pubdelays-pipeline download --source baseline --resume
```

For a smoke test:

```bash
pubdelays-pipeline download --source baseline --limit 2 --resume
```

Clean external metadata:

```bash
pubdelays-pipeline external-scimago \
  --input-dir data/raw_data/scimago \
  --output data/processed_data/scimago.csv \
  --resume

pubdelays-pipeline external-wos \
  --input data/raw_data/web_of_science/wos.csv \
  --output data/processed_data/web_of_science.csv \
  --resume

pubdelays-pipeline external-doaj \
  --input data/raw_data/directory_of_open_access_journals/doaj_2025_05_15.csv \
  --output data/processed_data/doaj.csv \
  --resume

pubdelays-pipeline external-npi \
  --input data/raw_data/norwegian_publication_indicator/norwegian_list_2025_05_14.csv \
  --output data/processed_data/norwegian_list.csv \
  --resume

pubdelays-pipeline external-retraction-watch \
  --input data/raw_data/retraction_watch/retraction_watch.csv \
  --output data/processed_data/retraction_watch.csv \
  --resume
```

Parse MEDLINE XML into JSONL:

```bash
pubdelays-pipeline parse \
  --input-dir data/raw_data/pubmed/xmls \
  --output-dir data/temp_data/pubmed/jsonl \
  --format jsonl \
  --parse-mesh-subterms \
  --jobs 16 \
  --resume
```

Transform JSONL into article Parquet shards:

```bash
pubdelays-pipeline transform \
  --input data/temp_data/pubmed/jsonl \
  --output-dir data/temp_data/article_parquet \
  --format parquet \
  --scimago data/processed_data/scimago.csv \
  --web-of-science data/processed_data/web_of_science.csv \
  --doaj data/processed_data/doaj.csv \
  --norwegian-list data/processed_data/norwegian_list.csv \
  --retraction-watch data/processed_data/retraction_watch.csv \
  --jobs 16 \
  --resume
```

Aggregate shards:

```bash
pubdelays-pipeline aggregate \
  --input data/temp_data/article_parquet \
  --output data/processed_data/processed.parquet \
  --resume
```

## SLURM mode

SLURM is opt-in. Local execution is the default.

Prepare parse and transform input lists:

```bash
scripts/slurm_prepare_arrays.sh
```

Submit parse array:

```bash
N=$(wc -l < data/manifests/parse_inputs.txt)
sbatch --array=0-$((N - 1)) scripts/slurm_parse_array.sh
```

After parsing finishes, refresh transform inputs and submit shard transforms:

```bash
pubdelays-pipeline list-inputs \
  --kind json \
  --input-dir data/temp_data/pubmed/jsonl \
  --output data/manifests/transform_inputs.txt

SHARDS=64 sbatch --array=0-63 scripts/slurm_transform_array.sh
```

Aggregate after all transform jobs complete:

```bash
sbatch scripts/slurm_aggregate.sh
```

The transform SLURM stage uses modulo sharding. Each task loads external metadata once, processes many JSONL files, and writes one Parquet shard. This is much faster than reloading all external metadata once per PubMed XML file.

## Manifest

Every mutating stage writes a row to `data/manifests/pipeline.sqlite` with stage name, status, input/output paths, byte sizes, checksums when enabled, row counts, worker identity, timestamps, and error text.

Inspect recent rows:

```bash
pubdelays-pipeline manifest --limit 20
```

## Semantic corrections relative to legacy code

Two legacy defects are intentionally corrected:

1. Missing `article_date` now falls back to `pubdate` when calculating `publication_delay`.
2. Ceased journals are filtered against the article publication year instead of using the broken `ceased = is.numeric(ceased)` transformation.

Everything else is intended to preserve the legacy join/filter semantics unless explicitly documented otherwise.
