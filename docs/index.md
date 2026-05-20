# pubdelays

`pubdelays` is a research pipeline for building a reproducible PubMed/MEDLINE publication-delay dataset. It favors legibility, explicit file contracts, and rerunnable stages over production-service complexity.

The pipeline reads PubMed XML, parses it into JSONL shards, joins external journal metadata with Polars, writes article-level Parquet shards, and aggregates final analysis files:

```text
PubMed XML/XML.GZ
  -> parsed JSONL shards
  -> transformed article Parquet shards
  -> processed.parquet + processed.csv
```

## What This Repository Optimizes For

- **Correctness:** semantic choices are documented and covered by fixture tests.
- **Reproducibility:** paths and resources come from `config/default.toml`; generated data stays under `data/`.
- **Ease of use:** local and SLURM workflows use the same CLI and stage names.
- **Auditability:** mutating stages write manifest rows; full-corpus SLURM arrays use per-task manifests that can be collected later.
- **Research pragmatism:** this is a batch analysis pipeline, not a long-running production service.

## Recommended Reading Order

1. [Getting Started](getting-started.md) for install and the standard run.
2. [Data Layout](data-layout.md) for where raw and generated files live.
3. [CLI Reference](cli.md) for commands by task.
4. [Stage Contracts](STAGE_CONTRACTS.md) for precise inputs, outputs, manifests, and resume behavior.
5. [HPC and SLURM](hpc-slurm.md) for job arrays and manifest collection.
6. [Analysis Dataset V1](ANALYSIS_DATASET_V1.md) for final columns.

## Build These Docs

```bash
uv sync --extra docs
uv run mkdocs serve
```

For a CI-style check:

```bash
uv run mkdocs build --strict
```
