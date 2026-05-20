---
title: Installation
description: Supported local setup commands for Nix and uv.
icon: octicons/download-16
---

# Installation

`pyproject.toml` declares Python `>=3.12`, runtime dependencies on `lxml` and `polars`, and the console script `pubdelays = "pubdelays.cli:main"`. The repository uses Nix as the reference environment and uv as the collaborator fallback.

=== "Nix"

    ```bash
    nix develop
    pubdelays --help
    pytest -q
    ```

=== "uv"

    ```bash
    scripts/bootstrap_uv.sh
    uv run pubdelays --help
    uv run pytest -q
    ```

For source-tree smoke checks without an installed entry point, use:

```bash
PYTHONPATH=src uv run python -m pubdelays.cli --help
```

!!! note "Docs tooling"
    The current development dependency group includes `zensical`. Build the documentation with `uv run zensical build` and preview it with `uv run zensical serve`.

## Verify the checkout

Run these commands before changing pipeline behavior:

```bash
python -m compileall -q src tests
pytest -q
ruff check src tests
git diff --check
```

If local Python is missing `polars`, run the Python commands through `uv run` or inside `nix develop`.
