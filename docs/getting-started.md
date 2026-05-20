# Getting Started

This page gives the standard path from a clean checkout to a complete analysis dataset. The commands are shown with default paths; use `--config` when running with a site-specific configuration.

## 1. Install

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

## 2. Create Directories

```bash
pubdelays init-dirs
```

Place PubMed XML/XML.GZ and external metadata under the paths described in [Data Layout](data-layout.md), then run:

```bash
pubdelays preflight
```

## 3. Review The Function Map

For a source-oriented trace of the pipeline, use [Function Flow](function-flow.md). It lists the concrete functions that read inputs, transform records, and write outputs.

## 4. Run Locally

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

If raw PubMed XML and external metadata are already present, skip the download commands. Stages use complete-file checks for resume behavior.

## 5. Run On SLURM

```bash
pubdelays slurm workflow --shards 64 --max-array-size 1001
```

The workflow submits parse, transform-input preparation, transform shards, and aggregation with `afterok` dependencies. Parse and transform arrays write per-task manifests under `data/manifests/slurm/`.

Collect per-task manifests once after the workflow completes:

```bash
pubdelays manifest collect \
  --manifest data/manifests/pipeline.sqlite \
  --input-dir data/manifests/slurm
```

## 6. Check Outputs

```text
data/processed_data/processed.parquet  # canonical analysis dataset
data/processed_data/processed.csv      # CSV export
data/processed_data/summaries/         # derived summary tables
```

Validate the final schema:

```bash
pubdelays schema --input data/processed_data/processed.parquet
```

For a 64-shard transform, the following should return `64`:

```bash
find data/temp_data/article_parquet -name '*.parquet' | wc -l
```
