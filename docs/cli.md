# CLI Reference

The command is `pubdelays`. Keep global options before the subcommand:

```bash
pubdelays --config config/default.toml <command>
```

Relative config paths resolve from the repository root. Commands are intentionally plain so they are easy to paste into shell scripts and job files.

## Setup And Inspection

```bash
pubdelays init-dirs
pubdelays preflight
pubdelays schema
pubdelays schema --input data/processed_data/processed.parquet
```

## Downloads

```bash
pubdelays download --source baseline --jobs 4 --resume
pubdelays download --source updatefiles --jobs 4 --resume
pubdelays download-external --source all --resume
```

`download` verifies PubMed `.xml.gz` files with `.md5` sidecars. `download-external` fetches public/configured metadata. Licensed files stay manual: place them in `data/raw_data/` or pass them explicitly at transform time.

## External Metadata

```bash
pubdelays external-all --resume
pubdelays external-scimago --resume
pubdelays external-wos --resume
pubdelays external-doaj --resume
pubdelays external-npi --resume
pubdelays external-retraction-watch --resume
pubdelays external-publisher --resume
```

`external-all` runs the configured preprocessors and writes normalized lookup tables under `data/processed_data/`.

## Parse, Validate, Transform, Aggregate

```bash
pubdelays parse --jobs 16 --format jsonl --parse-mesh-subterms --resume
pubdelays validate
pubdelays transform-shards --shards 64 --jobs 16 --format parquet --resume
pubdelays transform-shards --peer-review path/to/private-peer-review.csv --shards 64 --resume
pubdelays validate-shards --shards 64 --format parquet
pubdelays aggregate-all --resume
pubdelays summaries --resume
```

`transform-shards` is the full-corpus workhorse. It assigns parsed JSONL files to modulo shards, loads external metadata once per worker, and writes canonical article Parquet shards. `--peer-review` accepts a private/licensed table keyed by `doi`, `pmid`, or `title`; when omitted, peer-review columns remain present but empty.

## Manifests

```bash
pubdelays manifest --limit 20
pubdelays manifest summary
pubdelays manifest failed --limit 50
pubdelays manifest show --json
pubdelays manifest retry-script
```

HPC-friendly helpers that do not need the `sqlite3` shell:

```bash
pubdelays manifest check --manifest data/manifests/pipeline.sqlite
pubdelays manifest check --manifest data/manifests/pipeline.sqlite --cleanup --archive-dir data/manifests/corrupt
pubdelays manifest collect --manifest data/manifests/pipeline.sqlite --input-dir data/manifests/slurm
```

`manifest collect` is a post-run audit step. It appends per-task rows into the target manifest; run it once for a clean count.

## SLURM

```bash
pubdelays slurm submit parse --dry-run
pubdelays slurm submit transform-shards --dry-run --shards 64
pubdelays slurm workflow --shards 64 --max-array-size 1001
pubdelays slurm status <job-id>
pubdelays slurm cleanup <job-id>
pubdelays slurm cleanup <job-id> --cancel
```

`slurm cleanup` previews dependency-blocked pending jobs by default. It only calls `scancel` when `--cancel` is present.

## Output Comparison

```bash
pubdelays compare-outputs \
  --baseline data/processed_data/processed.previous.csv \
  --candidate data/processed_data/processed.csv \
  --output data/processed_data/validation/differential.csv
```

Use this when you need a row-level diff between two runs.
