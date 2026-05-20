---
title: Local development
description: Source editing workflow for tests, linting, and documentation checks.
icon: octicons/code-16
---

# Local development

## Edit loop

1. Inspect the relevant module and tests.
2. Patch the smallest coherent behavior.
3. Run targeted tests first.
4. Run broader static checks before committing.

## Targeted tests

```bash
pytest -q tests/test_medline_parser.py
pytest -q tests/test_transform_articles.py
pytest -q tests/test_shards.py
pytest -q tests/test_manifest.py
```

Choose tests based on the changed boundary. For example, parser date extraction changes belong with `tests/test_medline_parser.py`; final column changes belong with `tests/test_analysis_schema.py` and `tests/test_transform_articles.py`.

## Broad checks

```bash
python -m compileall -q src tests
pytest -q
ruff check src tests
git diff --check
```

With uv:

```bash
uv run pytest -q
uv run ruff check src tests
uv run zensical build
```

!!! tip "Entry point mismatch"
    In an editable or source-tree check, prefer `uv run python -m pubdelays.cli --help` if a previously installed `pubdelays` entry point might resolve to old code.
