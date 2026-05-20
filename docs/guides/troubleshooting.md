---
title: Troubleshooting
description: Concrete failure modes and commands for diagnosing pubdelays runs.
icon: octicons/alert-16
---

# Troubleshooting

## `preflight` reports missing inputs

Check `config/default.toml` or your custom config first. Raw defaults include:

```text
data/raw_data/pubmed/xmls
data/raw_data/scimago
data/raw_data/web_of_science/wos.csv
data/raw_data/directory_of_open_access_journals/doaj_2025_05_15.csv
data/raw_data/norwegian_publication_indicator/norwegian_list_2025_05_14.csv
data/raw_data/retraction_watch/retraction_watch.csv
```

Create directories with `pubdelays init-dirs`, then place raw files or adjust config paths.

## XML parsing fails

Parsing fails on malformed XML by default. For a deliberate salvage run:

```bash
pubdelays parse-one path/to/file.xml.gz path/to/output.jsonl --recover-malformed-xml
```

!!! warning "Use recovery deliberately"
    `--recover-malformed-xml` uses lxml best-effort recovery. Keep the default strict parse for normal runs so corrupt source files fail visibly.

## Shard validation fails

Run:

```bash
pubdelays validate-shards --shards 64 --format parquet
```

The validator checks missing shard IDs, duplicate shard outputs, wrong `of-N` totals, wrong format, unreadable files, and missing canonical columns.

Canonical files look like:

```text
articles-shard-00000-of-00064.parquet
articles-shard-00001-of-00064.parquet
```

## Manifest looks corrupt on HPC

Use Python-based integrity checks when the `sqlite3` shell is unavailable:

```bash
pubdelays manifest check --manifest data/manifests/pipeline.sqlite
pubdelays manifest check \
  --manifest data/manifests/pipeline.sqlite \
  --cleanup \
  --archive-dir data/manifests/corrupt
```

## CLI imports old code

If `pubdelays --help` does not show the expected command list, run from source:

```bash
PYTHONPATH=src uv run python -m pubdelays.cli --help
```
