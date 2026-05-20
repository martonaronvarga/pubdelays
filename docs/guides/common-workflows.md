---
title: Common workflows
description: Practical pubdelays command sequences grounded in the current CLI.
icon: octicons/list-ordered-16
---

# Common workflows

## Inspect without raw data

```bash
pubdelays --help
pubdelays init-dirs
pubdelays preflight
pubdelays schema
pubdelays manifest --limit 10
```

`preflight` can report missing raw inputs; that is useful before moving large source files.

## Small download smoke test

```bash
pubdelays download --source baseline --limit 2 --jobs 2 --resume
pubdelays parse --limit 2 --jobs 2 --format jsonl --resume
pubdelays validate
```

Use this to test NCBI connectivity and parser output shape without downloading the full baseline.

## Full local run with existing raw data

```bash
pubdelays external-all --resume
pubdelays journals --resume
pubdelays parse --jobs 16 --format jsonl --parse-mesh-subterms --resume
pubdelays validate
pubdelays transform-shards --shards 64 --jobs 16 --format parquet --resume
pubdelays validate-shards --shards 64 --format parquet
pubdelays aggregate-all --resume
pubdelays summaries --resume
```

## Compare outputs between runs

```bash
pubdelays compare-outputs \
  --baseline data/processed_data/processed.previous.csv \
  --candidate data/processed_data/processed.csv \
  --output data/processed_data/validation/differential.csv
```

Use this after semantic or dependency changes when you have a previous accepted output.
