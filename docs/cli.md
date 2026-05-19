# CLI Reference

The canonical command is `pubdelays`. The older `pubdelays-pipeline` entry point remains available for existing scripts.

All commands accept `--config config/default.toml` before the subcommand. Relative paths in the config resolve from the repository root.

## Setup and Inspection

```bash
pubdelays init-dirs
pubdelays preflight
pubdelays manifest --limit 20
pubdelays manifest summary
pubdelays schema
```

## Downloads

```bash
pubdelays download --source baseline --jobs 4 --resume
pubdelays download --source updatefiles --jobs 4 --resume
pubdelays download-external --source all --resume
```

`download` verifies PubMed `.xml.gz` files with their `.md5` sidecars. `download-external` writes configured external metadata into raw-data paths and does not require MD5 sidecars.

The downloader sends a project user agent and broad `Accept` header. This is required by sources such as DOAJ, where Python's default `urllib` user agent can receive HTTP 403.

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

`download-external --source all` includes DOAJ and Retraction Watch by default. It also includes SCImago and publisher metadata when these config keys are non-empty:

```toml
[external.download]
scimago_url_template = "https://example.org/scimagojr-{year}.csv"
publisher_url = "https://example.org/publishers.csv"
```

## Parse, Transform, Aggregate

```bash
pubdelays parse --jobs 16 --format jsonl --parse-mesh-subterms --resume
pubdelays validate
pubdelays transform-shards --shards 64 --jobs 16 --format parquet --resume
pubdelays validate-shards --shards 64 --format parquet
pubdelays aggregate-all --resume
pubdelays summaries --resume
```

Use `--dry-run` on expensive planning commands to inspect work without writing outputs or manifest rows.
