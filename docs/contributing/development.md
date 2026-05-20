---
title: Development
description: Source layout and behavior-change workflow for contributors.
icon: octicons/code-square-16
---

# Development

## Source layout

```text
src/pubdelays/parser/medline.py       streaming MEDLINE XML parser
src/pubdelays/external/               Polars external metadata preprocessors
src/pubdelays/transform/articles.py   article filtering, enrichment, schema construction
src/pubdelays/aggregate.py            article shard aggregation
src/pubdelays/manifest.py             SQLite manifest
src/pubdelays/cli.py                  CLI surface
config/default.toml                   canonical defaults
scripts/                              thin wrappers
```

## Change workflow

1. Read the relevant code and test fixtures.
2. Preserve semantic invariants unless intentionally changing them.
3. Add or update targeted tests for changed behavior.
4. Run narrow tests before broad checks.
5. Update docs when commands, paths, schemas, manifests, or user-facing behavior change.

!!! warning "Data semantics"
    Changes to `article_date` fallback, ceased-journal filtering, filter stages, or canonical columns require explicit tests and documentation updates.

## Dependencies

Runtime dependencies are declared in `pyproject.toml`: `lxml` and `polars`. Do not add dependencies without a clear pipeline or docs reason.
