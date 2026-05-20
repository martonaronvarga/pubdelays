# CLI Reference

The canonical command is `pubdelays`. Put global options before the subcommand:

```bash
pubdelays --config config/default.toml <command>
```

Relative config paths resolve from the repository root.

## Setup and Inspection

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

`download` verifies PubMed `.xml.gz` files with `.md5` sidecars. `download-external` writes public/configured external metadata into raw-data paths. Web of Science and Norwegian Publication Indicator inputs usually remain manual/licensed files.

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
pubdelays validate-shards --shards 64 --format parquet
pubdelays aggregate-all --resume
pubdelays summaries --resume
```

`transform` exists for compatibility, but `transform-shards` is preferred for full-corpus work because each worker loads external metadata once for many JSONL files.

## Manifest Commands

```bash
pubdelays manifest --limit 20
pubdelays manifest summary
pubdelays manifest failed --limit 50
pubdelays manifest show --json
pubdelays manifest retry-script
```

HPC recovery helpers that do not require the `sqlite3` shell:

```bash
pubdelays manifest check --manifest data/manifests/pipeline.sqlite
pubdelays manifest check --manifest data/manifests/pipeline.sqlite --cleanup --archive-dir data/manifests/corrupt
pubdelays manifest collect --manifest data/manifests/pipeline.sqlite --input-dir data/manifests/slurm
```

`manifest collect` appends per-task rows into the target manifest. It is intended as a post-run audit step; if you run it repeatedly against the same files, collected counts are duplicated.

## SLURM Commands

```bash
pubdelays slurm submit parse --dry-run
pubdelays slurm submit transform-shards --dry-run --shards 64
pubdelays slurm workflow --shards 64 --max-array-size 1001
pubdelays slurm status <job-id>
pubdelays slurm cleanup <job-id>
pubdelays slurm cleanup <job-id> --cancel
```

`slurm cleanup` previews dependency-blocked pending jobs by default and cancels them only with `--cancel`.
