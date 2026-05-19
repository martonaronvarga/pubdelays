# pubdelays

`pubdelays` is a reproducible PubMed/MEDLINE publication-delay pipeline. It downloads and verifies PubMed XML, preprocesses external metadata, parses XML into JSONL shards, transforms articles with Polars, and aggregates final Parquet/CSV analysis outputs.

## Standard Workflow

```bash
pubdelays init-dirs
pubdelays preflight
pubdelays download --source baseline --jobs 4 --resume
pubdelays download-external --source all --resume
pubdelays external-all --resume
pubdelays parse --jobs 16 --format jsonl --parse-mesh-subterms --resume
pubdelays validate
pubdelays transform-shards --shards 64 --jobs 16 --format parquet --resume
pubdelays aggregate-all --resume
pubdelays manifest summary
```

## Key Guarantees

- Paths come from `config/default.toml` unless overridden.
- Mutating stages write atomically and log manifest rows.
- Resume skips only complete outputs.
- XML parsing remains streaming.
- SLURM support is explicit and opt-in.

## Build These Docs

```bash
uv sync --extra docs
uv run mkdocs serve
```
