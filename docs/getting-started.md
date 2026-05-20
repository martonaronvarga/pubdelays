# Getting Started

This page gives the shortest path from a clean checkout to a complete research dataset.

## Install

Nix is the reference environment:

```bash
nix develop
pubdelays --help
pytest -q
```

Without Nix, use uv:

```bash
scripts/bootstrap_uv.sh
uv run pubdelays --help
uv run pytest -q
```

## Create Directories

```bash
pubdelays init-dirs
```

Place raw data under the paths documented in [Data Layout](data-layout.md), then check readiness:

```bash
pubdelays preflight
```

## Standard Local Run

```bash
pubdelays download --source baseline --jobs 4 --resume
pubdelays download-external --source all --resume
pubdelays external-all --resume
pubdelays parse --jobs 16 --format jsonl --parse-mesh-subterms --resume
pubdelays validate
pubdelays transform-shards --shards 64 --jobs 16 --format parquet --resume
pubdelays validate-shards --shards 64 --format parquet
pubdelays aggregate-all --resume
pubdelays summaries --resume
pubdelays manifest summary
```

If raw PubMed XML and external metadata are already present, skip the download commands.

## Standard SLURM Run

```bash
pubdelays slurm workflow --shards 64 --max-array-size 1001
```

The workflow submits parse, transform-input preparation, transform shards, and aggregation with `afterok` dependencies. Parse and transform array tasks write per-task manifests under `data/manifests/slurm/`.

After the workflow finishes, collect the per-task manifests once:

```bash
pubdelays manifest collect \
  --manifest data/manifests/pipeline.sqlite \
  --input-dir data/manifests/slurm
```

## Final Outputs

```text
data/processed_data/processed.parquet  # canonical analysis dataset
data/processed_data/processed.csv      # collaborator/export copy
data/processed_data/summaries/         # derived summary tables
```

Validate the final schema:

```bash
pubdelays schema --input data/processed_data/processed.parquet
```
