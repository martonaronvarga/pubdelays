---
title: Testing
description: Commands and test files for parser, transform, manifest, shard, and docs validation.
icon: octicons/checklist-16
---

# Testing

## Targeted commands

```bash
pytest -q tests/test_medline_parser.py
pytest -q tests/test_external_preprocessors.py
pytest -q tests/test_transform_articles.py
pytest -q tests/test_shards.py
pytest -q tests/test_manifest.py
pytest -q tests/test_end_to_end_pipeline.py
```

## Full checks

```bash
python -m compileall -q src tests
pytest -q
ruff check src tests
uv run zensical build
git diff --check
```

## Nix checks

```bash
nix flake check --show-trace
nix build --show-trace --print-build-logs
```

## CLI smoke checks

```bash
uv run python -m pubdelays.cli --help
uv run python -m pubdelays.cli schema
uv run python -m pubdelays.cli preflight
```

`preflight` can fail readiness when raw data is missing. Treat clear missing-input reporting as a useful result, not a docs failure.
