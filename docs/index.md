# pubdelays

`pubdelays` is a reproducible research pipeline for estimating publication and editorial delays from PubMed/MEDLINE records. It converts PubMed XML and journal metadata into article-level Parquet and CSV outputs with explicit schemas, stage contracts, and manifest records.

The documentation emphasizes concrete files and functions: where inputs live, which functions read them, what each stage writes, and which checks protect the final dataset.

![Detailed data flow](assets/data-flow.svg)

For a more detailed source map, see [Function Flow](function-flow.md).

## Design Priorities

- **Reproducibility:** defaults are declared in `config/default.toml`; generated data is written under `data/`.
- **Correctness:** date handling, journal-status filtering, and final columns are documented and tested with fixtures.
- **Auditability:** mutating stages write manifest rows; SLURM array tasks use per-task manifests to avoid shared SQLite writes.
- **Usability:** the same stage names are used locally and on SLURM.
- **Private metadata support:** licensed peer-review metadata can be supplied at run time with `--peer-review` and is not included in the repository.

## Control Flow

The execution path is deliberately shallow. The parser chooses a handler, the handler resolves configuration, and the stage writes outputs and manifest records.

![Command execution sequence](assets/control-flow.svg)

## Recommended Reading Order

1. [Getting Started](getting-started.md) for the standard commands.
2. [Data Layout](data-layout.md) for raw, temporary, manifest, and processed paths.
3. [CLI Reference](cli.md) for command options.
4. [Stage Contracts](STAGE_CONTRACTS.md) for stage-level inputs, outputs, and resume behavior.
5. [HPC and SLURM](hpc-slurm.md) for array jobs and manifest collection.
6. [Analysis Dataset V1](ANALYSIS_DATASET_V1.md) for final columns.

## Build The Documentation

```bash
uv sync --extra docs
uv run mkdocs serve
```

For a strict local build:

```bash
uv run mkdocs build --strict
```
